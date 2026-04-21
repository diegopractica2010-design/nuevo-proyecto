import logging
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional

from backend.config import FRONTEND_DIR, MAX_RESULTS
from backend.models import SearchResponse
from backend.search_service import SearchServiceError, search_products
from backend.basket_service import BasketService, PriceHistoryService
from backend.models_baskets import Basket, BasketSummary
from backend.auth import AuthService, TokenService
from backend.models_auth import Token, UserCreate, UserLogin, UserResponse

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Radar de Precios", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/", include_in_schema=False)
def index():
    logger.info("Serving index page")
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health", include_in_schema=False)
def health():
    logger.info("Health check requested")
    return {"status": "ok"}


@app.get("/search", response_model=SearchResponse)
def search(
    query: str = Query(..., min_length=1, description="Nombre del producto"),
    limit: int = Query(36, ge=1, le=MAX_RESULTS, description="Cantidad máxima de resultados"),
    store: str = Query("lider", description="Tienda a buscar: lider, jumbo"),
):
    logger.info(f"Search request: query='{query}', limit={limit}, store='{store}'")
    try:
        result = search_products(query=query, limit=limit, store=store)
        logger.info(f"Search completed: found {len(result.results)} products from {store}")
        return result
    except SearchServiceError as exc:
        logger.error(f"Search error for {store}: {exc.message}")
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


# Endpoints de canastas
@app.post("/baskets", response_model=Basket)
def create_basket(name: str = Body(..., embed=True), user_id: Optional[str] = None):
    logger.info(f"Creating basket: {name}")
    basket = BasketService.create_basket(name, user_id)
    return basket


@app.get("/baskets", response_model=list[BasketSummary])
def get_baskets(user_id: Optional[str] = None):
    logger.info(f"Getting baskets for user: {user_id}")
    return BasketService.get_user_baskets(user_id)


@app.get("/baskets/{basket_id}", response_model=Basket)
def get_basket(basket_id: str):
    logger.info(f"Getting basket: {basket_id}")
    basket = BasketService.get_basket(basket_id)
    if not basket:
        raise HTTPException(status_code=404, detail="Basket not found")
    return basket


@app.post("/baskets/{basket_id}/items")
def add_to_basket(basket_id: str, product: dict = Body(...), quantity: int = Body(1, embed=True)):
    logger.info(f"Adding to basket {basket_id}: {product.get('name', 'unknown')}")
    success = BasketService.add_to_basket(basket_id, product, quantity)
    if not success:
        raise HTTPException(status_code=404, detail="Basket not found")
    return {"message": "Item added to basket"}


@app.delete("/baskets/{basket_id}/items/{product_id}")
def remove_from_basket(basket_id: str, product_id: str):
    logger.info(f"Removing from basket {basket_id}: {product_id}")
    success = BasketService.remove_from_basket(basket_id, product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Basket or item not found")
    return {"message": "Item removed from basket"}


@app.delete("/baskets/{basket_id}")
def delete_basket(basket_id: str):
    logger.info(f"Deleting basket: {basket_id}")
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
def get_current_user(token: str = Query(..., description="JWT token")):
    username = TokenService.verify_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = AuthService.get_user(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(username=user.username, email=user.email)
