from backend.models import Product, SearchResponse
from backend.shopping_list_service import (
    ShoppingListItem,
    compare_shopping_list,
    score_product_for_query,
    select_best_products,
)


def test_select_best_products_respects_one_kg_requirement():
    products = [
        {"name": "Arroz Grado 1 500 g", "price": 900, "source": "lider", "in_stock": True},
        {"name": "Arroz Grado 1 1 kg", "price": 1200, "source": "lider", "in_stock": True},
        {"name": "Arroz Integral 1 kilo", "price": 1500, "source": "lider", "in_stock": True},
    ]

    selected = select_best_products(products, "arroz 1 kilo")

    assert selected[0]["name"] == "Arroz Grado 1 1 kg"
    assert all("500 g" not in product["name"] for product in selected)


def test_select_best_products_respects_one_liter_requirement():
    products = [
        {"name": "Leche Entera 200 ml", "price": 500, "source": "lider", "in_stock": True},
        {"name": "Leche Entera 1 litro", "price": 1200, "source": "lider", "in_stock": True},
    ]

    selected = select_best_products(products, "leche entera 1 litro")

    assert [product["name"] for product in selected] == ["Leche Entera 1 litro"]


def test_select_best_products_requires_all_long_query_tokens():
    products = [
        {"name": "Leche Descremada 1 litro", "price": 990, "source": "lider", "in_stock": True},
        {"name": "Leche Entera 1 litro", "price": 1200, "source": "jumbo", "in_stock": True},
    ]

    selected = select_best_products(products, "leche entera 1 litro")

    assert [product["name"] for product in selected] == ["Leche Entera 1 litro"]


def test_score_product_rewards_brand_and_product_match():
    maggi = {"name": "Caldo Sabor Carne Maggi 12 Tabletas", "price": 1580, "in_stock": True}
    generic = {"name": "Caldo de Carne 80 g", "price": 990, "in_stock": True}

    assert score_product_for_query(maggi, "caldo de carne maggi") > score_product_for_query(
        generic,
        "caldo de carne maggi",
    )


def test_select_best_products_chooses_cheapest_among_close_matches():
    products = [
        {"name": "Yogurt Los Choicos Pote Natural", "price": 900, "source": "jumbo", "in_stock": True},
        {"name": "Yogurt Los Choicos Pote Frutilla", "price": 850, "source": "lider", "in_stock": True},
        {"name": "Yogurt Familiar Otra Marca", "price": 700, "source": "lider", "in_stock": True},
    ]

    selected = select_best_products(products, "yoghurt pote los choicos")

    assert selected[0]["name"] == "Yogurt Los Choicos Pote Frutilla"


def test_select_best_products_treats_saco_de_carbon_as_charcoal():
    products = [
        {"name": "Shampoo Carbon Activado", "price": 1000, "source": "lider", "in_stock": True},
        {"name": "Carbon Premium 2,5 kg", "price": 3490, "source": "lider", "in_stock": True},
        {"name": "Briquetas de Carbon", "price": 2990, "source": "jumbo", "in_stock": True},
    ]

    selected = select_best_products(products, "saco de carbon")

    assert selected[0]["name"] == "Briquetas de Carbon"


def test_select_best_products_does_not_treat_ramen_as_tallarines():
    products = [
        {"name": "Pasta fideos instantaneos Ramen Sabor Carne", "price": 520, "source": "lider", "in_stock": True},
        {"name": "Fideo Pasta Tallarines N77 Bolsa 400 g", "price": 750, "source": "lider", "in_stock": True},
    ]

    selected = select_best_products(products, "fideos tallarines")

    assert selected[0]["name"] == "Fideo Pasta Tallarines N77 Bolsa 400 g"


def test_compare_shopping_list_isolates_one_store_failure(monkeypatch):
    def fake_search(query, limit, store):
        if store == "lider":
            raise RuntimeError("lider caido")
        return SearchResponse(
            query=query,
            applied_query=query,
            count=1,
            results=[
                Product(
                    name=f"{query} Jumbo 1 kg",
                    price=1990,
                    source="jumbo",
                    in_stock=True,
                )
            ],
        )

    monkeypatch.setattr("backend.shopping_list_service.search_products", fake_search)

    result = compare_shopping_list([ShoppingListItem(query="arroz 1 kilo")])

    item = result["items"][0]
    lider = item["stores"][0]
    jumbo = item["stores"][1]
    assert lider["store"] == "lider"
    assert "error" in lider
    assert jumbo["best"]["source"] == "jumbo"
    assert item["cheapest"]["source"] == "jumbo"
