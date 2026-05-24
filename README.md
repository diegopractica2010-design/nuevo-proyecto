# Radar de Precios

Comparador local de precios para supermercados chilenos. La app permite buscar productos en Lider y Jumbo, comparar una lista de compras, filtrar resultados, guardar favoritos en el navegador y crear canastas simples.

## Estado Real

El foco actual es estabilizar el flujo principal:

- `GET /search` busca productos en vivo por tienda (`lider` o `jumbo`).
- `POST /shopping-list/compare` compara Lider y Jumbo por item y devuelve la mejor opcion encontrada.
- El frontend es una app Next.js/React/TypeScript exportada como estatico y servida por FastAPI.
- Redis se usa como cache compartido cuando esta disponible; en desarrollo hay fallback local en memoria.
- La infraestructura de monitoreo, Celery, backups y despliegue existe en el repo, pero no debe tratarse como garantia de produccion lista sin validacion operacional.

## Requisitos

- Python 3.11+
- Redis opcional para cache compartido
- Docker opcional para levantar servicios auxiliares

## Desarrollo Local

```bash
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

cd frontend
$env:NODE_OPTIONS='--use-system-ca' # solo si npm no confia en el CA local de Windows
npm install
npm run build
cd ..

python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8001
```

Abrir:

- App: http://localhost:8001
- API docs: http://localhost:8001/docs

Para trabajar solo en UI:

```bash
cd frontend
$env:NEXT_PUBLIC_API_BASE_URL='http://localhost:8001'
npm run dev
```

## Frontend

- Stack: Next.js App Router, React, TypeScript, TailwindCSS, shadcn/ui-style primitives, Framer Motion, Zustand y React Query.
- Estructura: `src/app`, `src/features`, `src/components`, `src/services`, `src/hooks`, `src/stores`, `src/layouts`, `src/types`.
- Build: `npm run build` genera `frontend/out`, que FastAPI sirve desde `/` y `/_next`.
- Estado servidor: React Query gestiona `/search`, `/shopping-list/compare` y `/health/scraper`.
- Estado local: Zustand mantiene tienda activa, favoritos y busquedas recientes.

## API Principal

- `GET /health` - health check simple.
- `GET /search?q=arroz&store=lider` - busqueda en una tienda.
- `POST /shopping-list/compare` - comparacion de lista entre Lider y Jumbo.
- `POST /auth/register`, `POST /auth/login`, `GET /auth/me` - autenticacion.
- `POST /baskets`, `GET /baskets`, `POST /baskets/{id}/items` - canastas.
- `GET /price-history/{product_id}` - historial de precios.

## Tests

```bash
.\venv\Scripts\python.exe -m pytest -q
cd frontend
npm run typecheck
npm run build
```

Los tests live contra supermercados estan desactivados por defecto para evitar fallas por red o anti-bot externo. Para ejecutarlos:

```bash
$env:RUN_LIVE_ACCEPTANCE='1'
.\venv\Scripts\python.exe -m pytest tests/test_acceptance.py -q
```

## Configuracion Relevante

- `LIVE_STORE_QUERIES_ENABLED=true` habilita consultas en vivo.
- `COMPLIANCE_STRICT_MODE=false` deja las verificaciones estrictas como opt-in.
- `STORE_ROBOTS_ALLOW_ON_ERROR=true` evita bloquear desarrollo local si robots no responde.
- `RATE_LIMIT_REQUESTS_PER_MINUTE=60` define el limite por defecto.
- `CACHE_TTL_SECONDS=600` y `STALE_CACHE_TTL_SECONDS=1800` controlan cache fresco/stale.

## Documentacion

- `QUICK_START.md` mantiene instrucciones rapidas.
- `DEPLOYMENT.md` conserva notas de despliegue.
- Documentos historicos de fases y estado fueron movidos a `docs-archive/`.
