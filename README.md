# ADHD AI Assistant

CLI-прототип личного помощника для пользователя с СДВГ.

## Быстрый старт

```bash
python app/main.py task "Купить продукты"
python app/main.py list all
python app/main.py list task
python app/main.py clear
```

По умолчанию CLI использует JSON-хранилище: `data/notes.json`.

## Backend-хранилища

### 1. JSON (по умолчанию)

```bash
export ADHD_STORAGE_BACKEND=json
export ADHD_NOTES_PATH=data/notes.json
python app/main.py list all
```

### 2. PostgreSQL

```bash
export ADHD_STORAGE_BACKEND=postgres
export DATABASE_URL=postgresql://user:pass@localhost:5432/adhd_assistant
python app/main.py list all
```

## Зависимости

```bash
pip install -r requirements.txt
```

## Команды разработки

### Проверка модулей

```bash
make check
```

### Тесты

```bash
make test
```

### Один тест

```bash
make test-one TEST=tests/test_item_service.py::test_add_and_list_with_legacy_format
```

### Миграции PostgreSQL

```bash
# Создать схему
make migrate-up

# Импортировать data/notes.json
make migrate-import-json

# Откатить последний импорт
make migrate-rollback

# Полностью удалить схему
make migrate-down
```

## Миграция JSON -> PostgreSQL

Пошаговый план и SQL-проверки:

- `AI/03_migration.sql`
- `scripts/migrate_json_to_postgres.py`

## Архитектурные документы

- `.github/copilot-instructions.md` — рабочие инструкции для AI-сессий
- `AI/00_constitution.md` — принципы проекта
- `AI/01_architecture.md` — архитектурные решения по БД
- `AI/02_database_schema.sql` — зафиксированный PostgreSQL-диалект
- `docs/database_schema.md` — визуальная ER-диаграмма
