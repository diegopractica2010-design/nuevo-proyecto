import logging
import signal
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from fastapi import BackgroundTasks, Body, Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from typing import Optional

# ============================================================================
# FASE A/4: Initialize logging and Celery first
# ============================================================================
from backend.logging_setup import setup_logging
setup_logging()

from backend.config import FRONTEND_DIR, MAX_RESULTS, CORS_ORIGINS, PROMETHEUS_ENABLED
from backend.db import init_db
from backend.exception_handlers import register_exception_handlers
from backend.middleware import RateLimitMiddleware, RequestIdMiddleware, LoggingMiddleware
from backend.celery_app import init_celery
from backend.health_check import get_health_checker
from backend.models import SearchResponse
from backend.search_service import SearchServiceError, _persist_prices, search_products
from backend.basket_service import BasketService, PriceHistoryService
from backend.models_baskets import Basket, BasketSummary, PaginatedBaskets
from backend.auth import ACCESS_TOKEN_EXPIRE_MINUTES, AuthService, TokenService, pwd_context, require_admin, revoke_token, send_verification_email, send_password_reset_email
from backend.models_auth import Token, UserCreate, UserLogin, UserResponse

# FASE 4: Import new modules
from backend.security import SecurityHeadersMiddleware
from backend.metrics import (
    metrics_middleware,
    get_metrics_response,
)
from backend.backup import BackupManager

logger = logging.getLogger(__name__)


async def _startup_event() -> None:
    """Initialize startup-only resources."""
    logger.info("=" * 80)
    logger.info("Radar de Precios - Fase 4 (Produccion & Operacion)")
    logger.info(f"Started at {datetime.now(UTC).isoformat()}")
    logger.info("=" * 80)

    try:
        from backend.tasks import schedule_backups

        schedule_backups()
        logger.info("Backup scheduler started")
    except Exception as e:
        logger.warning(f"Failed to start backup scheduler: {e}")


async def _shutdown_event() -> None:
    """Cleanup resources gracefully on shutdown."""
    logger.info("=" * 80)
    logger.info("Shutting down Radar de Precios...")
    logger.info("=" * 80)

    try:
        logger.info("Waiting for pending Celery tasks...")
        from backend.celery_app import celery_app

        celery_app.control.inspect().active()
    except Exception as e:
        logger.warning(f"Error waiting for Celery tasks: {e}")

    try:
        from backend.db import engine

        engine.dispose()
        logger.info("Database connection pool disposed")
    except Exception as e:
        logger.warning(f"Error closing database: {e}")

    logger.info("Shutdown complete")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _startup_event()
    try:
        yield
    finally:
        await _shutdown_event()

# ============================================================================
# FastAPI App Initialization
# ============================================================================
app = FastAPI(
    title="Radar de Precios",
    version="0.4.0-phase4",
    description="Comparador de precios de supermercados chilenos (Fase 4: Produccion & Operacion)",
    lifespan=lifespan,
)

# ============================================================================
# FASE A/4: Initialize Infrastructure
# ============================================================================
# Initialize Celery
init_celery()

# Initialize database
init_db()

# Register error handlers
register_exception_handlers(app)

# ============================================================================
# Middleware Stack (order matters!)
# ============================================================================
# 1. Security headers (FASE 4)
app.add_middleware(SecurityHeadersMiddleware)

# 2. RequestId middleware (for tracing)
app.add_middleware(RequestIdMiddleware)

# 3. Logging middleware
app.add_middleware(LoggingMiddleware)

# 4. Metrics middleware (FASE 4)
if PROMETHEUS_ENABLED:
    app.middleware("http")(metrics_middleware)

# 5. Rate limiting
app.add_middleware(RateLimitMiddleware)

# 6. CORS (restrictive)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    allow_credentials=True,
    max_age=3600,  # Cache preflight 1 hour
)

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
app.mount(
    "/_next",
    StaticFiles(directory=FRONTEND_DIR / "out" / "_next", check_dir=False),
    name="next-static",
)

