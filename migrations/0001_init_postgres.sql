BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS project (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT project_status_ck CHECK (status IN ('active', 'archived', 'deleted'))
);

CREATE TABLE IF NOT EXISTS item (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES project(id) ON DELETE SET NULL,
    parent_id UUID REFERENCES item(id) ON DELETE SET NULL,
    type VARCHAR(50) NOT NULL,
    text TEXT NOT NULL,
    tags TEXT[] NOT NULL DEFAULT '{}',
    category VARCHAR(100),
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    priority VARCHAR(50),
    energy_level VARCHAR(50),
    time_estimate INT,
    difficulty VARCHAR(50),
    deadline TIMESTAMP,
    completed_at TIMESTAMP,
    source VARCHAR(50) NOT NULL DEFAULT 'cli',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT item_type_ck CHECK (type IN ('task', 'note', 'idea', 'reminder', 'reference')),
    CONSTRAINT item_status_ck CHECK (status IN ('pending', 'in_progress', 'done', 'archived', 'blocked')),
    CONSTRAINT item_priority_ck CHECK (priority IS NULL OR priority IN ('high', 'medium', 'low')),
    CONSTRAINT item_energy_ck CHECK (energy_level IS NULL OR energy_level IN ('low', 'medium', 'high')),
    CONSTRAINT item_difficulty_ck CHECK (difficulty IS NULL OR difficulty IN ('easy', 'medium', 'hard'))
);

