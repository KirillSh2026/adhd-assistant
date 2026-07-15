# Архитектура базы данных

**Полная SQL-схема:** см. `AI/02_database_schema.sql`

## Текущая схема (из project_schem_ADHD.drawio)

**Сущности:**
- PROJECT, ITEM, TASK, NOTE, IDEA
- REMINDER, ATTACHMENT
- UserState, DailyPlan, FocusSession

**Основные проблемы:**

### 1. Полиморфизм ITEM / TASK / NOTE / IDEA

**Проблема:** TASK, NOTE, IDEA выглядят как отдельные таблицы, но по логике — это типы ITEM.

**Рекомендация:**
```
ITEM
├── id (UUID)
├── project_id (FK → PROJECT)
├── parent_id (FK → ITEM, для подзадач)
├── type (ENUM: 'task', 'note', 'idea', 'reminder')
├── text (TEXT)
├── tags (JSON или отдельная таблица ITEM_TAGS)
├── status (ENUM: 'pending', 'in_progress', 'done', 'archived')
├── priority (ENUM: 'high', 'medium', 'low', null)
├── energy_level (ENUM: 'low', 'medium', 'high', null)
├── time_estimate (INT minutes, null)
├── deadline (TIMESTAMP, null)
├── created_at, updated_at, completed_at
└── source ('cli', 'api', 'web', etc.)

ITEM_TASK (для полей, специфичных только задачам)
├── item_id (FK → ITEM, PK)
└── ... специфичные поля

ITEM_NOTE, ITEM_IDEA — аналогично
```

**Преимущество:** единая логика поиска, фильтрации, сортировки; легче добавлять новые типы.

### 2. Зависимости между задачами (КРИТИЧЕСКОЕ)

**Проблема:** В текущей схеме нет явной таблицы для выявления и хранения зависимостей.

**Рекомендация добавить:**
```
ITEM_DEPENDENCY
├── id (UUID, PK)
├── from_item_id (FK → ITEM)
├── to_item_id (FK → ITEM)
├── relationship_type (ENUM: 'blocks', 'blocked_by', 'relates_to', 'duplicate_of', 'subtask_of')
├── created_at, updated_at
└── is_confirmed (BOOLEAN, false до подтверждения пользователем)
```

Это ключевой элемент Vision: выявление связей, определение заблокированных задач, планирование порядка.

### 3. DailyPlan.id_items — нарушает нормальную форму

**Проблема:** Хранение массива ID в одном поле неудобно для запросов.

**Рекомендация:**
```
DAILY_PLAN
├── id (UUID, PK)
├── user_date (DATE, для привязки к дню)
├── project_id (FK → PROJECT, опционально)
├── user_state_id (FK → USER_STATE)
└── created_at, updated_at

DAILY_PLAN_ITEM (связь многие-ко-многим)
├── daily_plan_id (FK → DAILY_PLAN)
├── item_id (FK → ITEM)
├── position (INT, для сохранения порядка)
└── status_on_plan ('pending', 'completed', 'skipped')
```

### 4. UserState: разделить на сеанс и долгосрочный профиль

**Проблема:** Текущая структура смешивает состояние прямо сейчас с профилем пользователя.

**Рекомендация:**
```
USER_PROFILE
├── id (UUID, PK)
├── timezone (STRING)
├── preferred_focus_duration (INT minutes, default 25)
├── preferred_break_duration (INT minutes, default 5)
├── tags_aliases (JSON, для синонимов)
└── preferences (JSON)

USER_SESSION
├── id (UUID, PK)
├── date (DATE)
├── energy_level (ENUM: 'low', 'medium', 'high')
├── mood (TEXT, опционально)
├── focus_capacity (INT 0-100, опционально)
├── external_blockers (TEXT, что мешает)
└── created_at, updated_at
```

**Преимущество:** разделение "состояния сейчас" от "предпочтений", возможность анализа долгосрочных паттернов.

### 5. FocusSession: уточнить связи

