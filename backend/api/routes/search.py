from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from backend.application.use_cases.search_products import search_products


router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search")
def search(q: str = Query(..., min_length=1, description="Producto a buscar")):
    query = q.strip()
    if not query:
        raise HTTPException(status_code=422, detail="Query parameter 'q' is required")
    return search_products(query)

