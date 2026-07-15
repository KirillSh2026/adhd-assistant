# Диаграммы потоков и взаимодействий

## 1. Жизненный цикл элемента (Item Lifecycle)

```mermaid
graph TD
    A["👤 Пользователь вводит текст<br/>python app/main.py task 'Купить хлеб'"] --> B["📥 INBOX_ENTRY<br/>raw_text='Купить хлеб'<br/>source='cli'"]
    
    B --> C{{"🤖 AI организует"}}
    
    C -->|Предложения| D["suggested_type: 'task'<br/>suggested_tags: ['shopping']<br/>suggested_priority: 'medium'"]
    
    D --> E{{"✅ Пользователь<br/>подтверждает"}}
    
    E -->|Да| F["➕ Создать ITEM<br/>type='task'<br/>text='Купить хлеб'<br/>status='pending'"]
    E -->|Нет| G["🔄 Отложить<br/>status='unprocessed'"]
    
    F --> H["🏷️ Добавить теги<br/>ITEM.tags=['shopping']"]
    
    H --> I["⏰ Установить<br/>deadline, priority,<br/>energy_level"]
    
    I --> J["🔗 Проверить<br/>зависимости<br/>ITEM_DEPENDENCY"]
    
    J --> K["📊 Добавить в<br/>DAILY_PLAN<br/>на дан день"]
    
    K --> L["💪 Начать работу<br/>status='in_progress'"]
    
    L --> M["⏱️ FOCUS_SESSION<br/>started_at,<br/>planned_duration,<br/>actual_duration"]
    
    M --> N{{"✔️ Завершено?"}}
    
    N -->|Да| O["✅ ITEM.status='done'<br/>ITEM.completed_at<br/>FOCUS_SESSION.actual_duration"]
    N -->|Нет| P["❌ ITEM.status='blocked'<br/>Зависит от:<br/>ITEM_DEPENDENCY.blocks"]
    
    O --> Q["📈 ITEM_AUDIT<br/>action='updated'<br/>old_value → new_value"]
    
    P --> R["🔄 Перепланировать<br/>в DAILY_PLAN"]
    
    Q --> S["📊 Анализ<br/>время, энергия,<br/>продуктивность"]
```

## 2. Выявление и управление зависимостями

```mermaid
graph LR
    A["📝 ITEM 1: 'Купить гвозди'"] --> B{{"🔍 AI анализирует<br/>содержимое"}}
    C["📝 ITEM 2: 'Повесить полку'"] --> B
    
    B --> D["🔗 Найдена связь<br/>ITEM_DEPENDENCY<br/>is_confirmed=FALSE"]
    
    D --> E["type: 'blocks'<br/>from: ITEM 2<br/>to: ITEM 1<br/>reason: 'нужны гвозди'"]
    
    E --> F{{"✅ Пользователь<br/>подтверждает"}}
    
    F -->|Да| G["✔️ is_confirmed=TRUE<br/>Активная зависимость"]
    F -->|Нет| H["❌ is_confirmed=FALSE<br/>Отклонено"]
    
    G --> I{{"📊 Планирование"}}
    
    I -->|ITEM 2 заблокирована| J["ITEM 2.status='blocked'<br/>Нельзя начать"]
    
    I -->|ITEM 1 свободна| K["ITEM 1.status='pending'<br/>Можно выбрать сегодня"]
    
    K --> L["✅ Выполнить ITEM 1"]
    
    L --> M["Когда ITEM 1 завершена"]
    
    M --> N["🔓 ITEM 2 разблокирована<br/>status='pending'"]
```

## 3. Объединение дубликатов

