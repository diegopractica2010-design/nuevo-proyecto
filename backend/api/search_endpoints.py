"""Search endpoints con soporte para variantes de productos."""

import logging
from typing import Optional

from fastapi import Body, HTTPException, Query

from backend.config import MAX_RESULTS
from backend.models import SearchResponse
from backend.models_variants import VariantSelectionResponse
from backend.product_variants_service import (
    get_variants_for_selection,
    has_variants,
    resolve_variant_selection,
)
from backend.search_service import SearchServiceError, search_products

logger = logging.getLogger(__name__)


def _result_count(result: SearchResponse | dict) -> int:
    if isinstance(result, dict):
        return len(result.get("results", []))
    return len(result.results)


async def search_endpoint(
    query: Optional[str] = Query(None, min_length=1, description="Nombre del producto"),
    q: Optional[str] = Query(None, min_length=1, description="Alias compatible para query"),
    limit: int = Query(100, ge=1, le=MAX_RESULTS, description="Cantidad máxima de resultados"),
    store: str = Query("lider", description="Tienda a buscar: lider, jumbo"),
    body: Optional[dict] = Body(default=None),
    show_variants: bool = Query(False, description="Si hay variantes, mostrar opciones de selección"),
) -> SearchResponse | VariantSelectionResponse:
    """Busca productos con soporte opcional para mostrar variantes."""
    
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
        if "show_variants" in body:
            show_variants = bool(body.get("show_variants"))

    search_query = query or q
    if not search_query:
        raise HTTPException(status_code=422, detail="Query parameter 'query' or 'q' is required")

    logger.info(f"Search request: query='{search_query}', limit={limit}, store='{store}'")
    try:
        result = await search_products(query=search_query, limit=limit, store=store)
        logger.info(f"Search completed: found {_result_count(result)} products from {store}")
        
        # Chequear si hay variantes y usuario pidió mostrarlas
        if show_variants and isinstance(result, SearchResponse) and has_variants(result.results):
            # Convertir a VariantSelectionResponse
            variant_response = get_variants_for_selection(
                [p.model_dump() if hasattr(p, 'model_dump') else p for p in result.results],
                limit=limit,
            )
            # Agregar metadata original
            variant_response["original_query"] = result.query
            variant_response["store"] = store
            variant_response["cached"] = result.cached
            return variant_response
        
        return result
    except SearchServiceError as exc:
        logger.error(f"Search error for {store}: {exc.message}")
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


async def resolve_variant_endpoint(
    store: str = Query("lider", description="Tienda"),
    query: str = Query(..., min_length=1, description="Query original"),
    variant_id: str = Query(..., description="ID del producto seleccionado"),
) -> dict:
    """Resuelve una selección de variante a un producto específico."""
    logger.info(f"Resolving variant: store={store}, query={query}, variant_id={variant_id}")
    
    try:
        # Hacer búsqueda nueva para obtener productos actuales
        result = await search_products(query=query, limit=50, store=store)
        
        if not isinstance(result, SearchResponse):
            raise HTTPException(status_code=500, detail="Unexpected search result format")
        
        # Encontrar el producto seleccionado
        products = [p.model_dump() if hasattr(p, 'model_dump') else p for p in result.results]
        selected = resolve_variant_selection(variant_id, products)
        
        if not selected:
            raise HTTPException(status_code=404, detail=f"Variant {variant_id} not found")
        
        logger.info(f"Variant resolved: {selected.get('name')}")
        return {
            "success": True,
            "product": selected,
            "original_query": query,
            "store": store,
        }
    except SearchServiceError as exc:
        logger.error(f"Error resolving variant: {exc.message}")
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except Exception as exc:
        logger.error(f"Unexpected error resolving variant: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
