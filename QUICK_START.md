# Guia Rapida

## Estado

Fase 3 agrega una experiencia usable con login, registro, Bearer token y canastas por usuario. Lider es la tienda principal; Jumbo es experimental. Los datos de usuarios, canastas e historial se guardan en `data/radar_precios.db` por defecto.

## Levantar local

```bash
pip install -r requirements.txt
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8001
```

Para cambiar la base de datos:

```bash
export DATABASE_URL=sqlite:///data/radar_precios.db
```

Abrir:

```text
http://localhost:8001
```

## Buscar productos

```bash
curl "http://localhost:8001/search?query=leche&store=lider&limit=10"
```

Alias compatible:

```bash
curl "http://localhost:8001/search?q=leche&store=lider&limit=10"
```

## Canastas por usuario

Crear:

```bash
curl -X POST http://localhost:8001/baskets \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {token}" \
  -d '{"name": "Compras de la semana"}'
```

Agregar producto:

```bash
curl -X POST http://localhost:8001/baskets/{basket_id}/items \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {token}" \
  -d '{
    "product": {
      "id": "123",
      "name": "Leche Entera 1L",
      "price": 1000,
      "source": "lider"
    },
    "quantity": 2
  }'
```

Listar:

```bash
curl http://localhost:8001/baskets \
  -H "Authorization: Bearer {token}"
```

Editar cantidad:

```bash
curl -X PATCH http://localhost:8001/baskets/{basket_id}/items/{product_id} \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {token}" \
  -d '{"quantity": 3}'
```

## Auth experimental

```bash
curl -X POST http://localhost:8001/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "juan", "email": "juan@example.com", "password": "cambiar123"}'
```

```bash
curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "juan", "password": "cambiar123"}'
```

No usar esta auth en produccion todavia.

## Tests

```bash
python -m pytest tests/ -v
```
