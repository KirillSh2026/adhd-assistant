# ADHD AI Assistant Instructions

## Commands

- Run the CLI from the repository root because it uses the relative path `data/notes.json`:
  - Add an item: `python app/main.py task "Buy groceries"`
  - Add with auto-detected type: `python app/main.py capture "Buy groceries tomorrow"`
  - Add from dictation (microphone): `python app/main.py dictate`
  - Add from dictation (audio file): `python app/main.py dictate /path/to/audio.wav`
  - Suggest similar/related items (PostgreSQL): `python app/main.py suggest-relations`
  - Show similarity clusters (PostgreSQL): `python app/main.py show-clusters`
  - Link items explicitly (PostgreSQL): `python app/main.py link-items 2 5 depends_on "Finish base work first"`
  - Confirm a suggested relation (PostgreSQL): `python app/main.py confirm-relation 2 5 duplicate_of`
  - Reject a suggested relation (PostgreSQL): `python app/main.py reject-relation 2 5 duplicate_of`
  - Merge duplicate items (PostgreSQL): `python app/main.py merge-items 2 5 --reason "Merging duplicates"`
  - Show merge history (PostgreSQL): `python app/main.py list-merges`
  - Undo last merge (PostgreSQL): `python app/main.py undo-merge`
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

- `app/main.py` is the thin runnable entrypoint: parses sys.argv into structured arguments, loads settings, creates service, and delegates to CLI layer.
- `cli/` package handles all CLI concerns (no direct sys.argv access in command handlers):
  - `cli/parser.py` parses sys.argv into structured CommandArgs with command name and remaining arguments
  - `cli/formatters.py` provides output formatting functions (print_item, print_relation, etc.)
  - `cli/utils.py` provides utilities like parse_int for argument parsing and validation
  - `cli/commands/` subpackage contains command handlers that receive parsed args as parameters:
    - `cli/commands/__init__.py` handles item management (list/clear/add-by-type)
    - `cli/commands/capture_commands.py` handles text capture and audio dictation
    - `cli/commands/relation_commands.py` handles relations and dependency linking
    - `cli/commands/merge_commands.py` handles item merging and merge history
  - `cli/dispatcher.py` routes commands to appropriate handlers with parsed arguments
- `config/settings.py` centralizes environment loading via `pydantic-settings` (single source for `ADHD_STORAGE_BACKEND`, `ADHD_NOTES_PATH`, `DATABASE_URL`, `ADHD_DICTATE_LANGUAGE`).
- `core/exceptions.py` defines domain exception hierarchy for typed error handling.
- `interfaces/storage.py` defines the storage contract; service layer works through this interface and does not branch on JSON/PostgreSQL internals.
- `services/` layer is organized around use cases (not technical concerns):
  - `services/capture_service.py` – Item creation and auto-classification
  - `services/list_service.py` – Item listing and filtering
  - `services/relation_service.py` – Relations, suggestions, and clustering
  - `services/merge_service.py` – Item merging and merge history
  - `services/item_service_registry.py` – Facade combining all specialized services
  - `services/item_service.py` – Legacy wrapper (backwards compatible, now delegates to registry)
  - `services/shared_item_utils.py` – Shared utilities for item operations
  - `services/speech_to_text_service.py` – Speech-to-text for `dictate` command
  - `services/item_type_classifier.py` – Auto-classification into task/note/idea
  - `services/relation_analysis_service.py` – Similarity analysis and clustering
- All services receive `Storage` as constructor parameter (no sys.argv, fully testable).
- `storage/json_storage.py` is the default storage backend using `data/notes.json`.
- `storage/postgres_storage.py` is the PostgreSQL backend (`ADHD_STORAGE_BACKEND=postgres`, `DATABASE_URL` required).
- `migrations/0001_init_postgres.sql` is the canonical PostgreSQL schema; `migrations/0002_drop_schema.sql` is full rollback.
- `scripts/migrate_json_to_postgres.py` performs phased import with source-tagged rollback (no sys.argv).

## Repository Conventions

- Preserve JSON UTF-8 Cyrillic content with `ensure_ascii=False` and two-space indentation.
- Keep backward compatibility with `type`/`text`/optional `datetime` records in both storage backends.
- `list task`, `list note`, and `list idea` filter empty text and keep numbering behavior over the filtered stream.

---

# Инструкции для ADHD AI Assistant

## Команды

- Запускайте CLI из корня репозитория: оно использует относительный путь `data/notes.json`.
  - Добавить элемент: `python app/main.py task "Купить продукты"`
  - Добавить с автоопределением типа: `python app/main.py capture "Купить продукты завтра"`
  - Добавить через диктовку (микрофон): `python app/main.py dictate`
  - Добавить через диктовку (аудиофайл): `python app/main.py dictate /path/to/audio.wav`
  - Предложить похожие/связанные элементы (PostgreSQL): `python app/main.py suggest-relations`
  - Показать кластеры похожих элементов (PostgreSQL): `python app/main.py show-clusters`
  - Явно связать элементы (PostgreSQL): `python app/main.py link-items 2 5 depends_on "Сначала завершить базу"`
  - Подтвердить предложенную связь (PostgreSQL): `python app/main.py confirm-relation 2 5 duplicate_of`
  - Отклонить предложенную связь (PostgreSQL): `python app/main.py reject-relation 2 5 duplicate_of`
  - Объединить дубликаты (PostgreSQL): `python app/main.py merge-items 2 5 --reason "Объединяем дубликаты"`
  - Показать историю merge (PostgreSQL): `python app/main.py list-merges`
  - Откатить последний merge (PostgreSQL): `python app/main.py undo-merge`
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
- `config/settings.py` — централизованная загрузка окружения через `pydantic-settings` (`ADHD_STORAGE_BACKEND`, `ADHD_NOTES_PATH`, `DATABASE_URL`, `ADHD_DICTATE_LANGUAGE`).
- `services/item_service.py` — слой бизнес-логики CLI (add/list/clear/capture), сохраняющий совместимость вывода.
- `services/speech_to_text_service.py` — распознавание речи в текст для команды `dictate`.
- `services/item_type_classifier.py` — автоопределение типа `task`, `note`, `idea` по тексту.
- `services/relation_analysis_service.py` — поиск похожих/связанных элементов и построение кластеров.
- `interfaces/storage.py` — контракт storage-слоя; `ItemService` не знает о деталях JSON/PostgreSQL backend.
- `storage/json_storage.py` — backend по умолчанию (`data/notes.json`).
- `storage/postgres_storage.py` — PostgreSQL backend (`ADHD_STORAGE_BACKEND=postgres`, нужен `DATABASE_URL`).
- `migrations/0001_init_postgres.sql` — каноничная PostgreSQL-схема; `migrations/0002_drop_schema.sql` — полный rollback.
- `scripts/migrate_json_to_postgres.py` — поэтапный импорт JSON с rollback по run-id.

## Соглашения репозитория

- Сохраняйте UTF-8 и кириллицу в JSON (`ensure_ascii=False`, отступ 2 пробела).
- Поддерживайте обратную совместимость с текущими полями `type`/`text`/опциональный `datetime` в обоих backend.
- Команды `list task`, `list note`, `list idea` фильтруют пустые тексты и сохраняют текущую логику нумерации в CLI.
