# Fases 2, 3 y 4

Este documento mantiene el roadmap real del producto. Las fases 2 y 3 quedan cerradas; la Fase 4 sigue pendiente.

## Fase 2: Arquitectura profesional

Estado: completada.

- SQLAlchemy configurado.
- SQLite local por defecto.
- `DATABASE_URL` configurable para PostgreSQL.
- Persistencia de usuarios, canastas, items e historial de precios.
- Migracion inicial con Alembic.
- Repositorios explicitos para usuarios, canastas e historial de precios.
- Adaptadores formales por tienda para Lider y Jumbo experimental.
- Datos de negocio principales fuera de memoria; solo queda cache temporal de busqueda.
- Tests de API, parser, scraper, busqueda, seguridad y persistencia pasando.

## Fase 3: Producto usable

Estado: completada.

- Registro, login y logout en frontend.
- Uso de `Authorization: Bearer`.
- Canastas reales por usuario autenticado.
- Flujo de agregar producto a canasta sin copiar IDs.
- Vista de canasta con cantidades, totales y edicion.
- Historial de precios visible desde las tarjetas de producto.
- UX para estados de carga, error y vacios en busqueda y canastas.

## Fase 4: Produccion y operacion

- Docker.
- CI/CD.
- Configuracion por ambiente.
- Secretos fuera del codigo.
- CORS seguro.
- Redis para cache y rate limiting.
- Workers asincronos para scraping.
- Logging estructurado.
- Metricas, monitoreo y alertas.
- Backups.

Cada fase debe cerrar con auditoria tecnica, funcional, seguridad, UX, testing y documentacion.