```mermaid
graph TD
    A["📝 ITEM 1<br/>text='Купить соль'<br/>created_at=2026-06-24"] --> B{{"🤖 AI обнаружила<br/>сходство"}}
    C["📝 ITEM 2<br/>text='Купить поваренную соль'<br/>created_at=2026-06-25"] --> B
    
    B --> D["⚠️ ITEM_DEPENDENCY<br/>type='duplicate_of'<br/>is_confirmed=FALSE"]
    
    D --> E["Причина: similarity > 0.8"]
    
    E --> F{{"✅ Пользователь решает"}}
    
    F -->|Объединить| G["🔗 Создать ITEM_MERGE<br/>merged_into_id=ITEM1.id<br/>merged_from_ids=[ITEM2.id]"]
    
    G --> H["💾 Сохранить исходное<br/>ITEM_MERGE.merged_from_content<br/>ITEM_MERGE.performed_at"]
    
    H --> I["📜 Запись в ITEM_AUDIT<br/>action='merged'<br/>ITEM 2: old_value → deleted"]
    
    I --> J["✅ ITEM 2.status='archived'<br/>Но данные не потеряны!"]
    
    J --> K{{"↩️ Если нужно отменить"}}
    
    K -->|Undo| L["🔄 ITEM_MERGE.can_undo=TRUE<br/>Восстановить ITEM 2"]
    
    F -->|Оставить отдельно| M["❌ Отклонить объединение<br/>is_confirmed=FALSE"]
```

## 4. Построение плана на день

```mermaid
graph TD
    A["🌅 Новый день"] --> B["🔄 Загрузить USER_PROFILE"]
    B --> C["⚡ Получить USER_SESSION<br/>energy_level='medium'<br/>focus_capacity=75%"]
    
    C --> D["📋 Получить все ITEM.status='pending'"]
    
    D --> E{{"🔍 Фильтрация<br/>по критериям"}}
    
    E -->|Проверить зависимости| F["🔗 ITEM_DEPENDENCY<br/>Исключить заблокированные"]
    
    E -->|По энергии| G["⚡ ITEM.energy_level<br/>Соответствует user энергии"]
    
    E -->|По времени| H["⏱️ ITEM.time_estimate<br/>Сумма ≤ доступное время"]
    
    E -->|По приоритету| I["🎯 ITEM.priority<br/>Сортировка DESC"]
    
    F --> J["✅ Готовые задачи"]
    G --> J
    H --> J
    I --> J
    
    J --> K["📊 Создать DAILY_PLAN<br/>plan_date=TODAY"]
    
    K --> L["Добавить DAILY_PLAN_ITEM<br/>с position для сортировки"]
    
    L --> M["💡 Рекомендация<br/>3-5 приоритетных задач"]
    
    M --> N{{"👤 Пользователь<br/>утверждает план"}}
    
    N -->|Изменить порядок| O["🔄 Обновить DAILY_PLAN_ITEM.position"]
    N -->|Добавить задачу| P["➕ Добавить еще ITEM"]
    N -->|Удалить задачу| Q["❌ Удалить из плана<br/>status_on_plan='skipped'"]
    
    O --> R["✅ DAILY_PLAN готов"]
    P --> R
    Q --> R
    
    R --> S["🎬 Начать работу<br/>FOCUS_SESSION"]
```

## 5. Отслеживание прогресса (FOCUS_SESSION)

```mermaid
graph TD
    A["🎯 Выбрана DAILY_PLAN_ITEM<br/>ITEM='Купить хлеб'"] --> B["⏱️ Создать FOCUS_SESSION<br/>planned_duration=25 (Pomodoro)"]
    
    B --> C["🚀 START FOCUS_SESSION<br/>started_at=NOW<br/>distractions=0"]
    
    C --> D["💪 Пользователь работает"]
    
    D --> E{{"😳 Отвлёкся?"}}
    
    E -->|Да| F["⚠️ distractions+1<br/>interruptions='Телефон'"]
    F --> D
    
    E -->|Нет| G["✅ Продолжить"]
    G --> D
    
    D --> H{{"⏰ Время истекло?"}}
    
    H -->|Нет| I["⏳ Продолжить..."]
    I --> D
    
    H -->|Да| J["✔️ FOCUS_SESSION.completed_at=NOW<br/>actual_duration=25 мин"]
    
    J --> K{{"✅ Задача завершена?"}}
    
    K -->|Да| L["✅ ITEM.status='done'<br/>ITEM.completed_at=NOW"]
    K -->|Нет| M["❌ ITEM.status='pending'<br/>Еще нужно работать"]
    
    L --> N["☕ Перерыв<br/>FOCUS_SESSION.break_duration=5"]
    M --> N
    
    N --> O["📊 ITEM_AUDIT<br/>action='updated'<br/>status: pending → done"]
    
    O --> P["📈 Статистика<br/>Сохранено в БД<br/>для анализа продуктивности"]
```

