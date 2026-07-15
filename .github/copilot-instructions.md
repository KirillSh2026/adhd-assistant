# ADHD AI Assistant Instructions

## Commands

- Run the CLI from the repository root because it uses the relative path `data/notes.json`:
  - Add an item: `python app/main.py task "Buy groceries"`
  - List all items: `python app/main.py list all`
  - List one type: `python app/main.py list task` (also `note` or `idea`)
  - Clear all items: `python app/main.py clear`
- Install dependencies: `pip install -r requirements.txt`
- Validate Python modules: `make check`
- Run tests: `make test`
- Run one test: `make test-one TEST=tests/test_item_service.py::test_add_and_list_with_legacy_format`
- PostgreSQL schema migration: `make migrate-up`
- JSON -> PostgreSQL import: `make migrate-import-json`
- Rollback latest JSON import: `make migrate-rollback`

## Architecture

- `app/main.py` is the runnable entrypoint and routes all CLI actions through `ItemService`.
- `services/item_service.py` contains the CLI-facing behavior (add/list/clear) and keeps backward-compatible list formatting semantics.
- `storage/json_storage.py` is the default storage backend using `data/notes.json`.
- `storage/postgres_storage.py` is the PostgreSQL backend (`ADHD_STORAGE_BACKEND=postgres`, `DATABASE_URL` required).
- `migrations/0001_init_postgres.sql` is the canonical PostgreSQL schema; `migrations/0002_drop_schema.sql` is full rollback.
- `scripts/migrate_json_to_postgres.py` performs phased import with source-tagged rollback.

## Repository Conventions

- Preserve JSON UTF-8 Cyrillic content with `ensure_ascii=False` and two-space indentation.
- Keep backward compatibility with `type`/`text`/optional `datetime` records in both storage backends.
- `list task`, `list note`, and `list idea` filter empty text and keep numbering behavior over the filtered stream.

---

# Инструкции для ADHD AI Assistant

## Команды

- Запускайте CLI из корня репозитория: оно использует относительный путь `data/notes.json`.
  - Добавить элемент: `python app/main.py task "Купить продукты"`
  - Вывести все элементы: `python app/main.py list all`
  - Вывести элементы одного типа: `python app/main.py list task` (также `note` или `idea`)
  - Очистить все элементы: `python app/main.py clear`
- Установить зависимости: `pip install -r requirements.txt`
- Проверить Python-модули: `make check`
- Запустить все тесты: `make test`
- Запустить один тест: `make test-one TEST=tests/test_item_service.py::test_add_and_list_with_legacy_format`
- Применить PostgreSQL-схему: `make migrate-up`
- Импортировать JSON в PostgreSQL: `make migrate-import-json`
- Откатить последний импорт JSON: `make migrate-rollback`

## Архитектура

- `app/main.py` — исполняемая точка входа CLI; все команды проходят через `ItemService`.
- `services/item_service.py` — слой бизнес-логики CLI (add/list/clear), сохраняющий совместимость вывода.
- `storage/json_storage.py` — backend по умолчанию (`data/notes.json`).
- `storage/postgres_storage.py` — PostgreSQL backend (`ADHD_STORAGE_BACKEND=postgres`, нужен `DATABASE_URL`).
- `migrations/0001_init_postgres.sql` — каноничная PostgreSQL-схема; `migrations/0002_drop_schema.sql` — полный rollback.
- `scripts/migrate_json_to_postgres.py` — поэтапный импорт JSON с rollback по run-id.

## Соглашения репозитория

- Сохраняйте UTF-8 и кириллицу в JSON (`ensure_ascii=False`, отступ 2 пробела).
- Поддерживайте обратную совместимость с текущими полями `type`/`text`/опциональный `datetime` в обоих backend.
- Команды `list task`, `list note`, `list idea` фильтруют пустые тексты и сохраняют текущую логику нумерации в CLI.
