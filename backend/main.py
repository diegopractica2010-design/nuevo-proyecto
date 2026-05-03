import logging
import signal
import json
from datetime import UTC, datetime
from fastapi import Body, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
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
from backend.search_service import SearchServiceError, search_products
from backend.basket_service import BasketService, PriceHistoryService
from backend.models_baskets import Basket, BasketSummary
from backend.auth import AuthService, TokenService
from backend.models_auth import Token, UserCreate, UserLogin, UserResponse
from backend.api.routes.search import router as api_search_router

# FASE 4: Import new modules
from backend.security import SecurityHeadersMiddleware
from backend.metrics import (
    metrics_middleware,
    get_metrics_response,
    record_search_request,
    record_search_duration,
)
from backend.backup import BackupManager

logger = logging.getLogger(__name__)

# ============================================================================
# FastAPI App Initialization
# ============================================================================
app = FastAPI(
    title="Radar de Precios",
    version="0.4.0-phase4",
    description="Comparador de precios de supermercados chilenos (Fase 4: Producción & Operación)"
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
app.include_router(api_search_router)

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


@app.get("/", include_in_schema=False)
def index():
    logger.info("Serving index page")
    return FileResponse(FRONTEND_DIR / "index.html")


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
    status_code = 200 if check.get("status") == "ok" else 503
    return check


@app.get("/health/ready", include_in_schema=False)
def health_ready():
    """Readiness probe (K8s ready)."""
    checker = get_health_checker()
    check = checker.check_ready()
    status_code = 200 if check.get("ready") else 503
    return check


@app.get("/health/full", include_in_schema=False)
def health_full():
    """Full system health check (diagnostics)."""
    checker = get_health_checker()
    check = checker.check_full()
    return check


@app.get("/health/scraper", include_in_schema=False)
def scraper_health():
    """Return the last saved scraper monitor status without running a new check."""
    try:
        from backend.parser_monitor import get_status

        return get_status()
    except Exception as exc:
        logger.warning("scraper health check failed: %s", exc)
        return {"status": "unavailable", "error": str(exc)}


@app.get("/search", response_model=SearchResponse)
def search(
    query: Optional[str] = Query(None, min_length=1, description="Nombre del producto"),
    q: Optional[str] = Query(None, min_length=1, description="Alias compatible para query"),
    limit: int = Query(36, ge=1, le=MAX_RESULTS, description="Cantidad máxima de resultados"),
    store: str = Query("lider", description="Tienda a buscar: lider, jumbo"),
):
    search_query = query or q
    if not search_query:
        raise HTTPException(status_code=422, detail="Query parameter 'query' or 'q' is required")

    logger.info(f"Search request: query='{search_query}', limit={limit}, store='{store}'")
    try:
        result = search_products(query=search_query, limit=limit, store=store)
        logger.info(f"Search completed: found {_result_count(result)} products from {store}")
        return result
    except SearchServiceError as exc:
        logger.error(f"Search error for {store}: {exc.message}")
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


# Endpoints de canastas
@app.post("/baskets", response_model=Basket)
def create_basket(
    name: str = Body(..., embed=True),
    user_id: Optional[str] = None,
    authorization: Optional[str] = Header(None),
):
    username = _username_from_authorization(authorization)
    owner_id = username or user_id
    logger.info(f"Creating basket: {name}")
    basket = BasketService.create_basket(name, owner_id)
    return basket


@app.get("/baskets", response_model=list[BasketSummary])
def get_baskets(authorization: str = Header(...)):
    username = _username_from_authorization(authorization, required=True)
    if not username:
        raise HTTPException(status_code=401, detail="Autenticacion requerida")
    owner_id = username
    logger.info(f"Getting baskets for user: {owner_id}")
    return BasketService.get_user_baskets(owner_id)


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
def get_price_history(product_id: str, store: str = Query("lider", description="Tienda")):
    logger.info(f"Getting price history for {product_id} in {store}")
    history = PriceHistoryService.get_price_history(product_id, store)
    trends = PriceHistoryService.get_price_trends(product_id, store)
    return {
        "product_id": product_id,
        "store": store,
        "history": [h.model_dump() for h in history],
        "trends": trends
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
def register(user: UserCreate):
    logger.info(f"Registering user: {user.username}")
    try:
        db_user = AuthService.create_user(user.username, user.email, user.password)
        return UserResponse(username=db_user.username, email=db_user.email)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


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


# ============================================================================
# FASE 4: Prometheus Metrics Endpoint
# ============================================================================
@app.get("/metrics", include_in_schema=False)
def metrics():
    """Prometheus metrics endpoint (FASE 4)."""
    if not PROMETHEUS_ENABLED:
        raise HTTPException(status_code=404, detail="Metrics disabled")
    
    metrics_data, content_type = get_metrics_response()
    return metrics_data


# ============================================================================
# FASE 4: Backup Management Endpoints
# ============================================================================
@app.post("/admin/backup", include_in_schema=False)
def trigger_backup(authorization: Optional[str] = Header(None)):
    """Manually trigger database backup (FASE 4 - Admin only)."""
    # In production, verify admin token
    username = _username_from_authorization(authorization)
    if not username:  # Simple admin check - use proper RBAC in production
        raise HTTPException(status_code=403, detail="Admin access required")
    
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
def backup_status(authorization: Optional[str] = Header(None)):
    """Get backup status and list (FASE 4 - Admin only)."""
    username = _username_from_authorization(authorization)
    if not username:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        from pathlib import Path
        backup_path = Path("./data/backups")
        
        if not backup_path.exists():
            return {"backups": [], "status": "no_backups"}
        
        backups = []
        for backup_dir in sorted(backup_path.iterdir(), reverse=True)[:10]:
            if backup_dir.is_dir():
                backups.append({
                    "timestamp": backup_dir.name,
                    "files": list(backup_dir.glob("*")),
                    "size": sum(f.stat().st_size for f in backup_dir.glob("*")),
                })
        
        return {
            "status": "success",
            "backups": backups,
            "count": len(backups),
        }
    except Exception as e:
        logger.error(f"Failed to get backup status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# FASE 4: Graceful Shutdown Handlers
# ============================================================================
@app.on_event("startup")
async def startup_event():
    """Startup event - initialize resources."""
    logger.info("=" * 80)
    logger.info("Radar de Precios - Fase 4 (Producción & Operación)")
    logger.info(f"Started at {datetime.now(UTC).isoformat()}")
    logger.info("=" * 80)
    
    # Start backup scheduler if enabled
    try:
        from backend.tasks import schedule_backups
        schedule_backups()
        logger.info("Backup scheduler started")
    except Exception as e:
        logger.warning(f"Failed to start backup scheduler: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event - cleanup resources gracefully."""
    logger.info("=" * 80)
    logger.info("Shutting down Radar de Precios...")
    logger.info("=" * 80)
    
    # Graceful shutdown steps:
    # 1. Stop accepting new requests (handled by FastAPI)
    # 2. Wait for pending tasks
    # 3. Close database connections
    # 4. Close Redis connections
    
    try:
        # Wait for Celery tasks to complete
        logger.info("Waiting for pending Celery tasks...")
        # In production, use timeout and force kill if needed
        from backend.celery_app import celery_app
        celery_app.control.inspect().active()  # Wait for active tasks
    except Exception as e:
        logger.warning(f"Error waiting for Celery tasks: {e}")
    
    # Close database connections
    try:
        from backend.db import engine

        engine.dispose()
        logger.info("Database connection pool disposed")
    except Exception as e:
        logger.warning(f"Error closing database: {e}")
    
    logger.info("Shutdown complete")


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
