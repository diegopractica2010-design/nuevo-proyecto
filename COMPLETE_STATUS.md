# Estado Completo Real

## Estado actual

**Fase 3 completada: producto usable.**

El proyecto no esta terminado y no esta listo para produccion. Ya existe una base arquitectonica honesta y una experiencia usable con usuarios, Bearer token y canastas por usuario.

## Implementado ahora

- Backend FastAPI.
- Frontend estatico servido por FastAPI.
- Busqueda con Lider como tienda principal.
- Jumbo corregido a nivel de contrato interno, pero se mantiene como experimental.
- Cache en memoria para busquedas.
- SQLAlchemy con SQLite local por defecto.
- `DATABASE_URL` configurable para evolucionar a PostgreSQL.
- Alembic con migracion inicial.
- Repositorios para separar servicios de SQLAlchemy directo.
- Adaptadores formales para Lider y Jumbo experimental.
- Canastas persistentes.
- Historial de precios persistente.
- Auth JWT experimental con usuarios persistentes.
- Login, registro y logout desde frontend.
- Canastas asociadas al usuario autenticado.
- Flujo de agregar productos a canastas sin copiar IDs.
- Edicion de cantidades en canasta.
- Historial de precios visible en tarjetas de producto.
- Tests iniciales para API, parser, scraper y servicio de busqueda.

## Pendiente para producto final

- PostgreSQL como motor productivo.
- Migraciones futuras para cambios de esquema posteriores a la migracion inicial.
- Repositorios/capa de datos mas explicita.
- Endurecimiento de auth para produccion.
- Normalizacion de productos entre tiendas.
- Workers asincronos para scraping.
- Redis real para cache/rate limiting.
- CI/CD.
- Docker y deploy reproducible.
- Logging estructurado y monitoreo.
- UX completa de login, canastas y comparacion.
- Revision legal/operativa del scraping.

## Criterio de cierre de Fase 2

- Usuarios persistidos en DB: cumplido.
- Canastas e items persistidos en DB: cumplido.
- Historial de precios persistido en DB: cumplido.
- Configuracion por `DATABASE_URL`: cumplido.
- Migracion inicial con Alembic: cumplido.
- Repositorios/capa de datos explicita: cumplido.
- Adaptadores formales por tienda: cumplido.
- Tests de persistencia pasan: cumplido.
- Documentacion describe el estado real: cumplido.
- No quedan datos de negocio principales en memoria, excepto cache de busquedas: cumplido.

## Criterio de cierre de Fase 3

- Login, registro y logout en frontend: cumplido.
- Uso de `Authorization: Bearer`: cumplido.
- Canastas por usuario autenticado: cumplido.
- Agregar productos sin copiar IDs: cumplido.
- Edicion de cantidades y totales: cumplido.
- Historial de precios visible: cumplido.
- Tests de API y persistencia pasan: cumplido.

## Nota

Este archivo reemplaza el estado anterior de "todas las fases completadas". Las fases 4 y 5 siguen pendientes.
