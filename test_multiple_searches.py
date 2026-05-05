"""
Probar con diferentes búsquedas para ver cantidad de productos
"""
from fastapi.testclient import TestClient
from backend.main import app
from backend.db import reset_db

reset_db()
client = TestClient(app)

search_terms = ["leche", "arroz", "cafe", "detergente", "pan"]

print("=" * 80)
print("PRUEBA: COMPARACION DE RESULTADOS POR PRODUCTO")
print("=" * 80)

for term in search_terms:
    response = client.get(f"/search?q={term}&limit=100&store=lider")
    data = response.json()
    count = len(data.get('results', []))
    print(f"\n{term.upper()}: {count} productos")
    
    if count > 0:
        first = data['results'][0]
        print(f"  Primero: {first.get('name')[:50]}... - ${first.get('price')}")

print("\n" + "=" * 80)
