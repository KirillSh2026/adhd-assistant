.PHONY: check test test-one migrate-up migrate-down migrate-import-json migrate-rollback

check:
	python -m py_compile app/main.py models/item.py services/item_service.py storage/json_storage.py storage/postgres_storage.py

test:
	pytest -q

test-one:
	pytest -q $(TEST)

migrate-up:
	psql "$$DATABASE_URL" -f migrations/0001_init_postgres.sql

migrate-down:
	psql "$$DATABASE_URL" -f migrations/0002_drop_schema.sql

migrate-import-json:
	python scripts/migrate_json_to_postgres.py --dsn "$$DATABASE_URL" --json-path data/notes.json

migrate-rollback:
	python scripts/migrate_json_to_postgres.py --dsn "$$DATABASE_URL" --rollback-last
