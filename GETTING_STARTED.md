# ADHD AI Assistant v1.0 — Инструкция использования

## 🚀 Быстрый старт (JSON-только)

### 1. Установка

```bash
git clone https://github.com/KirillSh2026/adhd-assistant.git
cd adhd-assistant
pip install -r requirements.txt
```

### 2. Запуск CLI

```bash
# Добавить задачу
python app/main.py task "Купить продукты"

# Добавить заметку
python app/main.py note "Идея для проекта"

# Добавить идею
python app/main.py idea "Начать медитировать"

# Автоопределение типа по тексту
python app/main.py capture "Купить продукты"

# Диктовка с микрофона
python app/main.py dictate

# Диктовка из аудиофайла
python app/main.py dictate /path/to/note.wav

# Поиск похожих записей и предложение связей (PostgreSQL)
python app/main.py suggest-relations

# Показать кластеры похожих записей (PostgreSQL)
python app/main.py show-clusters

# Показать сохраненные связи (PostgreSQL)
python app/main.py list-relations

# Вывести все элементы
python app/main.py list all

# Вывести только задачи
python app/main.py list task

# Вывести только заметки
python app/main.py list note

# Вывести только идеи
python app/main.py list idea

# Очистить все элементы
python app/main.py clear
```

### 3. Данные по умолчанию

По умолчанию CLI использует JSON-хранилище:
- **Файл**: `data/notes.json`
- **Формат**: JSON-массив с полями `type`, `text`, `datetime` (опционально)
- **Кодировка**: UTF-8 с сохранением Cyrillic

Пример структуры:
```json
[
  {
    "type": "task",
    "text": "Купить хлеб",
    "datetime": "2026-07-15 14:30:00"
  },
  {
    "type": "note",
    "text": "Важная идея"
  }
]
```

### 4. Настройка диктовки

- По умолчанию используется язык распознавания `ru-RU`
- После распознавания тип автоматически определяется как `task`, `note` или `idea`
- Сам аудиофайл в JSON/PostgreSQL не сохраняется, сохраняется только распознанный текст и определенный тип
- Для смены языка задайте переменную окружения:

```bash
export ADHD_DICTATE_LANGUAGE=en-US
python app/main.py dictate
```

- Если микрофон недоступен, используйте аудиофайл:

```bash
python app/main.py dictate /path/to/audio.wav
```

- Если хотите вручную переопределить тип, это все еще можно сделать:

```bash
python app/main.py dictate task /path/to/audio.wav
python app/main.py task "Купить продукты"
```

### 5. Работа со схожестью, связями и объединением

Эти команды требуют **PostgreSQL backend**, потому что записывают данные в:
- `item_dependency`
- `item_merge`
- `item_audit`

Подготовка:

```bash
export ADHD_STORAGE_BACKEND=postgres
export DATABASE_URL=******localhost:5432/adhd_assistant
make migrate-up
```

Поиск похожих записей и сохранение предложений:

```bash
python app/main.py suggest-relations
```

Что делает команда:
- сравнивает активные `task`, `note`, `idea`
- ищет дубликаты и связанные записи по текстовой схожести
- записывает предложения в `item_dependency` с `is_confirmed = false`

Просмотр сохраненных связей:

```bash
# Все связи
python app/main.py list-relations

# Только для одного элемента по его номеру из list all
python app/main.py list-relations 3
```

Явное связывание элементов:

```bash
python app/main.py link-items 2 5 related "Обе записи про один контекст"
python app/main.py link-items 4 2 depends_on "Сначала нужно закрыть базовую задачу"
python app/main.py link-items 3 7 duplicate_of "Повтор той же идеи"
```

Поддерживаемые типы CLI-связей:
- `related`
- `depends_on`
- `duplicate_of`

В PostgreSQL они сохраняются как:
- `related` -> `relates_to`
- `depends_on` -> `blocked_by`
- `duplicate_of` -> `duplicate_of`

Подтверждение предложенной связи:

```bash
python app/main.py confirm-relation 3 7 duplicate_of
```

Группировка в кластеры похожих записей:

```bash
python app/main.py show-clusters
```

Команда показывает группы элементов, которые связаны предложениями `related` или `duplicate_of`.

Подтверждаемое объединение нескольких записей в одну:

```bash
python app/main.py merge-items 3 7 8 --reason "Объединяем дубликаты одной идеи"
```

Что делает merge:
- обновляет текст целевой записи
- сохраняет историю объединения в `item_merge`
- помечает исходные элементы как `archived`
- создает подтвержденные `duplicate_of` связи
- пишет историю в `item_audit`

---

## 🧪 Разработка

### Проверка модулей

```bash
make check
```

Проверяет синтаксис Python модулей.

### Запуск тестов

```bash
# Все тесты
make test

# Один тест
make test-one TEST=tests/test_item_service.py::test_add_and_list_with_legacy_format
```

Тесты используют временные файлы и не трогают `data/notes.json`.

---

## 🐘 Переход на PostgreSQL

### Шаг 1: Поднять PostgreSQL

**Вариант A: Docker (рекомендуется)**
```bash
docker-compose up -d
```

**Вариант B: Локальная установка PostgreSQL**
```bash
# Убедиться, что PostgreSQL запущен
psql --version
```

### Шаг 2: Применить схему БД

```bash
export DATABASE_URL=postgresql://adhd:adhd@localhost:5432/adhd_assistant
make migrate-up
```

Команда создаст все таблицы, индексы и триггеры.