CREATE TABLE IF NOT EXISTS item_dependency (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_item_id UUID NOT NULL REFERENCES item(id) ON DELETE CASCADE,
    to_item_id UUID NOT NULL REFERENCES item(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL,
    reason TEXT,
    is_confirmed BOOLEAN NOT NULL DEFAULT FALSE,
    confirmed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT item_dependency_rel_ck CHECK (relationship_type IN ('blocks', 'blocked_by', 'relates_to', 'duplicate_of', 'subtask_of', 'parent_of')),
    CONSTRAINT item_dependency_not_self_ck CHECK (from_item_id <> to_item_id),
    CONSTRAINT item_dependency_unique UNIQUE(from_item_id, to_item_id, relationship_type)
);

CREATE TABLE IF NOT EXISTS item_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_id UUID NOT NULL REFERENCES item(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL,
    old_value JSONB,
    new_value JSONB,
    reason TEXT,
    performed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT item_audit_action_ck CHECK (action IN ('created', 'updated', 'merged', 'split', 'archived', 'status_changed'))
);

CREATE TABLE IF NOT EXISTS item_merge (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merged_into_id UUID NOT NULL REFERENCES item(id) ON DELETE CASCADE,
    merged_from_ids UUID[] NOT NULL,
    merged_from_content JSONB,
    merge_reason TEXT,
    performed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    can_undo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS attachment (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_id UUID NOT NULL REFERENCES item(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    mime_type VARCHAR(100),
    path VARCHAR(500),
    url VARCHAR(500),
    size INT,
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT attachment_type_ck CHECK (type IN ('image', 'document', 'link', 'file', 'note'))
);

CREATE TABLE IF NOT EXISTS reminder (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_id UUID NOT NULL REFERENCES item(id) ON DELETE CASCADE,
    scheduled_at TIMESTAMP NOT NULL,
    recurring VARCHAR(50) NOT NULL DEFAULT 'none',
    last_triggered_at TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    delivery_method VARCHAR(50) NOT NULL DEFAULT 'notification',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT reminder_recurring_ck CHECK (recurring IN ('none', 'daily', 'weekly', 'monthly', 'yearly')),
    CONSTRAINT reminder_delivery_ck CHECK (delivery_method IN ('notification', 'email', 'sms'))
);

CREATE TABLE IF NOT EXISTS user_profile (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timezone VARCHAR(50) NOT NULL DEFAULT 'UTC',
    preferred_focus_duration INT NOT NULL DEFAULT 25,
    preferred_break_duration INT NOT NULL DEFAULT 5,
    tags_aliases JSONB,
    preferences JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_session (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_profile_id UUID REFERENCES user_profile(id) ON DELETE SET NULL,
    session_date DATE NOT NULL,
    energy_level VARCHAR(50),
    mood TEXT,
    focus_capacity INT,
    external_blockers TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT user_session_energy_ck CHECK (energy_level IS NULL OR energy_level IN ('low', 'medium', 'high')),
    CONSTRAINT user_session_focus_ck CHECK (focus_capacity IS NULL OR (focus_capacity >= 0 AND focus_capacity <= 100)),
    CONSTRAINT user_session_unique UNIQUE(user_profile_id, session_date)
);

CREATE TABLE IF NOT EXISTS daily_plan (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_profile_id UUID REFERENCES user_profile(id) ON DELETE SET NULL,
    user_session_id UUID REFERENCES user_session(id) ON DELETE SET NULL,
    plan_date DATE NOT NULL,
    project_id UUID REFERENCES project(id) ON DELETE SET NULL,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT daily_plan_unique UNIQUE(user_profile_id, plan_date)
);

CREATE TABLE IF NOT EXISTS daily_plan_item (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    daily_plan_id UUID NOT NULL REFERENCES daily_plan(id) ON DELETE CASCADE,
    item_id UUID NOT NULL REFERENCES item(id) ON DELETE CASCADE,
    position INT NOT NULL,
    status_on_plan VARCHAR(50) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT daily_plan_item_unique UNIQUE(daily_plan_id, item_id),
    CONSTRAINT daily_plan_item_status_ck CHECK (status_on_plan IN ('pending', 'completed', 'skipped', 'moved_to_later'))
);

CREATE TABLE IF NOT EXISTS focus_session (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    daily_plan_item_id UUID REFERENCES daily_plan_item(id) ON DELETE SET NULL,
    item_id UUID NOT NULL REFERENCES item(id) ON DELETE CASCADE,
    user_session_id UUID REFERENCES user_session(id) ON DELETE SET NULL,
    planned_duration INT NOT NULL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    actual_duration INT,
    break_duration INT,
    distractions INT NOT NULL DEFAULT 0,
    interruptions TEXT,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS inbox_entry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_text TEXT NOT NULL,
    source VARCHAR(50) NOT NULL DEFAULT 'cli',
    suggested_type VARCHAR(50),
    suggested_tags TEXT[] NOT NULL DEFAULT '{}',
    suggested_project_id UUID REFERENCES project(id) ON DELETE SET NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'unprocessed',
    converted_to_item_id UUID REFERENCES item(id) ON DELETE SET NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT inbox_entry_status_ck CHECK (status IN ('unprocessed', 'processed', 'converted_to_item'))
);

CREATE INDEX IF NOT EXISTS idx_item_project_status ON item(project_id, status);
CREATE INDEX IF NOT EXISTS idx_item_deadline_not_null ON item(deadline) WHERE deadline IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_item_energy_not_null ON item(energy_level) WHERE energy_level IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_item_dependency_from ON item_dependency(from_item_id);
CREATE INDEX IF NOT EXISTS idx_item_dependency_to ON item_dependency(to_item_id);
CREATE INDEX IF NOT EXISTS idx_item_dependency_blocks ON item_dependency(to_item_id) WHERE relationship_type = 'blocks';
CREATE INDEX IF NOT EXISTS idx_item_audit_item ON item_audit(item_id);
CREATE INDEX IF NOT EXISTS idx_item_merge_into ON item_merge(merged_into_id);
CREATE INDEX IF NOT EXISTS idx_attachment_item ON attachment(item_id);
CREATE INDEX IF NOT EXISTS idx_reminder_item ON reminder(item_id);
CREATE INDEX IF NOT EXISTS idx_reminder_schedule ON reminder(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_user_session_profile_date ON user_session(user_profile_id, session_date);
CREATE INDEX IF NOT EXISTS idx_daily_plan_profile_date ON daily_plan(user_profile_id, plan_date);
CREATE INDEX IF NOT EXISTS idx_daily_plan_item_plan_position ON daily_plan_item(daily_plan_id, position);
CREATE INDEX IF NOT EXISTS idx_focus_session_item ON focus_session(item_id);
CREATE INDEX IF NOT EXISTS idx_inbox_entry_status ON inbox_entry(status);
CREATE INDEX IF NOT EXISTS idx_item_text_trgm ON item USING gin (text gin_trgm_ops);

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = CURRENT_TIMESTAMP;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION audit_item_update()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO item_audit (item_id, action, old_value, new_value, reason, performed_at)
  VALUES (
    NEW.id,
    'updated',
    jsonb_build_object('status', OLD.status, 'priority', OLD.priority, 'text', OLD.text),
    jsonb_build_object('status', NEW.status, 'priority', NEW.priority, 'text', NEW.text),
    'auto_audit_update_trigger',
    CURRENT_TIMESTAMP
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_item_set_updated_at ON item;
CREATE TRIGGER trg_item_set_updated_at
BEFORE UPDATE ON item
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_item_dependency_set_updated_at ON item_dependency;
CREATE TRIGGER trg_item_dependency_set_updated_at
BEFORE UPDATE ON item_dependency
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_reminder_set_updated_at ON reminder;
CREATE TRIGGER trg_reminder_set_updated_at
BEFORE UPDATE ON reminder
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_user_profile_set_updated_at ON user_profile;
CREATE TRIGGER trg_user_profile_set_updated_at
BEFORE UPDATE ON user_profile
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_user_session_set_updated_at ON user_session;
CREATE TRIGGER trg_user_session_set_updated_at
BEFORE UPDATE ON user_session
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_daily_plan_set_updated_at ON daily_plan;
CREATE TRIGGER trg_daily_plan_set_updated_at
BEFORE UPDATE ON daily_plan
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_focus_session_set_updated_at ON focus_session;
CREATE TRIGGER trg_focus_session_set_updated_at
BEFORE UPDATE ON focus_session
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_inbox_entry_set_updated_at ON inbox_entry;
CREATE TRIGGER trg_inbox_entry_set_updated_at
BEFORE UPDATE ON inbox_entry
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_item_audit_update ON item;
CREATE TRIGGER trg_item_audit_update
AFTER UPDATE ON item
FOR EACH ROW
WHEN (OLD IS DISTINCT FROM NEW)
EXECUTE FUNCTION audit_item_update();

COMMIT;
