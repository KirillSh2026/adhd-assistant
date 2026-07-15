-- JSON -> PostgreSQL phased migration plan with rollback
-- Runtime migration script: scripts/migrate_json_to_postgres.py

-- Phase 0: Preconditions
-- 1) DATABASE_URL is set
-- 2) PostgreSQL schema is applied
--      psql "$DATABASE_URL" -f migrations/0001_init_postgres.sql
-- 3) Legacy JSON still remains source of truth until phase 4 cutover

-- Phase 1: Dry-run import (no writes)
--      python scripts/migrate_json_to_postgres.py --dsn "$DATABASE_URL" --dry-run

-- Phase 2: Initial import
--      python scripts/migrate_json_to_postgres.py --dsn "$DATABASE_URL" --json-path data/notes.json

-- Phase 3: Verification
-- A. Imported row counts
SELECT COUNT(*) AS postgres_items FROM item;

-- B. Distribution by item type
SELECT type, COUNT(*) AS items_per_type
FROM item
GROUP BY type
ORDER BY type;

-- C. Imported rows from latest run
SELECT source, COUNT(*) AS imported_rows
FROM item
WHERE source LIKE 'cli_migration:%'
GROUP BY source
ORDER BY source DESC;

-- D. Legacy consistency quick-check (manual)
-- Compare this count with len(data/notes.json)
SELECT COUNT(*) AS imported_rows_total
FROM item
WHERE source LIKE 'cli_migration:%';

-- Phase 4: Cutover
-- Switch CLI backend:
--      export ADHD_STORAGE_BACKEND=postgres
--      export DATABASE_URL=postgresql://...
-- Keep data/notes.json untouched for rollback window.

-- Rollback (to JSON mode)
-- 1) Rollback the latest import batch (source-tag based):
--      python scripts/migrate_json_to_postgres.py --dsn "$DATABASE_URL" --rollback-last
-- 2) Switch backend back to JSON:
--      export ADHD_STORAGE_BACKEND=json
-- 3) (optional) remove schema:
--      psql "$DATABASE_URL" -f migrations/0002_drop_schema.sql
