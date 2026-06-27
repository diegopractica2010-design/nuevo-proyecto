# Estado del proyecto — Radar de Precios (actualizado 2026-06-02, noche)

## 🎯 Resumen rápido
App de comparación de precios. 3 tiendas funcionan rápido y confiable
(Lider, Jumbo, Santa Isabel). Hoy se depuró todo el sistema y se arreglaron
varios bugs críticos. Quedan mejoras acordadas por implementar (ver abajo).

## ✅ HECHO HOY (commits version 19 y version 20)

**Bugs críticos arreglados:**
1. **rate_limiter** colgaba 4s cada request (Redis caído) → 0.013s.
2. **cache.py** circuit breaker Redis (causa raíz lentitud, compare 34s→3s).
3. **Esquema DB** desactualizado rompía auth con 500: añadidas columnas
   `users.is_verified`, `users.role`, `products.product_url`, `products.image_url`.
4. **CSP/API base** (¡grande!): el frontend llamaba a `localhost:8001` y el CSP
   lo bloqueaba al abrir en `127.0.0.1` → la app no cargaba datos. Ahora usa
   URLs relativas (`frontend/.env.local` vacío). Funciona en ambos hosts.
5. **Mensajes de error** del api-client: ahora legibles (422 de validación).
6. **Santa Isabel** recuperada vía API BFF (`bff.santaisabel.cl/catalog/plp`).
7. **Stopwords**: "fideo/fideos" ya no se descartan.
8. **Logo "Radar"**: ahora navega a inicio limpio (anchor real).
9. **Lista de compras por defecto**: queries cortas (arroz, leche, aceite,
   detergente, confort). Las multi-palabra bloqueaban Lider.
10. **launcher.py**: el exe ahora carga el `.env` bundleado (JUMBO_API_KEY).

**Verificación:** 19/19 endpoints OK, 13/13 checks de navegador, página admin OK.

## ⚠️ POR QUÉ "no había precios en Lider/Jumbo" (diagnóstico)
- **Lider**: su anti-bot (Datadome) BLOQUEA queries multi-palabra como
  "arroz 1 kilo" (redirige a /blocked). Con queries cortas ("arroz") funciona.
- **Jumbo en el EXE**: el exe no cargaba el `.env` → JUMBO_API_KEY vacía →
  Jumbo desactivado. Arreglado en launcher.py (falta rebuild del exe).
- En el **servidor de desarrollo (fuente)** Jumbo siempre funcionó.

## 🟡 ESTADO DE EJECUCIÓN ACTUAL
- **Servidor dev corriendo en http://localhost:8001** con TODOS los fixes
  (uvicorn desde fuente, carga .env, Jumbo funciona). Tarea bg: `byfginqvo`.
- **El .exe en `dist/` está DESACTUALIZADO** (no tiene los cambios de version 20:
  logo, lista corta, launcher .env). PENDIENTE: rebuild del exe.
- Cómo correr dev: `python -m uvicorn backend.main:app --host 0.0.0.0 --port 8001`
  (con PYTHONPATH=raíz y NODE_TLS_REJECT_UNAUTHORIZED=0). Frontend: `cd frontend && npm run build`.

## 🚀 MEJORAS ACORDADAS — IMPLEMENTAR MAÑANA
El usuario eligió estas 4 + rediseño visual. Los datos ya existen en el backend
(verificado: `unit_price` "$6.125/kg", `is_offer`, `facets.brands`, `stats`).

1. **Ordenar buscador por precio POR UNIDAD ($/kg, $/L)** — parsear `unit_price`
   (string "$6.125/kg") a número y agregar opción de orden. (Frontend)
2. **"Mejor tienda para toda la canasta"** en el Comparar — calcular total por
   tienda de la lista completa + recomendar dónde comprar todo más barato vs
   óptimo mezclado. (Backend: agregar `store_totals` a /shopping-list/compare;
   Frontend: card resumen)
3. **Filtros en buscador** — solo ofertas / en stock / por marca. Las `facets`
   (marcas) e `is_offer` ya se calculan en el backend; falta exponerlas en UI.
4. **Recuperar Lider (normalizar query)** — auto-simplificar queries
   multi-palabra (quitar números + UNIT_WORDS) antes de pegarle a Lider, para
   que su anti-bot no bloquee. Ver `_query_tokens`/UNIT_WORDS en
   shopping_list_service.py y `normalize_query`/`fallback_query_variants` en scraper.py.
5. **Rediseño visual (NUEVO pedido)**: frontend más moderno y bonito, y
   **dejar espacio en los bordes (sidebars izq/der) para publicidad**. Hoy el
   layout es `max-w-7xl` centrado en `app-shell.tsx` (main) y `app-layout`.
   Idea: columnas laterales reservadas para ads en pantallas anchas (xl+),
   contenido centrado, cards más limpias.

Plan/todos ya creados para estas tareas (no implementadas aún).

## 📋 Tiendas no recuperadas (anti-bot, marcadas "pronto")
- Acuenta (Instaleap GraphQL), Unimarc (Cloudflare 403), Tottus (Falabella 404).
  Detalle técnico para recuperarlas en commits/historial. Excluidas del compare.

## ⚙️ Notas
- Sin Redis todo funciona (circuit breakers). Para cache real: Redis :6379.
- Playwright instalado pero PLAYWRIGHT_ENABLED=false (no da resultados usables
  para las 3 caídas). Descarga de Chromium requirió NODE_TLS_REJECT_UNAUTHORIZED=0.
- `.env` y `.env.local` NO están en git (protegidos). build/dist ignorados.
- Último commit: `version 20` + limpieza de _diag.py. Working tree limpio.