**Проблема:** FocusSession имеет прямые связи с project_id и item_id, но они уже есть через DailyPlan.

**Рекомендация:**
```
FOCUS_SESSION
├── id (UUID, PK)
├── daily_plan_item_id (FK → DAILY_PLAN_ITEM)
├── planned_duration (INT minutes)
├── actual_duration (INT minutes, null до завершения)
├── break_duration (INT minutes, null)
├── started_at, completed_at (TIMESTAMP)
├── notes (TEXT, что происходило)
└── distractions (JSON, опционально)
```

**Преимущество:** явная иерархия: DailyPlan → Item → FocusSession; нет дублирования FK.

### 6. Отсутствует таблица для истории объединения заметок

**Проблема:** При объединении заметок нужно сохранять исходные данные и ссылку на объединение.

**Рекомендация добавить:**
```
ITEM_MERGE
├── id (UUID, PK)
├── merged_into_id (FK → ITEM, финальная запись)
├── merged_from_ids (JSON или отдельная таблица)
├── merge_reason (TEXT)
├── performed_by (USER_ID, если многопользовательский)
├── created_at
└── can_undo (BOOLEAN)

ITEM_AUDIT
├── id (UUID, PK)
├── item_id (FK → ITEM)
├── action ('created', 'updated', 'merged', 'split', 'archived')
├── old_value (JSON)
├── new_value (JSON)
├── performed_at
└── reason (TEXT)
```

### 7. ATTACHMENT: уточнить связи

**Проблема:** Текущий дизайн неполный.

**Рекомендация:**
```
ATTACHMENT
├── id (UUID, PK)
├── item_id (FK → ITEM)
├── name (STRING)
├── type (ENUM: 'image', 'document', 'link', 'file')
├── mime_type (STRING, для файлов)
├── path (STRING, для локальных файлов)
├── url (STRING, для ссылок)
├── size (INT bytes, опционально)
├── created_at
└── metadata (JSON)
```

### 8. REMINDER: переместить в зависимость от ITEM

**Текущее состояние:** хорошо, но нужно уточнить структуру.

**Уточнение:**
```
REMINDER
├── id (UUID, PK)
├── item_id (FK → ITEM)
├── scheduled_at (TIMESTAMP)
├── recurring (ENUM: 'none', 'daily', 'weekly', 'monthly', 'yearly')
├── last_triggered_at (TIMESTAMP, для отслеживания)
├── is_active (BOOLEAN)
└── delivery_method (ENUM: 'notification', 'email', 'sms')
```

## Резюме изменений

| Исправить | Статус |
|-----------|--------|
| Унифицировать TASK/NOTE/IDEA в ITEM с типом | **КРИТИЧ** |
| Добавить ITEM_DEPENDENCY для выявления связей | **КРИТИЧ** |
| Нормализовать DAILY_PLAN (убрать id_items) | **ВАЖНО** |
| Разделить UserState на профиль + сеанс | **ВАЖНО** |
| Добавить ITEM_AUDIT и ITEM_MERGE для истории | **ВАЖНО** |
| Уточнить иерархию FocusSession | **СРЕДНЕ** |
| Расширить ATTACHMENT | **СРЕДНЕ** |

## Порядок реализации

1. Сначала унифицировать ITEM (может быть breaking change, но необходимо).
2. Добавить ITEM_DEPENDENCY — ключ к функции "выявление связей".
3. Нормализовать DAILY_PLAN.
4. Добавить ITEM_AUDIT перед началом слияния заметок.
5. Разделить UserState когда будут анализы паттернов.

## Обратная совместимость

При переходе с текущего `data/notes.json` (простой JSON с type, text, datetime):

```python
# Миграция
for note in old_notes:
    item = Item(
        id=uuid(),
        type=note['type'],  # 'task', 'note', 'idea'
        text=note['text'],
        created_at=note.get('datetime'),
        status='pending' if type == 'task' else None,
        source='cli'
    )
    db.save(item)
```

Новая схема БД становится обязательной при переходе с JSON на PostgreSQL/SQLite.
