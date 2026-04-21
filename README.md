# Radar de Precios

Comparador de precios de supermercados chilenos con datos reales, canastas de compras, historial de precios y autenticación de usuarios.

**Estado**: ✅ Versión 4.0.0 - Todas las Fases Completadas (1-4)

## Novedades v4.0

### Fase 2: Canastas e Historial ✅
- Sistema de canastas de compras con gestión completa
- Historial de precios con análisis de tendencias
- Cálculo automático de totales por tienda

### Fase 3: Usuarios ✅
- Autenticación con JWT tokens
- Registro y login de usuarios
- Canastas asociadas a perfiles personales

### Fase 4: Escalabilidad ✅
- Redis para cache distribuido
- Celery para tareas asíncronas
- Logging estructurado
- Preparado para múltiples workers

**Ver documentación completa**: [COMPLETE_STATUS.md](COMPLETE_STATUS.md) | [IMPLEMENTATION_PHASES_2_3_4.md](IMPLEMENTATION_PHASES_2_3_4.md)

## Características

- ✅ Búsqueda en tiempo real de productos en Lider.cl y Jumbo.cl
- ✅ Sistema de canastas de compras con cálculo de totales
- ✅ Historial de precios y análisis de tendencias
- ✅ Autenticación de usuarios con JWT
- ✅ Filtros avanzados por precio, ofertas, stock y favoritos
- ✅ Historial de búsquedas y productos favoritos
- ✅ API RESTful con FastAPI
- ✅ Interfaz web responsive con múltiples secciones
- ✅ Infraestructura preparada para escalabilidad (Redis, Celery)

## Instalación

1. Clona el repositorio:
   ```bash
   git clone <url-del-repo>
   cd nuevo-proyecto
   ```

2. Crea un entorno virtual:
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   ```

3. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   pip install pytest  # Para desarrollo
   ```

## Ejecución

### Opción 1: Script de inicio (Recomendado)
```bash
./run.sh
```

Para ejecutar con tests primero:
```bash
./run.sh --test
```

### Opción 2: Manual
```bash
# Activar entorno virtual
source venv/bin/activate

# Configurar PYTHONPATH
export PYTHONPATH=$(pwd)

# Iniciar servidor con recarga automática
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8001
```

### Producción
```bash
export PYTHONPATH=$(pwd)
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8001
```

Accede a http://localhost:8001

## Tests

```bash
export PYTHONPATH=$(pwd)
pytest tests/
```

## API

### Búsqueda
- `GET /search?q={query}&limit={limit}&store={store}`: Búsqueda de productos
  - `store`: `lider` o `jumbo` (default: `lider`)

### Canastas (Fase 2)
- `POST /baskets`: Crear nueva canasta
- `GET /baskets`: Listar canastas
- `GET /baskets/{id}`: Obtener detalle
- `POST /baskets/{id}/items`: Agregar producto
- `DELETE /baskets/{id}/items/{product_id}`: Remover producto
- `DELETE /baskets/{id}`: Eliminar canasta

### Historial de Precios (Fase 2)
- `GET /price-history/{product_id}?store={store}`: Obtener historial y tendencias

### Autenticación (Fase 3)
- `POST /auth/register`: Registrar usuario
- `POST /auth/login`: Iniciar sesión
- `GET /auth/me?token={token}`: Obtener usuario actual

### Sistema
- `GET /`: Interfaz web
- `GET /health`: Estado del servicio

## Estructura del Proyecto

```
nuevo-proyecto/
├── backend/
│   ├── main.py          # API FastAPI
│   ├── config.py        # Configuración
│   ├── models.py        # Modelos de datos
│   ├── scraper.py       # Lógica de scraping
│   ├── parser.py        # Parsing de HTML
│   └── search_service.py # Servicio de búsqueda
├── frontend/
│   ├── index.html       # Página principal
│   ├── app.js           # Lógica frontend
│   └── style.css        # Estilos
├── tests/               # Tests unitarios
└── requirements.txt     # Dependencias
```

## Mejoras Recientes

### Multi-Tienda
- ✅ Soporte para búsqueda en Lider.cl y Jumbo.cl
- ✅ Selector de tienda en la interfaz web
- ✅ Cache independiente por tienda
- ✅ Arquitectura modular para agregar más tiendas fácilmente

### Mejoras Técnicas
- ✅ Entorno virtual configurado
- ✅ Logging estructurado
- ✅ Tests de API con httpx
- ✅ Script de inicio automatizado
- ✅ Configuración VS Code con tasks
- ✅ Linting con Black y Flake8

## Contribución

1. Crea una rama para tu feature
2. Escribe tests para nuevos cambios
3. Asegura que todos los tests pasen
4. Envía un pull request

## Licencia

MIT