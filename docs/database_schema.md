# ER-диаграмма базы данных ADHD Assistant

```mermaid
erDiagram
    PROJECT ||--o{ ITEM : contains
    PROJECT ||--o{ DAILY_PLAN : has
    
    ITEM ||--o{ ITEM : has_parent
    ITEM ||--o{ ITEM_DEPENDENCY : from
    ITEM ||--o{ ITEM_DEPENDENCY : to
    ITEM ||--o{ ITEM_AUDIT : tracked_by
    ITEM ||--o{ ITEM_MERGE : merged_into
    ITEM ||--o{ ATTACHMENT : has
    ITEM ||--o{ REMINDER : has
    ITEM ||--o{ FOCUS_SESSION : covers
    
    ITEM_MERGE ||--o{ ITEM : has_sources
    
    USER_PROFILE ||--o{ USER_SESSION : creates
    USER_PROFILE ||--o{ DAILY_PLAN : plans
    
    USER_SESSION ||--o{ DAILY_PLAN : defines
    USER_SESSION ||--o{ FOCUS_SESSION : tracks
    
    DAILY_PLAN ||--o{ DAILY_PLAN_ITEM : contains
    DAILY_PLAN_ITEM ||--o{ ITEM : references
    DAILY_PLAN_ITEM ||--o{ FOCUS_SESSION : has
    
    INBOX_ENTRY ||--o{ ITEM : converts_to
    
    PROJECT {
        uuid id PK
        string name
        text description
        string status
        timestamp created_at
        timestamp updated_at
    }
    
    ITEM {
        uuid id PK
        uuid project_id FK
        uuid parent_id FK
        string type "task, note, idea, reminder, reference"
        text text
        string[] tags
        string category
        string status "pending, in_progress, done, archived, blocked"
        string priority "high, medium, low"
        string energy_level "low, medium, high"
        int time_estimate "минут"
        string difficulty "easy, medium, hard"
        timestamp deadline
        timestamp completed_at
        string source "cli, api, web, email"
        timestamp created_at
        timestamp updated_at
    }
    
    ITEM_DEPENDENCY {
        uuid id PK
        uuid from_item_id FK
        uuid to_item_id FK
        string relationship_type "blocks, blocked_by, relates_to, duplicate_of, subtask_of"
        text reason
        boolean is_confirmed
        timestamp confirmed_at
        timestamp created_at
        timestamp updated_at
    }
    
    ITEM_AUDIT {
        uuid id PK
        uuid item_id FK
        string action "created, updated, merged, split, archived"
        jsonb old_value
        jsonb new_value
        text reason
        timestamp performed_at
    }
    
    ITEM_MERGE {
        uuid id PK
        uuid merged_into_id FK
        uuid[] merged_from_ids
        jsonb merged_from_content
        text merge_reason
        timestamp performed_at
        boolean can_undo
    }
    
    ATTACHMENT {
        uuid id PK
        uuid item_id FK
        string name
        string type "image, document, link, file, note"
        string mime_type
        string path "для файлов"
        string url "для ссылок"
        int size "байты"
        jsonb metadata
        timestamp created_at
    }
    
    REMINDER {
        uuid id PK
        uuid item_id FK
        timestamp scheduled_at
        string recurring "none, daily, weekly, monthly, yearly"
        timestamp last_triggered_at
        boolean is_active
        string delivery_method "notification, email, sms"
        timestamp created_at
        timestamp updated_at
    }
    
    USER_PROFILE {
        uuid id PK
        string timezone
        int preferred_focus_duration "минут"
        int preferred_break_duration "минут"
        jsonb tags_aliases
        jsonb preferences
        timestamp created_at
        timestamp updated_at
    }
    
    USER_SESSION {
        uuid id PK
        uuid user_profile_id FK
        date session_date
        string energy_level "low, medium, high"
        text mood
        int focus_capacity "0-100%"
        text external_blockers
        timestamp created_at
        timestamp updated_at
    }
    
    DAILY_PLAN {
        uuid id PK
        uuid user_profile_id FK
        uuid user_session_id FK
        uuid project_id FK
        date plan_date
        text notes
        timestamp created_at
        timestamp updated_at
    }
    
    DAILY_PLAN_ITEM {
        uuid id PK
        uuid daily_plan_id FK
        uuid item_id FK
        int position "порядок в плане"
        string status_on_plan "pending, completed, skipped"
        timestamp created_at
    }
    
    FOCUS_SESSION {
        uuid id PK
        uuid daily_plan_item_id FK
        uuid item_id FK
        uuid user_session_id FK
        int planned_duration "минут"
        timestamp started_at
        timestamp completed_at
        int actual_duration "минут"
        int break_duration "минут"
        int distractions "количество"
        text interruptions
        text notes
        timestamp created_at
        timestamp updated_at
    }
    
    INBOX_ENTRY {
        uuid id PK
        text raw_text
        string source "cli, api, web, email"
        string suggested_type
        string[] suggested_tags
        uuid suggested_project_id
        string status "unprocessed, processed, converted_to_item"
        uuid converted_to_item_id FK
        timestamp created_at
        timestamp updated_at
    }
```

