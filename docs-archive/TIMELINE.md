# Timeline

## Abril 2026

Se audito el proyecto y se corrigio la declaracion de estado: el codigo corresponde a un prototipo avanzado, no a un producto terminado.

## Fase 1: Estabilizacion

Objetivo:

- Dejar el proyecto instalable y ejecutable.
- Alinear backend, frontend, tests y documentacion.
- Mantener Lider como flujo principal.
- Mantener Jumbo como experimental.
- Evitar nuevas features hasta cerrar estabilidad.

Estado:

- Completada como primera pasada de estabilizacion.

## Fase 2: Arquitectura y persistencia

Objetivo:

- Agregar SQLAlchemy.
- Crear DB local por defecto.
- Persistir usuarios, canastas, items e historial de precios.
- Mantener `DATABASE_URL` para evolucionar a PostgreSQL.
- Agregar tests de persistencia.

Estado:

- Completada como base de arquitectura y persistencia.
- Se agrego migracion inicial de Alembic.
- Se separo la capa de datos en repositorios.
- Se formalizaron adaptadores por tienda.

## Fase 3: Producto usable

Objetivo:

- Agregar registro, login y logout en frontend.
- Usar `Authorization: Bearer` para usuario actual.
- Crear canastas por usuario autenticado.
- Agregar productos a canastas desde resultados sin copiar IDs.
- Editar cantidades y ver totales de canasta.
- Ver historial de precios desde las tarjetas de producto.

Estado:

- Completada como primera version usable.

## Fases pendientes

- Fase 4: produccion y operacion.
- Fase 5: producto final profesional.
