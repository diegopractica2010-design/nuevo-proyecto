# FASE A: ESTABILIZACIÓN TÉCNICA

**Estado**: En ejecución  
**Objetivo**: Sistema NO cae bajo uso normal (4-6 semanas)  
**Última actualización**: 27 de abril, 2026  

---

## Cambios Implementados (COMPLETADO)

### 1. ✅ Infraestructura - Docker Compose

**Archivos creados:**
- `docker-compose.yml`: Orquestación de servicios (Redis, PostgreSQL, app, Celery workers, Celery beat)
- `Dockerfile`: Container image para la aplicación
- `.env.example`: Variables de entorno actualizadas

**Servicios incluidos:**
```
redis:7-alpine          - Cache + Task queue broker
postgres:16-alpine      - Database (para Fase C, opcional en Fase A)
app                     - FastAPI application (auto-reload en dev)
celery_worker           - Async task workers (4 workers, escalable)
celery_beat             - Scheduler para tareas periódicas
```

**Uso:**
```bash
# Development (localhost)
docker-compose up

# Production-like (PostgreSQL + Redis)
docker-compose up -d

# Ver logs
docker-compose logs -f app
docker-compose logs -f celery_worker
```

**Networking:**
- Todos los servicios en red `radar-network`
- Health checks configurados
- Volumes para persistencia (Redis data, PostgreSQL data)

---

### 2. ✅ Rate Limiting Real (Redis-backed)

**Archivo**: `backend/rate_limiter.py`

**Características:**
- ✅ Algoritmo sliding window (ventana deslizante)
- ✅ Basado en Redis (distribuido, multi-instancia)
- ✅ Graceful degradation (si Redis falla, permite requests)
- ✅ Configurable por IP
- ✅ Headers HTTP: X-RateLimit-*, Retry-After

**Configuración:**
```python
RATE_LIMIT_REQUESTS_PER_MINUTE = 10  # Default
RATE_LIMIT_BURST_SIZE = 15            # Permitir ráfagas
RATE_LIMIT_WINDOW_SECONDS = 60        # Ventana de tiempo
```

**Middleware integrado:**
- En `middleware.py`: `RateLimitMiddleware` 
- Aplica a todos los endpoints excepto `/health`, `/docs`, `/openapi.json`
- Respuesta 429 (Too Many Requests) con retry_after

**Monitoreo:**
```
Headers de respuesta:
  X-RateLimit-Limit: 10
  X-RateLimit-Remaining: 5
  X-RateLimit-Window: 60

Si limitado (429):
  Retry-After: 30
  X-RateLimit-Window: 60
```

---

### 3. ✅ Celery + Redis Queue (Async Scraping)

**Archivos:**
- `backend/celery_app.py`: Configuración de Celery (broker, backend, beat schedule)
- `backend/tasks.py`: Tareas async (búsquedas, mantenimiento)

**Tareas implementadas:**
1. `search_lider_async()`: Buscar en Lider async
2. `search_jumbo_async()`: Buscar en Jumbo async
3. `backup_database()`: Backup periódico (placeholder)
4. `monitor_parser_changes()`: Monitor cambios HTML (placeholder)
5. `cleanup_cache()`: Limpieza de cache (placeholder)

**Configuración:**
```python
broker = redis://localhost:6379/1
result_backend = redis://localhost:6379/2
task_serializer = "json"
task_time_limit = 30 min (hard)
task_soft_time_limit = 25 min
worker_prefetch_multiplier = 1
```

**Ejecución:**
```bash
# Worker
celery -A backend.celery_app worker --loglevel=info --concurrency=4

# Beat (scheduler)
celery -A backend.celery_app beat --loglevel=info

# O con docker-compose
docker-compose up celery_worker celery_beat
```

**Estado**: Tareas implementadas y testeable. Aún no integradas en search_service.py (Fase B).

---

### 4. ✅ Logging Centralizado

**Archivo**: `backend/logging_setup.py`

**Características:**
- ✅ Logs estruturados en JSON (para análisis)
- ✅ Múltiples handlers: console, file, error file
- ✅ Rotación automática de logs (10 MB x 10 backups)
- ✅ Logs separados por módulo (scraper, app, etc.)
- ✅ Integración con Sentry (si SENTRY_DSN definido)

**Configuración:**
```
Archivos de log (en data/logs/):
  app.log           - General application logs (JSON)
  errors.log        - Error logs detallados
  scraper.log       - Logs de scraping (JSON)
```

**Niveles:**
```
LOG_LEVEL = INFO (configurable via .env)
  - DEBUG: Detalles internos
  - INFO: Eventos importantes
  - WARNING: Situaciones inesperadas
  - ERROR: Errores que requieren atención
```

