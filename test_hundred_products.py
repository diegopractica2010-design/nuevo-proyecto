"""
Simulacion de cliente probando con 100 productos
"""
from fastapi.testclient import TestClient
from backend.main import app
from backend.db import reset_db

reset_db()
client = TestClient(app)

print("=" * 80)
print("PRUEBA: BUSQUEDA CON 100 PRODUCTOS")
print("=" * 80)

# Registrar y login
register_response = client.post("/auth/register", json={
    "username": "diego",
    "email": "diego@example.com",
    "password": "password123"
})

login_response = client.post("/auth/login", json={
    "username": "diego",
    "password": "password123"
})

token = login_response.json().get("access_token")
headers = {"Authorization": f"Bearer {token}"}

# Buscar con limit=100
print("\nBuscando 'leche' con limit=100...")
search_response = client.get("/search?q=leche&limit=100&store=lider")
print(f"Status: {search_response.status_code}")

data = search_response.json()
print(f"Total de productos: {len(data.get('results', []))}")
print(f"Stats:")
print(f"  - Min price: ${data.get('stats', {}).get('min_price', 'N/A')}")
print(f"  - Max price: ${data.get('stats', {}).get('max_price', 'N/A')}")
print(f"  - Average price: ${data.get('stats', {}).get('average_price', 'N/A'):.0f}")
print(f"  - In stock: {data.get('stats', {}).get('in_stock_count', 'N/A')}")

print(f"\nPrimeros 5 productos:")
for i, product in enumerate(data.get('results', [])[:5], 1):
    print(f"  {i}. {product['name']}")
    print(f"     Precio: ${product['price']}")
    print(f"     Marca: {product.get('brand', 'N/A')}")

print("\n" + "=" * 80)
print(f"[OK] Sistema devuelve {len(data.get('results', []))} productos")
print("=" * 80)
