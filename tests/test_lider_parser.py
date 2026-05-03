"""Tests del parser de Lider."""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.infrastructure.scrapers.lider import LiderScraper, _parse_price_string


FIXTURE_PATH = Path("tests/fixtures/lider_leche.html")


@pytest.fixture
def scraper():
    return LiderScraper()


@pytest.fixture
def fixture_html():
    if not FIXTURE_PATH.exists():
        pytest.skip(
            f"Fixture no encontrado: {FIXTURE_PATH}. "
            "Ejecutar el comando de regeneracion de fixtures del README/prompt."
        )
    return FIXTURE_PATH.read_text(encoding="utf-8")


def test_fixture_contiene_next_data(fixture_html):
    """El HTML de Lider debe tener el JSON embebido de Next.js."""
    assert "__NEXT_DATA__" in fixture_html, (
        "El HTML de Lider ya no tiene __NEXT_DATA__. "
        "El sitio puede haber cambiado de Next.js a otro framework."
    )


def test_parser_extrae_productos_desde_fixture(scraper, fixture_html):
    """El parser debe extraer al menos 1 producto del HTML del fixture."""
    products = scraper.parse_products(fixture_html, limit=10)
    assert len(products) >= 1, (
        "El parser no extrae productos del fixture. "
        f"HTML tiene __NEXT_DATA__: {'__NEXT_DATA__' in fixture_html}."
    )


def test_productos_tienen_nombre_y_precio(scraper, fixture_html):
    """Todos los productos extraidos deben tener nombre y precio validos."""
    products = scraper.parse_products(fixture_html, limit=10)
    for product in products:
        assert product.name and len(product.name) > 3, f"Nombre invalido: {product.name!r}"
        assert product.price > 100, f"Precio sospechoso: {product.price}"
        assert product.price < 100_000, f"Precio demasiado alto: {product.price}"


def test_productos_tienen_canonicalizacion(scraper, fixture_html):
    """Todos los productos deben tener un producto canonicalizado."""
    products = scraper.parse_products(fixture_html, limit=5)
    for product in products:
        assert product.product is not None
        assert product.product.canonical_key, f"canonical_key vacio para: {product.name}"


def test_limit_respetado(scraper, fixture_html):
    """El limite de productos debe respetarse."""
    products = scraper.parse_products(fixture_html, limit=3)
    assert len(products) <= 3


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("$1.990", 1990.0),
        ("$ 2.500", 2500.0),
        ("$10.990", 10990.0),
        ("$990", 990.0),
        ("Precio: $3.299", 3299.0),
        ("sin precio", None),
        ("", None),
    ],
)
def test_parse_price_string(text, expected):
    result = _parse_price_string(text)
    assert result == expected


@pytest.mark.skip(reason="Test de integracion: requiere red.")
def test_scraper_con_lider_real():
    products = LiderScraper().search("leche", limit=5)
    assert len(products) >= 1
    for product in products:
        assert product.name
        assert product.price > 100
