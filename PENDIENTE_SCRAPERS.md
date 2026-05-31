# Estado del scraping — continuar aquí

## Qué funciona hoy (confirmado)
- **Lider**: funciona vía HTML parsing (NO vía GraphQL — schema cambió)
- **Jumbo**: funciona con JUMBO_API_KEY del .env

## Lider GraphQL — schema nuevo (INCOMPLETO, investigación en curso)

El endpoint `https://super.lider.cl/orchestra/graphql` cambió su schema.

Lo confirmado hasta ahora:
- `prg: "desktop"` es argumento REQUERIDO (tipo `Prg!`)  
- La estructura es: `search(query, page, prg) → searchResult { itemStacks { items { ... } } }`
- `image` ya no existe en `Product` (sugiere `badge`, `cake`, o `name`)
- Todos los campos de precio son objetos anidados, NO escalares:
  - `wasPrice { ??? }`, `basePrice { ??? }`, `linePrice { ??? }`, `currentPrice { ??? }`
  - Ninguno de estos sub-campos ha sido encontrado aún: `value`, `price`, `amount` → todos 400

### Próximo paso para Lider GraphQL:
Encontrar los sub-campos válidos de `ProductPrice`. Intentar:
- `wasPrice { formattedValue }` 
- `wasPrice { centAmount }`
- `wasPrice { displayPrice }`
- `wasPrice { __typename }` para ver qué tipo es primero

Alternativamente, usar el query `search(...) { searchResult { itemStacks { items { name brand canonicalUrl availabilityStatusV2 { value } badges { text } } } } }` sin precio, y obtener precio de una segunda query.

## Santa Isabel — SIN API accesible
- HTML: cliente-side rendering (sin SSR, sin __NEXT_DATA__ con productos)
- Cencosud API: 401 Unauthorized
- VTEX API: 404 (ruta incorrecta)
- **Única solución**: Playwright (PLAYWRIGHT_ENABLED=true)

## Tottus — Cloudflare bloqueado
- API legacy ATG: falla
- VTEX API: 403 Cloudflare
- **Única solución**: Playwright (PLAYWRIGHT_ENABLED=true)

## Unimarc — Cloudflare bloqueado  
- API: bloqueada por Cloudflare
- **Única solución**: Playwright (PLAYWRIGHT_ENABLED=true)

## Acuenta
- Misma plataforma que Lider → se arreglará automáticamente cuando se arregle Lider GraphQL
- El código usa el mismo endpoint con `Origin: super.lider.cl` (correcto)

## Para continuar
1. Resolver sub-campos de `ProductPrice` en el GraphQL de Lider
2. Actualizar `backend/infrastructure/scrapers/lider.py` → `_graphql_payloads()` con el nuevo schema
3. Reconstruir el exe: `pyinstaller radar_precios.spec --clean -y`

## Archivos de test (eliminar después)
- test_scrapers.py
- test_apis.py  
- test_graphql_schema.py
- test_graphql2.py
- test_graphql3.py
- test_graphql4.py
- test_graphql5.py
- test_graphql6.py
