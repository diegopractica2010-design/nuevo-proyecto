from pydantic import BaseModel, Field


class Product(BaseModel):
    id: str | None = None
    sku: str | None = None
    name: str
    brand: str | None = None
    category: str | None = None
    price: float
    original_price: float | None = None
    discount_percent: int | None = None
    savings_amount: float | None = None
    savings_text: str | None = None
    unit_price: str | None = None
    image: str | None = None
    url: str | None = None
    availability: str | None = None
    in_stock: bool = False
    seller: str | None = None
    badges: list[str] = Field(default_factory=list)
    is_offer: bool = False
    position: int | None = None
    currency: str = "CLP"
    source: str = "lider"


class FacetValue(BaseModel):
    name: str
    count: int


class PriceRange(BaseModel):
    min: float | None = None
    max: float | None = None


class SearchFacets(BaseModel):
    brands: list[FacetValue] = Field(default_factory=list)
    categories: list[FacetValue] = Field(default_factory=list)
    price_range: PriceRange = Field(default_factory=PriceRange)


class SearchStats(BaseModel):
    min_price: float | None = None
    max_price: float | None = None
    average_price: float | None = None
    offer_count: int = 0
    in_stock_count: int = 0


class SearchResponse(BaseModel):
    query: str
    applied_query: str | None = None
    count: int
    results: list[Product] = Field(default_factory=list)
    facets: SearchFacets = Field(default_factory=SearchFacets)
    stats: SearchStats = Field(default_factory=SearchStats)
    suggestions: list[str] = Field(default_factory=list)
    fetched_at: str | None = None
    source: str = "lider"
    source_url: str | None = None
    strategy: str | None = None
    cached: bool = False
    warning: str | None = None
