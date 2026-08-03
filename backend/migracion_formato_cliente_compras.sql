-- Migración manual — Módulo Compras: soporte de formato Excel del cliente
-- (COMPRAS_ECO_NEOAGROX_2026.xlsx)
--
-- El proyecto usa Base.metadata.create_all() (sin Alembic), que solo crea
-- tablas NUEVAS y no altera tablas ya existentes. Como se agregaron columnas
-- nuevas a "ordenes_compra" y "ordenes_compra_items", hay que correr este
-- script UNA VEZ contra la base de datos ya desplegada (dev/staging/prod)
-- para que las columnas existan antes de levantar el backend actualizado.
--
-- Si la base es nueva (se crea desde cero con create_all), este script NO
-- es necesario: las tablas ya se crean con las columnas nuevas incluidas.
--
-- Todas las columnas son NULLABLE: no se pierde ni se corrompe ningún dato
-- existente, y las órdenes ya creadas simplemente quedan con estos campos
-- en NULL.

-- ==== PostgreSQL ====================================================
ALTER TABLE ordenes_compra ADD COLUMN IF NOT EXISTS dias_credito INTEGER;
ALTER TABLE ordenes_compra ADD COLUMN IF NOT EXISTS fecha_vencimiento_factura TIMESTAMPTZ;

ALTER TABLE ordenes_compra_items ADD COLUMN IF NOT EXISTS presentacion VARCHAR(50);
ALTER TABLE ordenes_compra_items ADD COLUMN IF NOT EXISTS unidad_medida VARCHAR(30);
ALTER TABLE ordenes_compra_items ADD COLUMN IF NOT EXISTS cantidad_por_unidad NUMERIC(14, 3);
ALTER TABLE ordenes_compra_items ADD COLUMN IF NOT EXISTS concepto VARCHAR(200);

-- ==== SQLite (uso local / desarrollo) ===============================
-- SQLite no soporta "IF NOT EXISTS" en ADD COLUMN ni TIMESTAMPTZ: correr
-- cada línea suelta y, si alguna columna ya existe, ignorar el error
-- "duplicate column name" de esa línea puntual.
--
-- ALTER TABLE ordenes_compra ADD COLUMN dias_credito INTEGER;
-- ALTER TABLE ordenes_compra ADD COLUMN fecha_vencimiento_factura DATETIME;
--
-- ALTER TABLE ordenes_compra_items ADD COLUMN presentacion VARCHAR(50);
-- ALTER TABLE ordenes_compra_items ADD COLUMN unidad_medida VARCHAR(30);
-- ALTER TABLE ordenes_compra_items ADD COLUMN cantidad_por_unidad NUMERIC(14, 3);
-- ALTER TABLE ordenes_compra_items ADD COLUMN concepto VARCHAR(200);
