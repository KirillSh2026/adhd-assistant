-- Скрипт миграции с data/notes.json в целевую БД

-- ============ ШАГИ МИГРАЦИИ ============

-- 1. Создать профиль пользователя
INSERT INTO user_profile (timezone, preferences)
VALUES ('UTC', '{"source": "cli_migration"}')
RETURNING id AS user_profile_id;

-- 2. Создать проект по умолчанию
INSERT INTO project (name, description, status)
VALUES ('Inbox', 'Миграция из data/notes.json', 'active')
RETURNING id AS project_id;

-- 3. Обработка каждой заметки из JSON:
-- Пример Python-скрипта для миграции (используется в app/main.py при переходе на БД)

/*
import json
import uuid
from datetime import datetime
import psycopg2
from psycopg2.extras import Json

# Подключение к БД
conn = psycopg2.connect("dbname=adhd_assistant")
cur = conn.cursor()

# Загрузить старые заметки
with open('data/notes.json', 'r', encoding='utf-8') as f:
    old_notes = json.load(f)

# Получить ID профиля и проекта
cur.execute("SELECT id FROM user_profile LIMIT 1")
user_profile_id = cur.fetchone()[0]

cur.execute("SELECT id FROM project WHERE name = 'Inbox'")
project_id = cur.fetchone()[0]

# Конвертировать каждую заметку
for old_note in old_notes:
    item_id = str(uuid.uuid4())
    
    # Парсить дату, если есть
    created_at = None
    if 'datetime' in old_note:
        try:
            created_at = datetime.strptime(old_note['datetime'], '%Y-%m-%d %H:%M:%S')
        except:
            pass
    
    # Определить статус для задач
    status = 'done' if old_note.get('type') == 'task' else 'pending'
    
    # Вставить в новую таблицу
    cur.execute("""
        INSERT INTO item (
            id, project_id, type, text, status,
            source, created_at, updated_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        item_id,
        project_id,
        old_note.get('type', 'note'),
        old_note.get('text', ''),
        status,
        'cli_migration',
        created_at or datetime.now(),
        created_at or datetime.now()
    ))
    
    # Создать запись в audit для отслеживания
    cur.execute("""
        INSERT INTO item_audit (item_id, action, performed_at, reason)
        VALUES (%s, 'created', %s, 'Migrated from JSON')
    """, (item_id, created_at or datetime.now()))

conn.commit()
cur.close()
conn.close()

print(f"Перенесено {len(old_notes)} заметок из data/notes.json в БД")
*/

-- ============ ПРОВЕРКА МИГРАЦИИ ============

-- Убедиться, что все записи перенесены
SELECT COUNT(*) as total_items FROM item;

-- Показать по типам
SELECT type, COUNT(*) as count FROM item GROUP BY type;

-- Проверить наличие дублей (если какие-то заметки выглядят одинаково)
SELECT text, COUNT(*) as duplicates
FROM item
WHERE text IS NOT NULL AND text != ''
GROUP BY text
HAVING COUNT(*) > 1
ORDER BY duplicates DESC;

-- ============ ПОСЛЕ МИГРАЦИИ ============

-- 1. Выполнить анализ дубликатов (ITEM_DEPENDENCY с relationship_type = 'duplicate_of')
-- Пример: две разные заметки "Купить хлеб" и "Купить булку"

INSERT INTO item_dependency (from_item_id, to_item_id, relationship_type, reason, is_confirmed)
SELECT 
    i1.id, i2.id, 'duplicate_of',
    'Похожий текст, требует проверки',
    FALSE
FROM item i1
JOIN item i2 ON i1.id < i2.id
WHERE i1.project_id = i2.project_id
  AND (
      -- Строгая похожесть текста
      SIMILARITY(i1.text, i2.text) > 0.8
      -- Или точный совпадение
      OR i1.text = i2.text
  )
-- Не показывать уже обработанные
AND NOT EXISTS (
    SELECT 1 FROM item_dependency
    WHERE (from_item_id = i1.id AND to_item_id = i2.id)
       OR (from_item_id = i2.id AND to_item_id = i1.id)
);

-- 2. Проанализировать теги и автоматизировать организацию
-- (Это поле можно заполнить вручную через UI или с помощью NLP)

-- 3. Убедиться, что нет нарушений целостности
-- Проверить, что нет циклических зависимостей (если они возникли)
WITH RECURSIVE cycle_check AS (
    SELECT from_item_id, to_item_id, 1 as depth
    FROM item_dependency
    WHERE is_confirmed = TRUE
    
    UNION ALL
    
    SELECT c.from_item_id, d.to_item_id, c.depth + 1
    FROM cycle_check c
    JOIN item_dependency d ON c.to_item_id = d.from_item_id
    WHERE c.depth < 10 -- предотвращение бесконечного цикла
)
SELECT DISTINCT from_item_id, to_item_id
FROM cycle_check
WHERE from_item_id = to_item_id;

-- ============ ОТКАТ МИГРАЦИИ (ЕСЛИ НУЖНО) ============

/*
-- Удалить все из новых таблиц (ОСТОРОЖНО!)
DELETE FROM item_dependency;
DELETE FROM item_audit;
DELETE FROM focus_session;
DELETE FROM daily_plan_item;
DELETE FROM daily_plan;
DELETE FROM reminder;
DELETE FROM attachment;
DELETE FROM item;
DELETE FROM project;
DELETE FROM user_session;
DELETE FROM user_profile;
*/
