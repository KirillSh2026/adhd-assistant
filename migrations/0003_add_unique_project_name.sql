BEGIN;

-- Add unique constraint on project.name
ALTER TABLE project ADD CONSTRAINT project_name_unique UNIQUE (name);

COMMIT;
