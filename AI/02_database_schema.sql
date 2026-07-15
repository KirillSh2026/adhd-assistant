-- Целевая схема БД для ADHD AI Assistant
-- Поддерживает: захват заметок, организацию, выявление зависимостей, планирование
-- Совместима с миграцией из data/notes.json

-- ============ ОСНОВНЫЕ ТАБЛИЦЫ ============

CREATE TABLE project (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'active', -- 'active', 'archived', 'deleted'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE item (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES project(id) ON DELETE SET NULL,
    parent_id UUID REFERENCES item(id) ON DELETE SET NULL,
    
    -- Содержимое
    type VARCHAR(50) NOT NULL, -- 'task', 'note', 'idea', 'reminder', 'reference'
    text TEXT NOT NULL,
    
    -- Организация
    tags TEXT[], -- массив тегов
    category VARCHAR(100),
    
    -- Статус и приоритет
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'in_progress', 'done', 'archived', 'blocked'
    priority VARCHAR(50), -- 'high', 'medium', 'low', null
    
    -- Для ADHD
    energy_level VARCHAR(50), -- 'low', 'medium', 'high', null
    time_estimate INT, -- минут на выполнение, null если неизвестно
    difficulty VARCHAR(50), -- 'easy', 'medium', 'hard', null
    
    -- Сроки
    deadline TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- Техническое
    source VARCHAR(50) DEFAULT 'cli', -- 'cli', 'api', 'web', 'email'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_project(project_id),
    INDEX idx_status(status),
    INDEX idx_priority(priority),
    INDEX idx_created(created_at)
);

-- ============ ЗАВИСИМОСТИ (КЛЮЧЕВОЙ КОМПОНЕНТ) ============

CREATE TABLE item_dependency (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_item_id UUID NOT NULL REFERENCES item(id) ON DELETE CASCADE,
    to_item_id UUID NOT NULL REFERENCES item(id) ON DELETE CASCADE,
    
    -- Тип отношения
    relationship_type VARCHAR(50) NOT NULL, -- 'blocks', 'blocked_by', 'relates_to', 'duplicate_of', 'subtask_of', 'parent_of'
    reason TEXT, -- почему есть зависимость
    
    -- Подтверждение пользователем
    is_confirmed BOOLEAN DEFAULT FALSE,
    confirmed_at TIMESTAMP,
    
    -- Техническое
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT no_self_dependency CHECK (from_item_id != to_item_id),
    UNIQUE(from_item_id, to_item_id, relationship_type),
    INDEX idx_from(from_item_id),
    INDEX idx_to(to_item_id),
    INDEX idx_confirmed(is_confirmed)
);

-- ============ ИСТОРИЯ И АУДИТ ============

CREATE TABLE item_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_id UUID NOT NULL REFERENCES item(id) ON DELETE CASCADE,
    
    action VARCHAR(50) NOT NULL, -- 'created', 'updated', 'merged', 'split', 'archived', 'status_changed'
    
    -- Старое и новое значение (для важных полей)
    old_value JSONB,
    new_value JSONB,
    
    -- Контекст
    reason TEXT,
    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_item(item_id),
    INDEX idx_action(action),
    INDEX idx_performed(performed_at)
);

CREATE TABLE item_merge (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merged_into_id UUID NOT NULL REFERENCES item(id) ON DELETE CASCADE,
    
    -- Исходные записи (JSON, для сохранения истории)
    merged_from_ids UUID[] NOT NULL,
    merged_from_content JSONB, -- содержимое исходных записей
    
    merge_reason TEXT,
    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Возможность отката
    can_undo BOOLEAN DEFAULT TRUE,
    
    INDEX idx_merged_into(merged_into_id)
);

-- ============ ВЛОЖЕНИЯ ============

CREATE TABLE attachment (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_id UUID NOT NULL REFERENCES item(id) ON DELETE CASCADE,
    
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL, -- 'image', 'document', 'link', 'file', 'note'
    mime_type VARCHAR(100),
    
    -- Хранилище
    path VARCHAR(500), -- для локальных файлов
    url VARCHAR(500), -- для ссылок
    size INT, -- в байтах
    
    metadata JSONB, -- доп. данные (размеры изображения, автор ссылки и т.д.)
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_item(item_id),
    INDEX idx_type(type)
);

-- ============ НАПОМИНАНИЯ ============

CREATE TABLE reminder (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_id UUID NOT NULL REFERENCES item(id) ON DELETE CASCADE,
    
    scheduled_at TIMESTAMP NOT NULL,
    recurring VARCHAR(50) DEFAULT 'none', -- 'none', 'daily', 'weekly', 'monthly', 'yearly'
    
    -- Отслеживание
    last_triggered_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    
    delivery_method VARCHAR(50) DEFAULT 'notification', -- 'notification', 'email', 'sms'
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_item(item_id),
    INDEX idx_scheduled(scheduled_at),
    INDEX idx_active(is_active)
);

-- ============ ПРОФИЛЬ И СОСТОЯНИЕ ПОЛЬЗОВАТЕЛЯ ============