### Шаг 3: Переключить CLI на PostgreSQL

```bash
export ADHD_STORAGE_BACKEND=postgres
export DATABASE_URL=postgresql://adhd:adhd@localhost:5432/adhd_assistant
python app/main.py list all
```

Команды CLI остаются теми же, но данные теперь читаются из PostgreSQL.

### Шаг 4: Импортировать данные из JSON (опционально)

Если у вас уже есть данные в `data/notes.json`:

```bash
make migrate-import-json
```

Это:
- Прочитает `data/notes.json`
- Создаст default-проект "Inbox"
- Вставит все записи в таблицу `item`
- Сохранит информацию о миграции в таблице `migration_run`

Проверить импорт:
```bash
psql "$DATABASE_URL" -c "SELECT COUNT(*) FROM item;"
```

---

## ↩️ Откат и отладка

### Откатить последний импорт JSON

Если импорт не понравился:

```bash
make migrate-rollback
```

Это:
- Найдет последнюю успешную миграцию
- Удалит все элементы с меткой `source = 'cli_migration:<run_id>'`
- Очистит audit trail
- Пометит миграцию как "rolled_back"

### Полностью удалить PostgreSQL схему

```bash
make migrate-down
```

**Осторожно**: удалит ВСЕ таблицы и функции.

---

## 🔄 Переключение между backends

### JSON → PostgreSQL

```bash
export ADHD_STORAGE_BACKEND=postgres
export DATABASE_URL=postgresql://...
python app/main.py list all
```

### PostgreSQL → JSON

```bash
export ADHD_STORAGE_BACKEND=json
export ADHD_NOTES_PATH=data/notes.json
python app/main.py list all
```

Оба режима работают одновременно — выбирает текущий environment переменные.

---

## 📊 Инспекция данных

### PostgreSQL

```bash
export DATABASE_URL=postgresql://adhd:adhd@localhost:5432/adhd_assistant

# Показать все элементы
psql "$DATABASE_URL" -c "SELECT id, type, text, status, created_at FROM item LIMIT 20;"

# Показать по типам
psql "$DATABASE_URL" -c "SELECT type, COUNT(*) FROM item GROUP BY type;"

# Показать зависимости
psql "$DATABASE_URL" -c "SELECT * FROM item_dependency LIMIT 10;"

# Показать историю изменений
psql "$DATABASE_URL" -c "SELECT * FROM item_audit LIMIT 10;"
```

### JSON

```bash
python -c "import json; data = json.load(open('data/notes.json')); print(json.dumps(data, indent=2, ensure_ascii=False))"
```

---

## 🏗️ Архитектура этого релиза

### Текущее состояние

- **v1.0 (this release)**:
  - JSON-хранилище по умолчанию (полностью функционально)
  - PostgreSQL backend для будущих миграций
  - Basic service layer и CLI
  - Наследование legacy-формата (type/text/datetime)

### Где это используется

| Компонент | Статус | Примечание |
|-----------|--------|-----------|
| Захват заметок | ✅ Работает | `python app/main.py task/note/idea "текст"` и `python app/main.py capture "текст"` |
| Список | ✅ Работает | `python app/main.py list task/note/idea/all` |
| JSON-хранилище | ✅ Работает | По умолчанию, `data/notes.json` |
| PostgreSQL backend | ✅ Готов | Переключается через env vars |
| Миграция JSON → PG | ✅ Работает | `make migrate-import-json` |
| Откат миграции | ✅ Работает | `make migrate-rollback` |
| Поиск похожих записей | ✅ Работает | `python app/main.py suggest-relations` |
| Кластеры похожих записей | ✅ Работает | `python app/main.py show-clusters` |
| Явные связи и зависимости | ✅ Работает | `python app/main.py link-items ...` |
| Подтверждение предложений | ✅ Работает | `python app/main.py confirm-relation ...` |
| Объединение записей | ✅ Работает | `python app/main.py merge-items ...` |
| Планирование (features) | 🔄 На будущее | Таблицы `daily_plan`, `focus_session` готовы |
| Анализ паттернов (features) | 🔄 На будущее | Таблица `item_audit` собирает данные |

---

## ⚠️ Известные ограничения v1.0

1. **Нет LLM/embeddings-анализа**: классификация и схожесть сейчас rule-based/heuristic
2. **Нет UI**: только CLI
3. **Нет многопользовательского режима**: один пользователь в рамках одного инстанса
4. **Расширенные связи и merge требуют PostgreSQL**: JSON-режим не хранит `item_dependency` и `item_merge`
5. **Нет напоминаний**: структура готова, но функциональность не реализована

---

## 🚢 Следующие этапы

- v1.1: AI-выявление дубликатов и зависимостей
- v1.2: Адаптивное планирование дня
- v2.0: Web UI и многопользовательская поддержка

---

## 📚 Дополнительные ресурсы

- **Архитектура**: `AI/00_constitution.md`, `AI/01_architecture.md`
- **Видение**: `AI/05_product_vision.md`
- **База данных**: `docs/database_schema.md`, `docs/workflows.md`
- **Инструкции для AI**: `.github/copilot-instructions.md`

---

## 🐛 Помощь и обратная связь

- Если JSON-режим не работает: проверьте `data/notes.json` (должен быть valid JSON)
- Если PostgreSQL-миграция неудачна: выполните `make migrate-down` и повторите
- Если тесты падают: запустите `make check` для проверки синтаксиса

---

**v1.0 Ready!** Наслаждайтесь быстрым захватом мыслей. 🎯
