# 🚀 Guía Rápida - Nuevas Funcionalidades

## Canastas de Compras

### Crear una Canasta
```bash
curl -X POST http://localhost:8001/baskets \
  -H "Content-Type: application/json" \
  -d '{"name": "Compras de la semana"}'
```

Respuesta:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Compras de la semana",
  "items": [],
  "created_at": "2026-04-20T10:00:00",
  "updated_at": "2026-04-20T10:00:00"
}
```

### Agregar Producto a Canasta
```bash
curl -X POST http://localhost:8001/baskets/550e8400-e29b-41d4-a716-446655440000/items \
  -H "Content-Type: application/json" \
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

### Ver Canasta
```bash
curl http://localhost:8001/baskets/550e8400-e29b-41d4-a716-446655440000
```

---

## Historial de Precios

### Obtener Tendencias de Precio
```bash
curl http://localhost:8001/price-history/123?store=lider
```

Respuesta:
```json
{
  "product_id": "123",
  "store": "lider",
  "history": [
    {"product_id": "123", "store": "lider", "price": 1000, "date": "2026-04-20T10:00:00"},
    {"product_id": "123", "store": "lider", "price": 950, "date": "2026-04-20T11:00:00"},
    {"product_id": "123", "store": "lider", "price": 900, "date": "2026-04-20T12:00:00"}
  ],
  "trends": {
    "current_price": 900,
    "min_price": 900,
    "max_price": 1000,
    "trend": "decreasing",
    "history_count": 3
  }
}
```

---

## Autenticación

### Registrar Usuario
```bash
curl -X POST http://localhost:8001/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "juanperez",
    "email": "juan@example.com",
    "password": "micontraseña123"
  }'
```

### Iniciar Sesión
```bash
curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "juanperez",
    "password": "micontraseña123"
  }'
```

Respuesta:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Verificar Token
```bash
curl "http://localhost:8001/auth/me?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

## Búsqueda Multi-Tienda

### Búsqueda en Lider (default)
```bash
curl "http://localhost:8001/search?query=leche&store=lider&limit=10"
```

### Búsqueda en Jumbo
```bash
curl "http://localhost:8001/search?query=leche&store=jumbo&limit=10"
```

---

## Frontend - Nuevas Funcionalidades

### 1. Selector de Tienda
En el formulario de búsqueda, antes de hacer clic en "Buscar":
- Selecciona "Líder" o "Jumbo" en el dropdown

### 2. Agregar a Canasta
En cada producto:
- Click en botón "Agregar a canasta"
- Ingresar ID de canasta cuando se pida
- El producto se añade automáticamente

### 3. Ver Canastas
- Click en "Canastas" en la navegación superior
- Ver lista de canastas creadas
- Click en canasta para ver detalle
- Ver total de compra por tienda

---

## Flujo Completo - Ejemplo

### 1. Crear Canasta
```json
POST /baskets
Body: {"name": "Canasta Lunes"}
```

### 2. Buscar Productos
```
GET /search?query=leche&store=lider&limit=10
```

### 3. Agregar a Canasta
```json
POST /baskets/{id}/items
Body: {
  "product": { ... producto de búsqueda ... },
  "quantity": 2
}
```

### 4. Verificar Tendencia de Precio
```
GET /price-history/{product_id}?store=lider
```

### 5. Ver Total
```
GET /baskets/{id}
```

---

## Configuración Avanzada

### Redis
```bash
# Instalar Redis (si no está instalado)
# Debian/Ubuntu
sudo apt-get install redis-server

# macOS
brew install redis

# Iniciar Redis
redis-server
```

### Variables de Entorno
```bash
# .env file o export
export REDIS_URL=redis://localhost:6379/0
export CELERY_BROKER_URL=redis://localhost:6379/0
export SECRET_KEY=tu-clave-secreta-muy-segura
```

---

## Troubleshooting

### Error: ModuleNotFoundError
```bash
# Solución
source venv/bin/activate
pip install -e ".[dev]"
export PYTHONPATH=$(pwd)
```

### Redis no conecta
```bash
# Verificar si Redis está corriendo
redis-cli ping
# Debe responder "PONG"
```

### Token expirado
```bash
# Los tokens expiran en 30 minutos
# Hacer login nuevamente para obtener nuevo token
```

---

## Próximos Pasos

1. **Base de Datos**: Reemplazar almacenamiento en memoria con PostgreSQL
2. **Más Tiendas**: Agregar Falabella, Paris, ABC, Santa Isabel
3. **Alertas**: Notificaciones por email de cambios de precio
4. **Dashboard**: Panel de analytics personal
5. **Mobile**: PWA o app nativa

---

## Recursos

- API Docs: http://localhost:8001/docs (Swagger)
- ReDoc: http://localhost:8001/redoc
- Code: Ver archivos en `backend/` y `frontend/`
- Tests: `pytest tests/ -v`