logger.info("=" * 80)
logger.info("Radar de Precios - Fase A (Estabilización)")
logger.info("=" * 80)


def _result_count(result: SearchResponse | dict) -> int:
    if isinstance(result, dict):
        return len(result.get("results", []))
    return len(result.results)


def _username_from_authorization(authorization: Optional[str], *, required: bool = False) -> Optional[str]:
    if not authorization:
        if required:
            raise HTTPException(status_code=401, detail="Authorization header missing")
        return None

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    username = TokenService.verify_token(authorization[7:])
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    return username


def _ensure_basket_access(basket: Basket, username: Optional[str]) -> None:
    if basket.user_id and basket.user_id != username:
        raise HTTPException(status_code=403, detail="Basket belongs to another user")


def _safe_frontend_path(relative_path: str):
    frontend_out = (FRONTEND_DIR / "out").resolve()
    candidate = (frontend_out / relative_path).resolve()
    if candidate == frontend_out or frontend_out in candidate.parents:
        return candidate
    return None


def _frontend_file_response(path: str, *, fallback_index: bool = False) -> FileResponse | None:
    clean_path = (path or "index").strip().lstrip("/")
    candidates: list[str] = []
    if clean_path:
        candidates.append(clean_path)
        if "." not in clean_path.rsplit("/", 1)[-1]:
            candidates.append(f"{clean_path}.html")
            candidates.append(f"{clean_path}/index.html")
    if fallback_index:
        candidates.append("index.html")

    for relative in candidates:
        candidate = _safe_frontend_path(relative)
        if candidate and candidate.is_file():
            return FileResponse(candidate)
    return None