**Sentry (Opcional):**
```
Si SENTRY_DSN definido (.env), automáticamente:
  - Captura excepciones no manejadas
  - Envía traces de performance
  - Integración con FastAPI, SQLAlchemy, Celery
```

---

### 5. ✅ Configuración Mejorada (Pydantic BaseSettings)

**Archivo**: `backend/config.py` (completamente reescrito)

**Ventajas:**
- ✅ Type-safe settings (Pydantic v2)
- ✅ Carga desde .env automática
- ✅ Fallback a defaults sensatos
- ✅ Singleton pattern (caching)
- ✅ Backward compatible (exports módulo-level)

**Nuevas variables:**
```
ENVIRONMENT = development|production
LOG_LEVEL = DEBUG|INFO|WARNING|ERROR
REDIS_URL = redis://...
REDIS_PASSWORD = ...
CELERY_BROKER_URL = ...
CELERY_RESULT_BACKEND = ...
RATE_LIMIT_REQUESTS_PER_MINUTE = 10
SENTRY_DSN = (opcional)
BACKUP_* = configuración de backups
```

---

### 6. ✅ Middleware Mejorado

**Archivo**: `backend/middleware.py` (completamente reescrito)

**Middlewares:**
1. **RequestIdMiddleware**: Agrega X-Request-ID a cada request (para trazabilidad)
2. **LoggingMiddleware**: Log estructurado de todas las requests (duración, status)
3. **RateLimitMiddleware**: Rate limiting real con Redis (ver sección 2)

**Orden (importante):**
```
RequestId → Logging → RateLimit → CORS
```

---

### 7. ✅ Main.py Actualizado

**Cambios:**
- ✅ Inicialización de logging PRIMERO
- ✅ Inicialización de Celery
- ✅ Middlewares en orden correcto
- ✅ Version bumped a 0.2.0-fase-a

---

### 8. ✅ Requirements.txt Actualizado

**Nuevas dependencias:**
```
redis[hiredis]>=5.0.0          - Client Redis (hiredis = C bindings)
celery[redis]>=5.3.0            - Task queue
pydantic-settings               - Settings management
python-multipart                - Multipart form data
starlette-middleware-logging    - Logging improvements
sentry-sdk[fastapi,sqlalchemy]  - Error tracking (opcional)
python-json-logger              - JSON logging formatter
psycopg2-binary                 - PostgreSQL adapter
alembic                         - Database migrations (Fase B)
```

---

## Tareas Restantes (Fase A)

### 2. 🔄 Rate Limiting (EN PROGRESO)

**Status**: ✅ IMPLEMENTADO en `backend/rate_limiter.py`
**TODO**: Tests, benchmarking, documentación de uso

---

### 3. 🔲 Celery Integration (Parcialmente Completo)

**Status**: 
- ✅ Celery app + Redis broker configurado
- ✅ Tareas básicas creadas (search_lider_async, search_jumbo_async)
- ❌ NO INTEGRADO en search_service.py (Fase B)
- ❌ Beat schedule vacío (agregar luego)

**Siguiente**: Integrar async tasks en search_service → usar `search_lider_async.delay()` en lugar de `search_lider()` sincrónico

---

### 4. 🔲 Parser Versioning + Monitoring

**TODO**: 
- Snapshot de estructura HTML Lider/Jumbo
- Monitor de cambios (comparar snapshoots periódicos)
- Alerta cuando estructura cambie
- Fallback automático a cache stale

**Prioridad**: ALTA (uno de los riesgos críticos)

---

### 5. 🔲 Healthcheck Exhaustivo

**TODO**:
- `/health` endpoint actual: muy básico
- Agregar checks de: Redis, PostgreSQL, scraper connectivity
- Implementar liveness + readiness probes (K8s ready)

**Ejemplo**:
```json
GET /health/live → {status: ok}
GET /health/ready → {status: ok, redis: ok, db: ok, scraper: ok}
```

---

### 6. 🔲 Backup Automático

**TODO**:
- Implementar backup de SQLite (local o S3)
- Scheduler: cron job o Celery beat task
- Configuración: `BACKUP_INTERVAL_HOURS = 24`
- Path: `./data/backups/` o S3

---

### 7. 🔲 Load Testing (k6)

**TODO**:
- Crear k6 script para simular 100 búsquedas/min
- Identificar cuello de botella (CPU, RAM, timeout)
- Documentar resultados

---

### 8. 🔲 Documentación + Guía de Ejecución

**TODO**:
- PHASE_A_SETUP.md (este archivo continuado)
- PHASE_A_DEPLOYMENT.md (deploy a producción)
- PHASE_A_MONITORING.md (cómo monitorear en producción)

