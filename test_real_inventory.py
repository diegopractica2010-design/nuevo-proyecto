"""
Investigacion: Cuantos productos venden realmente Lider y Jumbo
"""
from fastapi.testclient import TestClient
from backend.main import app
from backend.db import reset_db
from backend.scraper import search_lider
from backend.scraper_jumbo import search_jumbo

reset_db()
client = TestClient(app)

print("=" * 80)
print("INVESTIGACION: CANTIDAD REAL DE PRODUCTOS")
print("=" * 80)

# Probar Lider con diferentes límites
print("\n[LIDER]")
print("-" * 40)

search_terms = ["leche", "arroz", "cafe", "detergente", "azucar"]

for term in search_terms:
    try:
        # Llamar al scraper directamente sin límite
        result = search_lider(term, limit=500)  # Pedir 500 para ver qué devuelve
        count = len(result.products)
        print(f"{term.upper()}: {count} productos disponibles")
    except Exception as e:
        print(f"{term.upper()}: Error - {str(e)[:50]}")

# Probar Jumbo
print("\n[JUMBO]")
print("-" * 40)

for term in search_terms:
    try:
        # Llamar al scraper directamente
        result = search_jumbo(term, limit=500)  # Pedir 500 para ver qué devuelve
        count = len(result.products) if hasattr(result, 'products') else len(result)
        print(f"{term.upper()}: {count} productos disponibles")
    except Exception as e:
        print(f"{term.upper()}: Error - {str(e)[:50]}")

print("\n" + "=" * 80)
print("Investigacion completada")
print("=" * 80)