## 6. Анализ паттернов (Insights)

```mermaid
graph TD
    A["📊 Запрос за неделю"] --> B["🔍 Анализ FOCUS_SESSION"]
    A --> C["🔍 Анализ USER_SESSION"]
    A --> D["🔍 Анализ ITEM_AUDIT"]
    
    B --> E["⏱️ Сколько времени<br/>на каждый тип"]
    C --> F["⚡ Как менялась энергия<br/>в течение недели"]
    D --> G["✅ Сколько задач<br/>завершено/отложено"]
    
    E --> H["📈 Отчет"]
    F --> H
    G --> H
    
    H --> I["💡 Выводы<br/>- В понедельник низкая энергия<br/>- Лучше работаю с TASK над NOTE<br/>- Нужно 30 мин на фокус"]
    
    I --> J{{"🎯 Рекомендации"}}
    
    J -->|Планирование| K["📋 На понедельник выбрать<br/>легкие задачи (energy=low)"]
    J -->|Организация| L["🏷️ Группировать похожие<br/>задачи вместе"]
    J -->|Мотивация| M["💪 Вы завершили 12 задач!<br/>Лучше чем неделю назад"]
```

---

## Ключевые объекты и их роли

| Таблица | Роль | Когда используется |
|---------|------|-------------------|
| **INBOX_ENTRY** | Входящее | Первый захват, перед организацией |
| **ITEM** | Базовая единица | Всегда (все операции) |
| **ITEM_DEPENDENCY** | Выявление связей | Планирование, фильтрация, анализ |
| **ITEM_AUDIT** | История изменений | Откат, анализ, контроль качества |
| **ITEM_MERGE** | Объединение дубликатов | Очистка, организация |
| **DAILY_PLAN** | План на день | Каждый день, в начале |
| **FOCUS_SESSION** | Отслеживание работы | Во время выполнения задачи |
| **USER_SESSION** | Состояние пользователя | Планирование, адаптивные рекомендации |

---

## Примеры сценариев

### Сценарий 1: Быстрый захват без организации
```
1. пользователь: "Купить продукты"
2. CLI добавляет в INBOX_ENTRY
3. AI предлагает тип='task', теги=['shopping']
4. Пользователь: "Согласен"
5. ITEM создана и добавлена в DAILY_PLAN
6. Готово за 10 секунд ✅
```

### Сценарий 2: Выявление зависимостей
```
1. ITEM: "Повесить полку"
2. ITEM: "Купить гвозди"
3. AI: "Гвозди нужны для полки?"
4. Пользователь: "Да"
5. ITEM_DEPENDENCY: 2 блокирует 1
6. При планировании: сначала гвозди, потом полка ✅
```

### Сценарий 3: Объединение дубликатов
```
1. ITEM: "Купить молоко"
2. ITEM: "Молоко купить"
3. AI: "Это одно и то же?"
4. Пользователь: "Да, объедини"
5. ITEM_MERGE сохраняет обе версии
6. ITEM остается одна, но история не потеряна ✅
```

### Сценарий 4: Адаптивное планирование
```
1. USER_SESSION: energy_level='low', focus_capacity=40%
2. Доступно: 2 часа
3. AI выбирает:
   - ITEM priority='high', energy='low', time=30 мин
   - ITEM priority='medium', energy='low', time=90 мин
   - Исключает: priority='low', energy='high'
4. Результат: реалистичный план на день ✅
```