## Описание слоев

### 🔵 Слой захвата (INBOX_ENTRY)
- Быстрая фиксация мыслей без структуры
- AI предлагает тип, теги, проект
- Пользователь подтверждает → конвертируется в ITEM

### 🟢 Слой базовых данных (ITEM + PROJECT)
- Единая таблица `ITEM` для всех типов (task, note, idea, reminder)
- Иерархия: подзадачи через `parent_id`
- Поля для ADHD: `energy_level`, `time_estimate`, `difficulty`

### 🔴 Слой связей (ITEM_DEPENDENCY)
- **Ключевой компонент**: выявление зависимостей
- Типы: blocks, blocked_by, relates_to, duplicate_of, subtask_of
- `is_confirmed`: AI предлагает, пользователь подтверждает

### 🟡 Слой истории (ITEM_AUDIT + ITEM_MERGE)
- `ITEM_AUDIT`: каждое изменение записано
- `ITEM_MERGE`: при объединении заметок сохраняются исходные данные
- Полный откат и анализ возможны

### 🟣 Слой планирования (DAILY_PLAN + FOCUS_SESSION)
- `USER_PROFILE`: долгосрочные предпочтения
- `USER_SESSION`: состояние на конкретный день (энергия, настроение)
- `DAILY_PLAN`: рекомендуемый план на день с учетом зависимостей
- `FOCUS_SESSION`: отслеживание реального времени работы (Pomodoro-like)

### 📎 Слой дополнений (ATTACHMENT + REMINDER)
- `ATTACHMENT`: файлы, изображения, ссылки
- `REMINDER`: повторяющиеся напоминания с доставкой

## Ключевые связи

| Операция | Таблицы | Описание |
|----------|---------|---------|
| **Захват заметки** | INBOX_ENTRY → ITEM | Пользователь вводит текст → AI организует → ITEM |
| **Выявление зависимостей** | ITEM → ITEM_DEPENDENCY | AI анализирует тексты → предлагает связи |
| **Объединение дубликатов** | ITEM + ITEM_MERGE | Две ITEM → ITEM_MERGE с историей → одна ITEM |
| **Планирование дня** | ITEM + DAILY_PLAN_ITEM | Выбрать задачи на день с учетом зависимостей |
| **Работа над задачей** | DAILY_PLAN_ITEM → FOCUS_SESSION | Сеанс концентрации, отслеживание прогресса |
| **Анализ паттернов** | USER_SESSION + ITEM_AUDIT + FOCUS_SESSION | Какие задачи делают в какое время, энергия |

## Статусы и переходы

### ITEM.status
```
pending → in_progress → done
   ↓
blocked (требует разрешения ITEM_DEPENDENCY)
   ↓
archived
```

### ITEM_DEPENDENCY.is_confirmed
```
FALSE (AI предложение)
   ↓ пользователь подтверждает
TRUE (активная зависимость)
```

### DAILY_PLAN_ITEM.status_on_plan
```
pending → completed
   ↓
skipped
   ↓
moved_to_later (в следующий день)
```

## Примеры запросов

### 1. Показать заблокированные задачи
```sql
SELECT i.id, i.text, blocking.text as blocked_by
FROM item i
JOIN item_dependency d ON i.id = d.to_item_id AND d.relationship_type = 'blocks'
JOIN item blocking ON d.from_item_id = blocking.id
WHERE i.status = 'blocked' AND blocking.status != 'done';
```

### 2. Найти дубликаты
```sql
SELECT i1.id, i1.text, i2.id, i2.text
FROM item i1
JOIN item_dependency d ON i1.id = d.from_item_id
JOIN item i2 ON d.to_item_id = i2.id
WHERE d.relationship_type = 'duplicate_of' AND d.is_confirmed = FALSE;
```

### 3. План на день с учетом энергии
```sql
SELECT dp.plan_date, i.text, i.time_estimate, i.energy_level
FROM daily_plan_item dpi
JOIN daily_plan dp ON dpi.daily_plan_id = dp.id
JOIN item i ON dpi.item_id = i.id
JOIN user_session us ON dp.user_session_id = us.id
WHERE dp.plan_date = CURRENT_DATE
  AND us.energy_level = 'high'
  AND i.energy_level IN ('high', 'medium', NULL)
ORDER BY dpi.position;
```

### 4. Анализ продуктивности
```sql
SELECT 
    DATE(fs.completed_at) as work_date,
    us.energy_level,
    COUNT(fs.id) as focus_sessions,
    AVG(fs.actual_duration) as avg_duration,
    COUNT(CASE WHEN i.status = 'done' THEN 1 END) as completed_tasks
FROM focus_session fs
JOIN item i ON fs.item_id = i.id
JOIN user_session us ON fs.user_session_id = us.id
WHERE fs.completed_at >= CURRENT_DATE - INTERVAL 7 DAY
GROUP BY DATE(fs.completed_at), us.energy_level
ORDER BY work_date DESC;
```
