# Estado del proyecto — Radar de Precios (actualizado 2026-06-02)

## 🎯 Resumen

Se arregló el problema de "no escrapea" + lentitud. **Causa raíz: Redis caído**
bloqueaba el event loop. Tras el fix, 3 tiendas funcionan rápido y confiable.

## ✅ FUNCIONANDO (verificado end-to-end)

| Tienda | Velocidad | Cómo |
|--------|-----------|------|
| **Lider** | ~4s | HTML fallback (super.lider.cl) |
| **Jumbo** | ~1s | API Cencosud VTEX (`JUMBO_API_KEY`) |
| **Santa Isabel** | ~0.5s | API BFF `bff.santaisabel.cl/catalog/plp` (recuperada) |

- **Comparar lista**: 5/5 productos en ~3-5s con las 3 tiendas. Santa Isabel
  frecuentemente tiene el precio más bajo.
- **Buscador**: 12 resultados, ordenados del más barato al más caro + botón toggle.

## ❌ NO DISPONIBLES (muros anti-bot reales)

| Tienda | Problema |
|--------|----------|
| **Acuenta** | Plataforma Instaleap (GraphQL `SUPER_BODEGA`/store 580). La operación de búsqueda no se captura limpiamente; el HTML es client-rendered |
| **Unimarc** | Cloudflare bloquea httpx (403) Y el navegador headless (selectores no cargan). BFF en `bff-unimarc-web.unimarc.cl` |
| **Tottus** | API Falabella redirige a 404; Playwright devuelve 1 producto con precio corrupto |

→ Marcadas `requires_playwright=True` + `experimental=True`. En la UI salen con
etiqueta **"pronto"** y atenuadas. Excluidas del comparador (que solo usa las rápidas).
`PLAYWRIGHT_ENABLED=false` (el navegador no entrega resultados usables y añade 15s).

## 🔧 Cambios de esta sesión (sin commit)

**Backend:**
- `infrastructure/cache/cache.py` — **circuit breaker Redis** (causa raíz; 34s→3s)
- `rate_limiter.py` — **mismo bug Redis**: con Redis caído, cada request se colgaba
  ~4s (cliente no se ponía en None tras fallar + timeout 5s + retry). Fix: timeouts
  a 1s, `retry_on_timeout=False`, `redis_client=None` al fallar. **Toda request HTTP
  pasó de 4s→0.013s** (ej: búsqueda Santa Isabel 6.6s→0.6s)
- `domain/constants.py` — quitados "fideo"/"fideos" de stopwords (bug de matching)
- `store_adapters.py` — `requires_playwright`, `comparable_stores()`, SI/Jumbo no-experimental
- `shopping_list_service.py` — usa `comparable_stores()`, timeout 10s, limit 10
- `config.py` — `SANTA_ISABEL_API_KEY` / `_BFF_URL` / `_STORE`
- `infrastructure/scrapers/santa_isabel.py` — `_try_bff_api` (estrategia principal)
- `main.py` — `/stores` expone `available`

**Frontend (recompilado):**
- `search-dashboard.tsx` — orden por precio + toggle, menos resultados, textos
- `api-client.ts` — límite 12
- `app-shell.tsx` — etiqueta "pronto" en tiendas no disponibles
- `types/api.ts` — campo `available`
- `shopping-list-workbench.tsx` — precios por tienda + manejo de errores

**Infra:** Playwright 1.60.0 + Chromium instalados (descarga con
`NODE_TLS_REJECT_UNAUTHORIZED=0`), pero `PLAYWRIGHT_ENABLED=false`.

## 📋 Si se quieren recuperar las 3 tiendas (trabajo futuro)
- **Acuenta**: capturar la operación GraphQL `SearchProducts` de Instaleap
  (variables clientId=`SUPER_BODEGA`, storeReference=`580`) e integrar como httpx,
  igual que se hizo con Santa Isabel.
- **Unimarc**: requiere bypass de Cloudflare — `curl_cffi` (TLS fingerprinting) o
  Playwright con stealth. Su BFF (`bff-unimarc-web.unimarc.cl/bff-api/`) da JSON limpio
  una vez pasado Cloudflare.
- **Tottus**: arreglar el parsing de precio en `_scrape_html_playwright` (concatena
  varios precios) y encontrar el endpoint de listado real de Falabella.

## ⚙️ Cómo correr
- Backend puerto **8001**: sirve también el frontend de `frontend/out/`.
- Frontend: tras editar, `cd frontend && npm run build` + recargar navegador (F5).
- URL: http://127.0.0.1:8001
- Sin Redis todo funciona (circuit breaker). Para cache real: Redis en localhost:6379.
- Cambios sin commit (ver `git status`).