def _request_wants_html(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    return "text/html" in accept and "application/json" not in accept


@app.get("/", include_in_schema=False)
def index():
    logger.info("Serving index page")
    response = _frontend_file_response("index", fallback_index=True)
    if response:
        return response
    raise HTTPException(status_code=503, detail="Frontend build not available. Run npm run build in frontend/")


@app.get("/health", include_in_schema=False)
def health():
    """Simple liveness check for load balancers."""
    logger.debug("Health check requested")
    return {"status": "ok"}


@app.get("/health/live", include_in_schema=False)
def health_live():
    """Liveness probe (K8s ready)."""
    checker = get_health_checker()
    check = checker.check_live()
    return check


@app.get("/health/ready", include_in_schema=False)
def health_ready():
    """Readiness probe (K8s ready)."""
    checker = get_health_checker()
    check = checker.check_ready()
    return check


@app.get("/health/full", include_in_schema=False)
def health_full():
    """Full system health check (diagnostics)."""
    checker = get_health_checker()
    check = checker.check_full()
    return check


@app.get("/status", include_in_schema=False)
def status_dashboard():
    from backend.status_dashboard import get_status_html
    return HTMLResponse(content=get_status_html())


@app.get("/health/scraper", include_in_schema=False)
def scraper_health():
    """Return the last saved scraper monitor status without running a new check."""
    try:
        from backend.parser_monitor import get_status

        return get_status()
    except Exception as exc:
        logger.warning("scraper health check failed: %s", exc)
        return {"status": "unavailable", "error": str(exc)}


@app.get("/stores")
def get_stores():
    from backend.store_adapters import list_stores
    return [
        {
            "id": s.name,
            "display_name": s.display_name,
            "experimental": s.experimental,
            "url": s.url,
            "logo_url": s.logo_url,
            "description": s.description,
            "country": s.country,
            "currency": s.currency,
        }
        for s in list_stores()
    ]


@app.get("/search", response_model=SearchResponse)
@app.post("/search", response_model=SearchResponse)
async def search(
    background: BackgroundTasks,
    query: Optional[str] = Query(None, min_length=1, description="Nombre del producto"),
    q: Optional[str] = Query(None, min_length=1, description="Alias compatible para query"),
    limit: int = Query(100, ge=1, le=MAX_RESULTS, description="Cantidad máxima de resultados"),
    store: str = Query("lider", description="Tienda a buscar: lider, jumbo"),
    body: Optional[dict] = Body(default=None),
):
    # For POST requests, also accept params from JSON body
    if body is not None:
        query = query or body.get("query") or body.get("q")
        q = q or body.get("q") or body.get("query")
        if "limit" in body:
            try:
                limit = int(body["limit"])
            except (ValueError, TypeError):
                pass
        if "store" in body:
            store = str(body["store"])

    search_query = query or q
    if not search_query:
        raise HTTPException(status_code=422, detail="Query parameter 'query' or 'q' is required")

    logger.info(f"Search request: query='{search_query}', limit={limit}, store='{store}'")
    try:
        result = await search_products(query=search_query, limit=limit, store=store)
        if (
            isinstance(result, SearchResponse)
            and result.results
            and not result.cached
            and not (result.strategy or "").startswith("db")
        ):
            background.add_task(_persist_prices, result.results, (store or "lider").strip().lower())
        logger.info(f"Search completed: found {_result_count(result)} products from {store}")
        return result
    except SearchServiceError as exc:
        logger.error(f"Search error for {store}: {exc.message}")
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@app.post("/shopping-list/compare")
async def compare_shopping_list_endpoint(payload: dict = Body(...)):
    from backend.shopping_list_service import compare_shopping_list, parse_shopping_items

    raw_items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(raw_items, list):
        raise HTTPException(status_code=422, detail="El payload debe incluir items como lista")

    items = parse_shopping_items(raw_items)
    if not items:
        raise HTTPException(status_code=422, detail="Agrega al menos un producto a la lista")
    if len(items) > 40:
        raise HTTPException(status_code=422, detail="La lista puede tener hasta 40 productos")

    try:
        return await compare_shopping_list(items)
    except Exception as exc:
        logger.error("Shopping list compare error: %s", exc, exc_info=True)
        raise HTTPException(status_code=502, detail="No se pudo comparar la lista") from exc


# Endpoints de canastas
@app.post("/baskets", response_model=Basket)
def create_basket(
    name: str = Body(..., embed=True),
    authorization: Optional[str] = Header(None),
):
    username = _username_from_authorization(authorization)
    owner_id = username  # user_id query param removed — was injectable
    logger.info(f"Creating basket: {name}")
    basket = BasketService.create_basket(name, owner_id)
    return basket


@app.get("/baskets", response_model=PaginatedBaskets)
def get_baskets(
    request: Request,
    authorization: Optional[str] = Header(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    if _request_wants_html(request):
        response = _frontend_file_response("baskets")
        if response:
            return response
    username = _username_from_authorization(authorization, required=True)
    logger.info(f"Getting baskets for user: {username}")
    return BasketService.get_user_baskets(username, limit=limit, offset=offset)


@app.get("/baskets/{basket_id}", response_model=Basket)
def get_basket(basket_id: str, authorization: Optional[str] = Header(None)):
    username = _username_from_authorization(authorization)
    logger.info(f"Getting basket: {basket_id}")
    basket = BasketService.get_basket(basket_id)
    if not basket:
        raise HTTPException(status_code=404, detail="Basket not found")
    _ensure_basket_access(basket, username)
    return basket


@app.post("/baskets/{basket_id}/items")
def add_to_basket(
    basket_id: str,
    payload: dict = Body(...),
    authorization: Optional[str] = Header(None),
):
    username = _username_from_authorization(authorization)
    product = payload.get("product") if isinstance(payload.get("product"), dict) else payload
    quantity = int(payload.get("quantity") or 1)
    logger.info(f"Adding to basket {basket_id}: {product.get('name', 'unknown')}")
    basket = BasketService.get_basket(basket_id)
    if not basket:
        raise HTTPException(status_code=404, detail="Basket not found")
    _ensure_basket_access(basket, username)
    success = BasketService.add_to_basket(basket_id, product, quantity)
    if not success:
        raise HTTPException(status_code=404, detail="Basket not found")
    return {"message": "Item added to basket"}


@app.patch("/baskets/{basket_id}/items/{product_id}")
def update_basket_item(
    basket_id: str,
    product_id: str,
    quantity: int = Body(..., embed=True, ge=0),
    authorization: Optional[str] = Header(None),
):
    username = _username_from_authorization(authorization)
    basket = BasketService.get_basket(basket_id)
    if not basket:
        raise HTTPException(status_code=404, detail="Basket not found")
    _ensure_basket_access(basket, username)
    success = BasketService.update_item_quantity(basket_id, product_id, quantity)
    if not success:
        raise HTTPException(status_code=404, detail="Basket or item not found")
    return {"message": "Item updated"}


@app.delete("/baskets/{basket_id}/items/{product_id}")
def remove_from_basket(
    basket_id: str,
    product_id: str,
    authorization: Optional[str] = Header(None),
):
    username = _username_from_authorization(authorization)
    logger.info(f"Removing from basket {basket_id}: {product_id}")
    basket = BasketService.get_basket(basket_id)
    if not basket:
        raise HTTPException(status_code=404, detail="Basket not found")
    _ensure_basket_access(basket, username)
    success = BasketService.remove_from_basket(basket_id, product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Basket or item not found")
    return {"message": "Item removed from basket"}


@app.delete("/baskets/{basket_id}")
def delete_basket(basket_id: str, authorization: Optional[str] = Header(None)):
    username = _username_from_authorization(authorization)
    logger.info(f"Deleting basket: {basket_id}")
    basket = BasketService.get_basket(basket_id)
    if not basket:
        raise HTTPException(status_code=404, detail="Basket not found")
    _ensure_basket_access(basket, username)
    success = BasketService.delete_basket(basket_id)
    if not success:
        raise HTTPException(status_code=404, detail="Basket not found")
    return {"message": "Basket deleted"}


# Endpoint de historial de precios
@app.get("/price-history/{product_id}")
def get_price_history(
    product_id: str,
    store: str = Query("lider", description="Tienda"),
    days: int = Query(30, ge=1, le=365, description="Dias a consultar"),
):
    logger.info(f"Getting price history for {product_id} in {store}")
    if "|" in product_id or ":" in product_id:
        return _get_canonical_price_history(product_id, store, days)

    history = PriceHistoryService.get_price_history(product_id, store)
    trends = PriceHistoryService.get_price_trends(product_id, store, days=days)

    return {
        "product_id": product_id,
        "store": store,
        "history": [h.model_dump() for h in history],
        "trends": trends
    }


def _get_canonical_price_history(canonical_key: str, store: str, days: int) -> dict:
    from datetime import timedelta
    from sqlalchemy import select

    from backend.db import SessionLocal
    from backend.infrastructure.db.models import PriceRecord, ProductRecord, StoreRecord

    store_name = "Lider" if store == "lider" else "Jumbo" if store == "jumbo" else store.title()
    cutoff = datetime.now(UTC) - timedelta(days=days)
    with SessionLocal() as session:
        statement = (
            select(PriceRecord)
            .join(ProductRecord, ProductRecord.id == PriceRecord.product_id)
            .join(StoreRecord, StoreRecord.id == PriceRecord.store_id)
            .where(ProductRecord.canonical_key == canonical_key)
            .where(StoreRecord.name == store_name)
            .where(PriceRecord.observed_at >= cutoff)
            .order_by(PriceRecord.observed_at)
        )
        records = list(session.scalars(statement).all())

    values = [float(record.value) for record in records]
    trend = "stable"
    if len(values) >= 2:
        first_price = values[0]
        last_price = values[-1]
        if last_price < first_price * 0.95:
            trend = "decreasing"
        elif last_price > first_price * 1.05:
            trend = "increasing"

    return {
        "canonical_key": canonical_key,
        "store": store,
        "days": days,
        "history": [
            {
                "price": float(record.value),
                "observed_at": record.observed_at.isoformat(),
            }
            for record in records
        ],
        "trends": {
            "current_price": values[-1] if values else None,
            "min_price": min(values) if values else None,
            "max_price": max(values) if values else None,
            "trend": trend,
            "history_count": len(values),
        },
    }


# FASE A: Monitoring Endpoints
@app.get("/monitoring/parser-status", include_in_schema=False)
def monitoring_parser_status():
    """Get parser monitoring status (FASE A)."""
    from backend.parser_monitor import get_parser_status
    logger.info("Parser status requested")
    return get_parser_status()


@app.post("/monitoring/parser-check", include_in_schema=False)
def monitoring_parser_check(store: str = Query("lider")):
    """Manually trigger parser change check (FASE A)."""
    from backend.parser_monitor import compare_snapshots
    logger.info(f"Manual parser check triggered for {store}")
    result = compare_snapshots(store)
    return result or {"status": "error"}


@app.get("/monitoring/debug/celery-tasks", include_in_schema=False)
def monitoring_celery_debug():
    """Debug Celery tasks (FASE A - dev only)."""
    from backend.tasks import debug_task
    logger.info("Submitting debug task to Celery")
    
    try:
        task_result = debug_task.delay()
        return {
            "status": "submitted",
            "task_id": task_result.id,
            "task_name": task_result.name,
        }
    except Exception as e:
        logger.error(f"Failed to submit debug task: {e}")
        return {
            "status": "error",
            "error": str(e),
        }


# Endpoints de autenticación
@app.post("/auth/register", response_model=UserResponse)
def register(background: BackgroundTasks, user: UserCreate):
    logger.info(f"Registering user: {user.username}")
    try:
        db_user = AuthService.create_user(user.username, user.email, user.password)
        verify_token = TokenService.create_access_token(
            data={"sub": user.username, "purpose": "email_verify"},
            expires_delta=timedelta(hours=24),
        )
        background.add_task(send_verification_email, user.username, user.email, verify_token)
        return UserResponse(username=db_user.username, email=db_user.email)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/auth/verify")
def verify_email(token: str = Query(...)):
    """Verify email address via signed JWT link."""
    from backend.db import SessionLocal
    from backend.repositories import UserRepository
    payload = TokenService.decode_payload(token)
    if not payload or payload.get("purpose") != "email_verify":
        raise HTTPException(status_code=400, detail="Token de verificación inválido o expirado")
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=400, detail="Token inválido")
    with SessionLocal() as session:
        user = UserRepository(session).get_by_username(username)
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        user.is_verified = True
        session.commit()
    return {"detail": "Email verificado correctamente. Ya puedes iniciar sesión."}


@app.post("/auth/login", response_model=Token)
def login(user: UserLogin):
    logger.info(f"Login attempt: {user.username}")
    db_user = AuthService.authenticate_user(user.username, user.password)
    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = TokenService.create_access_token(data={"sub": db_user.username})
    return Token(access_token=access_token, token_type="bearer")


@app.get("/auth/me", response_model=UserResponse)
def get_current_user(authorization: str = Header(None, description="JWT token (Bearer)")):
    username = _username_from_authorization(authorization, required=True)
    user = AuthService.get_user(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(username=user.username, email=user.email)


@app.post("/auth/logout")
def logout(authorization: str = Header(..., description="Bearer JWT")):
    """Revoke the current token so it cannot be reused after logout."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization[7:]
    payload = TokenService.decode_payload(token)
    if payload:
        jti = payload.get("jti", "")
        exp = payload.get("exp", 0)
        if jti:
            remaining_ttl = max(int(exp - datetime.now(UTC).timestamp()), 0)
            revoke_token(jti, remaining_ttl or ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    return {"detail": "Logged out successfully"}


@app.post("/auth/refresh", response_model=Token)
def refresh_token(authorization: str = Header(None, description="JWT token (Bearer)")):
    """Refresh JWT token: accepts a valid Bearer token, returns a new one with reset TTL."""
    logger.info("Token refresh attempt")
    
    # Validate current token
    username = _username_from_authorization(authorization, required=True)
    
    # Verify user exists
    user = AuthService.get_user(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Create new token with reset TTL
    new_token = TokenService.create_access_token(data={"sub": username})
    logger.info(f"Token refreshed for user: {username}")
    
    return Token(access_token=new_token, token_type="bearer")


@app.post("/auth/forgot-password")
def forgot_password(background: BackgroundTasks, body: dict = Body(...)):
    """Send a password reset link to the user's email."""
    import hashlib
    from backend.db import SessionLocal
    from backend.repositories import UserRepository
    email = (body.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=422, detail="email es requerido")
    with SessionLocal() as session:
        user = UserRepository(session).get_by_email(email)
    if user:
        reset_token = TokenService.create_access_token(
            data={"sub": user.username, "purpose": "pwd_reset"},
            expires_delta=timedelta(hours=1),
        )
        token_hash = hashlib.sha256(reset_token.encode()).hexdigest()
        try:
            from backend.infrastructure.cache.cache import _get_client
            _get_client().set(f"pwd_reset:{user.username}", token_hash, ex=3600)
        except Exception as exc:
            logger.warning("Could not store pwd_reset in Redis: %s", exc)
        background.add_task(send_password_reset_email, user.username, email, reset_token)
    return {"detail": "Si ese email existe, recibirás un enlace de restablecimiento."}


@app.post("/auth/reset-password")
def reset_password(body: dict = Body(...)):
    """Reset the user's password using a valid reset token."""
    import hashlib
    from backend.db import SessionLocal
    from backend.repositories import UserRepository
    from backend.models_auth import validate_password_strength
    token = body.get("token", "")
    new_password = body.get("new_password", "")
    if not token or not new_password:
        raise HTTPException(status_code=422, detail="token y new_password son requeridos")
    failures = validate_password_strength(new_password)
    if failures:
        raise HTTPException(status_code=422, detail="; ".join(failures))
    payload = TokenService.decode_payload(token)
    if not payload or payload.get("purpose") != "pwd_reset":
        raise HTTPException(status_code=400, detail="Token inválido o expirado")
    username = payload.get("sub")
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    try:
        from backend.infrastructure.cache.cache import _get_client
        client = _get_client()
        stored = client.get(f"pwd_reset:{username}")
        if not stored or stored != token_hash:
            raise HTTPException(status_code=400, detail="Token ya utilizado o expirado")
        client.delete(f"pwd_reset:{username}")
    except HTTPException:
        raise
    except Exception as exc:
        # Redis unavailable: fail-closed (reject) — no permitir reset sin verificación
        logger.error("Redis unavailable for pwd_reset validation: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="El servicio de verificación no está disponible. Intenta de nuevo en unos minutos.",
        ) from exc
    with SessionLocal() as session:
        user = UserRepository(session).get_by_username(username)
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        user.hashed_password = pwd_context.hash(new_password)
        session.commit()
    return {"detail": "Contraseña actualizada. Por favor inicia sesión."}


# ============================================================================
# FASE 4: Prometheus Metrics Endpoint
# ============================================================================
@app.get("/metrics", include_in_schema=False)
def metrics():
    """Prometheus metrics endpoint (FASE 4)."""
    if not PROMETHEUS_ENABLED:
        raise HTTPException(status_code=404, detail="Metrics disabled")
    
    metrics_data, content_type = get_metrics_response()
    return Response(content=metrics_data, media_type=content_type)


# ============================================================================
# FASE 4: Backup Management Endpoints
# ============================================================================
@app.post("/admin/backup", include_in_schema=False)
def trigger_backup(username: str = Depends(require_admin)):
    """Manually trigger database backup (FASE 4 - Admin only)."""
    try:
        logger.info(f"Backup triggered by {username}")
        manager = BackupManager()
        results = manager.backup_all()
        
        # Try to upload to S3 if configured
        try:
            s3_result = manager.upload_to_s3()
            results["s3_upload"] = s3_result
        except Exception as e:
            logger.warning(f"S3 upload failed: {e}")
        
        return {
            "status": "success",
            "message": "Backup completed",
            "timestamp": datetime.now(UTC).isoformat(),
            "results": results,
        }
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Backup failed: {str(e)}")


@app.get("/admin/backup-status", include_in_schema=False)
def backup_status(username: str = Depends(require_admin)):
    """Get backup status and list (FASE 4 - Admin only)."""
    try:
        from pathlib import Path
        backup_path = Path("./data/backups")
        
        if not backup_path.exists():
            return {"backups": [], "status": "no_backups"}
        
        backups = []
        for backup_dir in sorted(backup_path.iterdir(), reverse=True)[:10]:
            if backup_dir.is_dir():
                files = list(backup_dir.glob("*"))
                backups.append({
                    "timestamp": backup_dir.name,
                    "files": [str(f.name) for f in files],
                    "size": sum(f.stat().st_size for f in files),
                })
        
        return {
            "status": "success",
            "backups": backups,
            "count": len(backups),
        }
    except Exception as e:
        logger.error(f"Failed to get backup status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/promote", include_in_schema=False)
def promote_user(
    body: dict = Body(...),
    _admin: str = Depends(require_admin),
):
    """Promote a user to a given role (admin only). Body: {username, role}."""
    from backend.db import SessionLocal
    from backend.repositories import UserRepository
    username = body.get("username", "").strip()
    role = body.get("role", "admin").strip()
    if not username:
        raise HTTPException(status_code=422, detail="username es requerido")
    if role not in ("admin", "user"):
        raise HTTPException(status_code=422, detail="role debe ser 'admin' o 'user'")
    with SessionLocal() as session:
        repo = UserRepository(session)
        user = repo.get_by_username(username)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user.role = role
        session.commit()
    logger.info("User '%s' promoted to role='%s' by admin", username, role)
    return {"status": "success", "username": username, "role": role}


@app.post("/admin/promote-bootstrap", include_in_schema=False)
def promote_user_bootstrap(username: str = Query(...)):
    """Bootstrap endpoint: promote a user to admin. Only works when no admins exist."""
    from backend.db import SessionLocal
    from backend.repositories import UserRepository
    with SessionLocal() as session:
        repo = UserRepository(session)
        if repo.count_admins() > 0:
            raise HTTPException(status_code=403, detail="Bootstrap disabled: admins already exist")
        user = repo.get_by_username(username)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user.role = "admin"
        session.commit()
    logger.info("Bootstrap: user '%s' promoted to admin", username)
    return {"status": "success", "username": username, "role": "admin"}


@app.post("/admin/test-alert", include_in_schema=False)
async def test_alert(username: str = Depends(require_admin)):
    """Send a test Slack alert to verify SLACK_WEBHOOK_URL is configured (admin-only)."""
    from backend.alerts import AlertManager, AlertLevel

    logger.info(f"Test alert triggered by {username}")
    sent = await AlertManager.send_slack_alert(
        message="This is a test alert from Radar de Precios. If you see this, Slack alerts are working.",
        title="Test Alert — Radar de Precios",
        level=AlertLevel.INFO,
        additional_info={"triggered_by": username},
    )
    if sent:
        return {"status": "sent", "message": "Test alert sent to Slack successfully"}
    return {"status": "failed", "message": "Failed to send alert — check SLACK_WEBHOOK_URL in config"}


@app.get("/{full_path:path}", include_in_schema=False)
def frontend_static(full_path: str):
    response = _frontend_file_response(full_path)
    if response:
        return response
    raise HTTPException(status_code=404, detail="Not Found")


# ============================================================================
# Signal Handlers for SIGTERM/SIGINT (Docker/K8s)
# ============================================================================
def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}, initiating shutdown...")
    import sys
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