---

## Guía de Setup Local (Fase A)

### Opción 1: Docker Compose (RECOMENDADO)

```bash
# 1. Clonar repo (ya tienes)
cd /path/to/proyecto/nuevo-proyecto

# 2. Copiar .env
cp .env.example .env

# 3. Build images
docker-compose build

# 4. Up services
docker-compose up -d

# 5. Ver logs
docker-compose logs -f app

# 6. Test
curl http://localhost:8001/health
curl "http://localhost:8001/search?q=leche&store=lider"

# 7. Detener
docker-compose down
```

### Opción 2: Local Sin Docker (Para Desarrollo)

```bash
# 1. Instalar Redis (manual o WSL)
# En Windows PowerShell: choco install redis-64
# O en WSL: sudo apt-get install redis-server

# 2. Iniciar Redis
redis-server

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Iniciar app FastAPI
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8001

# 5. En otra terminal: Celery worker
celery -A backend.celery_app worker --loglevel=info --concurrency=4

# 6. En otra terminal: Celery beat (opcional)
celery -A backend.celery_app beat --loglevel=info
```

---

## Verificaciones de Funcionalidad

### Rate Limiting
```bash
# Test: hacer múltiples requests
for i in {1..15}; do
  curl http://localhost:8001/search?q=leche
  echo "Request $i"
done

# Esperado en req 11+: HTTP 429 (Too Many Requests)
```

### Logging
```bash
# Ver logs en tiempo real
docker-compose logs -f app

# O en local:
tail -f data/logs/app.log
```

### Celery
```bash
# Ver tasks
docker exec -it radar-celery-worker celery -A backend.celery_app inspect active

# Debug task
curl "http://localhost:8001/debug-task" (endpoint futura)
```

### Redis
```bash
# Conectar a Redis
redis-cli -a redis123

# Ver keys de rate limiting
KEYS rate_limit:*

# Ver cache de búsquedas
KEYS *lider:*
```

---

## Diferencias con Código Original

| Aspecto | Antes | Ahora |
|--------|-------|-------|
| **Rate Limiting** | En memoria (no escalable) | Redis (distribuido) |
| **Logging** | basicConfig simple | Structured JSON + multiple handlers |
| **Config** | Módulo-level variables | Pydantic BaseSettings |
| **Async** | No existe (sync only) | Celery ready (tasks creadas) |
| **Observabilidad** | Nula | Request ID + structured logs + Sentry ready |
| **Infra** | Manual | Docker compose (desarrollo + staging) |
| **Monitoring** | GET /health básico | Ready para Prometheus + health checks mejorados |

---

## Próximas Tareas (Orden de Prioridad)

1. ✅ **Docker + Redis + Config** → DONE
2. ✅ **Rate Limiting Real** → DONE
3. ✅ **Logging Centralizado** → DONE
4. ✅ **Celery Setup** → DONE (tasks creadas, no integradas aún)
5. ⏳ **Parser Versioning** → CRÍTICO (próxima tarea)
6. ⏳ **Healthcheck** → IMPORTANTE
7. ⏳ **Load Testing** → NECESARIO (identificar límites)
8. ⏳ **Backup** → IMPORTANTE (producción)

---

## Línea de Tiempo Estimada

| Tarea | Semana | Status |
|-------|--------|--------|
| Docker + Config | S1 | ✅ COMPLETADO |
| Rate Limiting | S1-S2 | ✅ COMPLETADO |
| Celery Tasks | S1-S2 | ✅ FRAMEWORK (tests pendientes) |
| Parser Monitoring | S2 | ⏳ TODO |
| Healthcheck | S2 | ⏳ TODO |
| Load Testing | S2-S3 | ⏳ TODO |
| Backup | S3 | ⏳ TODO |
| **Total Fase A** | **4-6 semanas** | **~40% completado** |

---

## Riesgos Residuales (Fase A)

🔴 **CRÍTICOS**:
1. Parser de Lider/Jumbo aún sin versioning (1 cambio HTML = cero resultados)
2. Celery tasks no integradas en search_service (aún llamadas sincrónicas)
3. Healthcheck no exhaustivo (no detecta fallos de Redis)

🟠 **IMPORTANTES**:
1. Load testing no realizado (¿cuál es el límite real?)
2. Backup no implementado (si BD se corrompe = pérdida total)
3. Monitoring muy básico (no hay alertas reales)

---

## Referencias

- Docker Compose: https://docs.docker.com/compose/
- Redis: https://redis.io/docs/
- Celery: https://docs.celeryproject.org/
- Pydantic: https://docs.pydantic.dev/
- Sentry: https://sentry.io/
