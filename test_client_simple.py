"""
Simulacion completa como cliente frontend real
Sin emojis para que PowerShell lo pueda procesar
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
if register_response.status_code == 200:
    print("[OK] REGISTRO OK")
else:
    print(f"[ERROR] REGISTRO FALLO: {register_response.json()}")

print("\n" + "=" * 80)
print("PRUEBA 2: LOGIN")
print("=" * 80)

login_response = client.post("/auth/login", json={
    "username": "diego",
    "password": "password123"
})

print(f"Status: {login_response.status_code}")
if login_response.status_code == 200:
    token = login_response.json().get("access_token")
    print(f"[OK] LOGIN OK - Token: {token[:20]}...")
    headers = {"Authorization": f"Bearer {token}"}
else:
    print(f"[ERROR] LOGIN FALLO")
    headers = {}

print("\n" + "=" * 80)
print("PRUEBA 3: BUSQUEDA (AHORA DEBE DEVOLVER RESULTADOS)")
print("=" * 80)

search_response = client.get("/search?q=leche&limit=36&store=lider")
print(f"Status: {search_response.status_code}")
data = search_response.json()
print(f"Results: {len(data.get('results', []))} productos")
print(f"Warning: {data.get('warning', 'Sin warning')}")
print(f"Strategy: {data.get('strategy', 'N/A')}")
print(f"Cached: {data.get('cached', False)}")

if len(data.get('results', [])) > 0:
    print("[OK] BUSQUEDA CON RESULTADOS!")
    # Mostrar el primero
    first = data['results'][0]
    print(f"  - {first.get('name', 'N/A')}: ${first.get('price', 'N/A')}")
elif data.get('warning'):
    print(f"[WARNING] BUSQUEDA SIN RESULTADOS: {data.get('warning')}")
else:
    print("[ERROR] BUSQUEDA SIN RESULTADOS Y SIN WARNING")

print("\n" + "=" * 80)
print("PRUEBA 4: CREAR CANASTA (CON AUTENTICACION)")
print("=" * 80)

basket_auth_response = client.post("/baskets", 
    json={"name": "Canasta de Diego"},
    headers=headers
)
print(f"Status: {basket_auth_response.status_code}")
if basket_auth_response.status_code == 200:
    basket = basket_auth_response.json()
    basket_id_auth = basket.get("id")
    print(f"[OK] CANASTA CREADA: {basket_id_auth[:8]}...")
    print(f"   user_id: {basket.get('user_id')}")
else:
    print(f"[ERROR] CANASTA FALLO: {basket_auth_response.json()}")
    basket_id_auth = None

print("\n" + "=" * 80)
print("PRUEBA 5: VER CANASTAS DEL USUARIO")
print("=" * 80)

if headers:
    list_response = client.get("/baskets", headers=headers)
    print(f"Status: {list_response.status_code}")
    if list_response.status_code == 200:
        baskets = list_response.json()
        print(f"[OK] CANASTAS DEL USUARIO: {len(baskets)} encontradas")
        for b in baskets:
            print(f"   - {b['name']}: {b['item_count']} items")
    else:
        print(f"[ERROR] NO SE PUDIERON CARGAR CANASTAS")

print("\n" + "=" * 80)
print("RESUMEN")
print("=" * 80)
print("[OK] = Funciona correctamente")
print("[ERROR] = No funciona")
print("[WARNING] = Funciona pero con limitaciones")
