"""
Simulación completa como cliente frontend real
Probando cada función que falla
"""
import json
from fastapi.testclient import TestClient
from backend.main import app
from backend.db import reset_db

reset_db()
client = TestClient(app)

print("=" * 80)
print("PRUEBA 1: REGISTRO DE USUARIO")
print("=" * 80)

register_response = client.post("/auth/register", json={
    "username": "diego",
    "email": "diego@example.com",
    "password": "password123"
})

print(f"Status: {register_response.status_code}")
print(f"Response: {register_response.json()}")

if register_response.status_code == 200:
    print("✅ REGISTRO OK")
else:
    print(f"❌ REGISTRO FALLÓ: {register_response.json()}")

print("\n" + "=" * 80)
print("PRUEBA 2: LOGIN")
print("=" * 80)

login_response = client.post("/auth/login", json={
    "username": "diego",
    "password": "password123"
})

print(f"Status: {login_response.status_code}")
print(f"Response: {login_response.json()}")

if login_response.status_code == 200:
    token = login_response.json().get("access_token")
    print(f"✅ LOGIN OK - Token: {token[:20]}...")
    headers = {"Authorization": f"Bearer {token}"}
else:
    print(f"❌ LOGIN FALLÓ")
    headers = {}

print("\n" + "=" * 80)
print("PRUEBA 3: BÚSQUEDA (con la URL que usa el frontend)")
print("=" * 80)

# Frontend llama a /api/search
print("\n3a. Intentando: /api/search?q=leche")
search_response_api = client.get("/api/search?q=leche&limit=36&store=lider")
print(f"Status: {search_response_api.status_code}")

# Backend tiene /search
print("\n3b. Intentando: /search?q=leche")
search_response = client.get("/search?q=leche&limit=36&store=lider")
print(f"Status: {search_response.status_code}")
data = search_response.json()
print(f"Results: {len(data.get('results', []))} productos")
print(f"Warning: {data.get('warning', 'Sin warning')}")
print(f"Strategy: {data.get('strategy', 'N/A')}")

if len(data.get('results', [])) > 0:
    print("✅ BÚSQUEDA CON RESULTADOS")
elif data.get('warning'):
    print(f"⚠️  BÚSQUEDA ENCOLADA (sin resultados aún): {data.get('warning')}")
else:
    print("❌ BÚSQUEDA SIN RESULTADOS Y SIN WARNING")

print("\n" + "=" * 80)
print("PRUEBA 4: CREAR CANASTA (sin autenticación)")
print("=" * 80)

basket_response = client.post("/baskets", json={"name": "Mi canasta"})
print(f"Status: {basket_response.status_code}")
if basket_response.status_code == 200:
    basket = basket_response.json()
    basket_id = basket.get("id")
    print(f"✅ CANASTA CREADA (sin auth): {basket_id}")
    print(f"   user_id: {basket.get('user_id', 'None')}")
else:
    print(f"❌ CREAR CANASTA FALLÓ: {basket_response.json()}")
    basket_id = None

print("\n" + "=" * 80)
print("PRUEBA 5: CREAR CANASTA (CON AUTENTICACIÓN)")
print("=" * 80)

basket_auth_response = client.post("/baskets", 
    json={"name": "Canasta de Diego"},
    headers=headers
)
print(f"Status: {basket_auth_response.status_code}")
if basket_auth_response.status_code == 200:
    basket = basket_auth_response.json()
    basket_id_auth = basket.get("id")
    print(f"✅ CANASTA AUTENTICADA CREADA: {basket_id_auth}")
    print(f"   user_id: {basket.get('user_id')}")
else:
    print(f"❌ CANASTA AUTENTICADA FALLÓ: {basket_auth_response.json()}")
    basket_id_auth = None

print("\n" + "=" * 80)
print("PRUEBA 6: AGREGAR PRODUCTO A CANASTA")
print("=" * 80)

if basket_id:
    add_response = client.post(
        f"/baskets/{basket_id}/items",
        json={
            "product": {
                "id": "sku-123",
                "name": "Leche Entera",
                "price": 1500,
                "source": "lider"
            },
            "quantity": 2
        }
    )
    print(f"Status: {add_response.status_code}")
    if add_response.status_code == 200:
        print("✅ PRODUCTO AGREGADO")
    else:
        print(f"❌ FALLÓ: {add_response.json()}")

print("\n" + "=" * 80)
print("PRUEBA 7: VER CANASTAS DEL USUARIO")
print("=" * 80)

if headers:
    list_response = client.get("/baskets", headers=headers)
    print(f"Status: {list_response.status_code}")
    if list_response.status_code == 200:
        baskets = list_response.json()
        print(f"✅ CANASTAS DEL USUARIO: {len(baskets)} encontradas")
        for b in baskets:
            print(f"   - {b['name']}: {b['item_count']} items")
    else:
        print(f"❌ NO SE PUDIERON CARGAR CANASTAS: {list_response.json()}")
else:
    print("⚠️  SIN AUTENTICACIÓN - SALTANDO")

print("\n" + "=" * 80)
print("RESUMEN DE PROBLEMAS")
print("=" * 80)
