-- PostgreSQL-only target schema for ADHD AI Assistant.
-- Canonical migration file: migrations/0001_init_postgres.sql
-- Rollback file: migrations/0002_drop_schema.sql

-- This file intentionally mirrors the migration entrypoint so every agent
-- uses a single SQL dialect and a single source of truth.

\echo 'Apply with: psql "$DATABASE_URL" -f migrations/0001_init_postgres.sql'
\echo 'Rollback with: psql "$DATABASE_URL" -f migrations/0002_drop_schema.sql'

\ir ../migrations/0001_init_postgres.sql