CREATE TABLE user_profile (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    timezone VARCHAR(50) DEFAULT 'UTC',
    preferred_focus_duration INT DEFAULT 25, -- минут
    preferred_break_duration INT DEFAULT 5, -- минут
    
    -- Синонимы тегов для организации
    tags_aliases JSONB, -- { "urgent": ["asap", "now"], "shopping": ["shop", "buy"] }
    
    preferences JSONB, -- любые другие предпочтения
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_session (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_profile_id UUID REFERENCES user_profile(id) ON DELETE SET NULL,
    
    session_date DATE NOT NULL,
    
    -- Состояние в этот день
    energy_level VARCHAR(50), -- 'low', 'medium', 'high'
    mood TEXT, -- свободное описание
    focus_capacity INT, -- 0-100, % умственной работоспособности
    
    -- Внешние факторы
    external_blockers TEXT, -- что сейчас мешает
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_profile_id, session_date),
    INDEX idx_profile(user_profile_id),
    INDEX idx_date(session_date)
);

-- ============ ЕЖЕДНЕВНЫЙ ПЛАН ============

CREATE TABLE daily_plan (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_profile_id UUID REFERENCES user_profile(id) ON DELETE SET NULL,
    user_session_id UUID REFERENCES user_session(id) ON DELETE SET NULL,
    
    plan_date DATE NOT NULL,
    project_id UUID REFERENCES project(id) ON DELETE SET NULL,
    
    notes TEXT, -- заметки по плану на день
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_profile_id, plan_date),
    INDEX idx_profile(user_profile_id),
    INDEX idx_date(plan_date)
);

CREATE TABLE daily_plan_item (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    daily_plan_id UUID NOT NULL REFERENCES daily_plan(id) ON DELETE CASCADE,
    item_id UUID NOT NULL REFERENCES item(id) ON DELETE CASCADE,
    
    position INT NOT NULL, -- порядок в плане (для сортировки)
    status_on_plan VARCHAR(50) DEFAULT 'pending', -- 'pending', 'completed', 'skipped', 'moved_to_later'
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(daily_plan_id, item_id),
    INDEX idx_plan(daily_plan_id),
    INDEX idx_item(item_id)
);

-- ============ СЕАНСЫ КОНЦЕНТРАЦИИ (POMODORO-LIKE) ============

CREATE TABLE focus_session (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    daily_plan_item_id UUID REFERENCES daily_plan_item(id) ON DELETE SET NULL,
    
    item_id UUID NOT NULL REFERENCES item(id) ON DELETE CASCADE,
    user_session_id UUID REFERENCES user_session(id) ON DELETE SET NULL,
    
    -- План
    planned_duration INT NOT NULL, -- минут (рекомендуемая длительность)
    
    -- Выполнение
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    actual_duration INT, -- минут (реально отработал)
    break_duration INT, -- минут (перерыв после сеанса)
    
    -- Качество
    distractions INT DEFAULT 0, -- сколько раз отвлекался
    interruptions TEXT, -- что помешало
    notes TEXT, -- впечатления от работы
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_item(item_id),
    INDEX idx_user_session(user_session_id),
    INDEX idx_completed(completed_at)
);

-- ============ ВХОДЯЩИЕ (БЫСТРЫЙ ЗАХВАТ) ============

CREATE TABLE inbox_entry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    raw_text TEXT NOT NULL, -- как пользователь ввел
    source VARCHAR(50) DEFAULT 'cli', -- откуда пришло
    
    -- Предложения AI для организации
    suggested_type VARCHAR(50), -- что AI думает, что это
    suggested_tags TEXT[],
    suggested_project_id UUID,
    
    status VARCHAR(50) DEFAULT 'unprocessed', -- 'unprocessed', 'processed', 'converted_to_item'
    converted_to_item_id UUID REFERENCES item(id) ON DELETE SET NULL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_status(status),
    INDEX idx_created(created_at)
);

-- ============ ИНДЕКСЫ ДЛЯ ЧАСТЫХ ЗАПРОСОВ ============

CREATE INDEX idx_item_by_project_status ON item(project_id, status);
CREATE INDEX idx_item_by_deadline ON item(deadline) WHERE deadline IS NOT NULL;
CREATE INDEX idx_item_by_energy ON item(energy_level) WHERE energy_level IS NOT NULL;
CREATE INDEX idx_dependency_blocked_by ON item_dependency(to_item_id) WHERE relationship_type = 'blocks';
CREATE INDEX idx_daily_plan_items_by_position ON daily_plan_item(daily_plan_id, position);

-- ============ ТРИГГЕРЫ ДЛЯ АВТОМАТИЧЕСКОГО ОБНОВЛЕНИЯ ============

-- Обновить updated_at при изменении item
CREATE TRIGGER update_item_updated_at
BEFORE UPDATE ON item
FOR EACH ROW
SET updated_at = CURRENT_TIMESTAMP;

-- Создать запись в audit при изменении item
CREATE TRIGGER audit_item_update
AFTER UPDATE ON item
FOR EACH ROW
INSERT INTO item_audit (item_id, action, old_value, new_value)
VALUES (
    NEW.id,
    'updated',
    jsonb_build_object('status', OLD.status, 'priority', OLD.priority, 'text', OLD.text),
    jsonb_build_object('status', NEW.status, 'priority', NEW.priority, 'text', NEW.text)
);
