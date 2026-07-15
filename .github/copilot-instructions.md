# ADHD AI Assistant Instructions

## Commands

- Run the CLI from the repository root because it uses the relative path `data/notes.json`:
  - Add an item: `python app/main.py task "Buy groceries"`
  - List all items: `python app/main.py list all`
  - List one type: `python app/main.py list task` (also `note` or `idea`)
  - Clear all items: `python app/main.py clear`
- Validate the current Python modules: `python -m py_compile app/main.py models/item.py services/item_service.py storage/json_storage.py`
- No dependency, build, lint, or automated test command is configured. Consequently, there is no single-test command; use the relevant CLI command as the current focused behavior check.

## Architecture

- `app/main.py` is the current runnable application and owns the CLI flow. It directly loads, filters, appends, and rewrites `data/notes.json`.
- `data/notes.json` is a JSON array of captured items. Current entries use `type`, `text`, and an optional `datetime` timestamp.
- `models/item.py`, `services/item_service.py`, and `storage/json_storage.py` define the intended layered direction: `Item` is the domain object, `ItemService` should coordinate operations, and `JsonStorage` should persist them. The service and storage methods are currently stubs, so do not treat these layers as wired into the CLI yet.
- `note.md` describes the planned richer item schema for the AI assistant, including priority, energy, scheduling, and status fields. It is a target model rather than the schema currently written by the CLI.

## Repository Conventions

- Preserve the JSON file's UTF-8 Cyrillic content: when serializing JSON, use `ensure_ascii=False` and the existing two-space indentation.
- Keep backwards compatibility with the current `type`/`text`/optional `datetime` records when introducing the richer schema from `note.md`; make schema migration explicit instead of silently replacing existing fields.
- The `list task`, `list note`, and `list idea` branches filter empty `text` values, but retain each item’s original list position when printing. Preserve this numbering behavior unless intentionally changing the CLI contract.

---

# Инструкции для ADHD AI Assistant

## Команды

- Запускайте CLI из корня репозитория: оно использует относительный путь `data/notes.json`.
  - Добавить элемент: `python app/main.py task "Купить продукты"`
  - Вывести все элементы: `python app/main.py list all`
  - Вывести элементы одного типа: `python app/main.py list task` (также `note` или `idea`)
  - Очистить все элементы: `python app/main.py clear`
- Проверить текущие Python-модули: `python -m py_compile app/main.py models/item.py services/item_service.py storage/json_storage.py`
- В репозитории не настроены зависимости, сборка, линтер или автоматические тесты. Поэтому команды запуска отдельного теста нет; для точечной проверки текущего поведения используйте подходящую команду CLI.

## Архитектура

- `app/main.py` — текущее запускаемое приложение, управляющее работой CLI. Оно напрямую загружает, фильтрует, дополняет и перезаписывает `data/notes.json`.
- `data/notes.json` — JSON-массив сохраненных элементов. Текущие записи содержат `type`, `text` и необязательную временную метку `datetime`.
- `models/item.py`, `services/item_service.py` и `storage/json_storage.py` задают целевое разделение на слои: `Item` — доменный объект, `ItemService` должен координировать операции, а `JsonStorage` — сохранять их. Методы сервиса и хранилища пока являются заглушками, поэтому эти слои еще не подключены к CLI.
- `note.md` описывает планируемую расширенную схему элемента для AI-помощника, включая поля приоритета, энергии, планирования и статуса. Это целевая модель, а не схема, которую сейчас записывает CLI.

## Соглашения репозитория

- Сохраняйте UTF-8-содержимое JSON на кириллице: при сериализации используйте `ensure_ascii=False` и существующие отступы в два пробела.
- При введении расширенной схемы из `note.md` сохраняйте обратную совместимость с текущими записями `type`/`text`/необязательное `datetime`; выполняйте миграцию схемы явно, а не заменяйте существующие поля незаметно.
- Ветви `list task`, `list note` и `list idea` отфильтровывают записи с пустым `text`, но при выводе сохраняют исходную позицию каждого элемента в списке. Сохраняйте это поведение нумерации, если только намеренно не меняете контракт CLI.
