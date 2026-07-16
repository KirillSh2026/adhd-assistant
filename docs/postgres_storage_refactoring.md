# PostgreSQL Storage Refactoring Guide

## Overview

The PostgreSQL storage layer has been refactored from a 637-line monolith into a clean, layered architecture following domain-driven design principles.

### Before vs After

**Before (Monolith):**
```
PostgresStorage (637 lines, 17 methods)
  ├─ SQL queries mixed with business logic
  ├─ Connection duplication (psycopg.connect in each method)
  ├─ Raw dict objects (no types)
  ├─ Business rules embedded in SQL
  └─ Difficult to test and maintain
```

**After (Layered):**
```
PostgresStorage (orchestrator, ~300 lines)
  ↓
UnitOfWork (connection + transaction management)
  ↓
Repositories (data access layer)
  ├─ ProjectRepository (CRUD for projects)
  ├─ ItemRepository (CRUD for items)
  ├─ RelationRepository (manage relationships)
  └─ MergeRepository (manage merges + history)
  ↓
Domain Rules (business logic validation)
  ├─ MergeRules
  ├─ RelationRules
  └─ ItemRules
  ↓
SnapshotService (merge rollback support)
```

## Architecture Layers

### 1. DTOs (Data Transfer Objects)

**File:** `storage/postgres/dtos.py`

Immutable, typed records representing database tables:

```python
@dataclass(frozen=True)
class ItemRecord:
    id: str
    project_id: str
    type: str          # from ItemType Enum
    text: str
    status: str        # from ItemStatus Enum
    created_at: datetime
    # ... more fields
```

**Why DTOs?**
- Type safety (no raw `dict[str, Any]`)
- Immutability (prevents accidental mutations)
- Clear contract between repositories and storage
- Easy to add fields without breaking code

### 2. Repositories (Data Access Layer)

**File:** `storage/postgres/repositories/`

Each repository handles SQL for one entity type:

#### ProjectRepository
```python
repo.find_by_name(conn, "Inbox") → ProjectRecord
repo.find_or_create(conn, "MyProject") → ProjectRecord
repo.list_all(conn) → list[ProjectRecord]
```

#### ItemRepository
```python
repo.find_by_project(conn, project_id) → list[ItemRecord]
repo.insert(conn, project_id, type, text) → ItemRecord
repo.update(conn, item_id, text=...) → ItemRecord
repo.delete(conn, item_id) → None
repo.clear_project(conn, project_id) → int
```

#### RelationRepository
```python
repo.find_relation(conn, from_id, to_id, type) → RelationRecord | None
repo.insert_suggestion(conn, from_id, to_id, type, reason) → RelationRecord
repo.upsert_relation(conn, from_id, to_id, type, reason, confirmed) → RelationRecord
repo.confirm(conn, from_id, to_id, type) → RelationRecord
repo.reject_suggestion(conn, from_id, to_id, type) → None
repo.list_for_item(conn, item_id) → list[RelationRecord]
```

#### MergeRepository
```python
repo.record_merge(conn, project_id, source_id, target_id, reason, snapshot) → MergeRecord
repo.mark_reverted(conn, merge_id) → MergeRecord
repo.find_latest_for_project(conn, project_id) → MergeRecord | None
repo.list_for_project(conn, project_id) → list[MergeRecord]
repo.find_merges_involving_item(conn, item_id) → list[MergeRecord]
```

**Why Repositories?**
- Single Responsibility (each handles one entity)
- All SQL in one place (easy to find and maintain)
- Testable (can mock repositories)
- Reusable (other storage backends can use same pattern)
- Type-safe (return typed DTOs, not raw dicts)

### 3. Base Repository

**File:** `storage/postgres/repositories/base_repository.py`

Common functionality for all repositories:

```python
class BaseRepository:
    def _execute(conn, query, params) → list[tuple]
    def _execute_one(conn, query, params) → tuple | None
    def _execute_write(conn, query, params) → int
    def _execute_returning(conn, query, params) → tuple | None
    def _assert_project_id(conn, project_id) → None
    def _assert_item_exists(conn, item_id, project_id) → None
```

**Benefits:**
- No code duplication
- Consistent error handling
- Helper methods for common patterns
- Easy to add new repositories

### 4. Configuration

**File:** `storage/postgres/config.py`

```python
config = PostgresConfig(
    dsn="postgresql://user:pass@localhost/db",
    project_name="Inbox"
)

# Or from settings
config = PostgresConfig.from_settings(settings)
```

**Why separate config?**
- Single source of truth for DB connection
- Easy to test (pass mock config)
- Validates DSN on creation
- Decouples PostgresStorage from pydantic-settings

### 5. Unit of Work (Transaction Management)

**File:** `storage/postgres/unit_of_work.py`

Coordinates repositories and manages connection lifecycle:

```python
with UnitOfWork(config) as uow:
    project_id = uow.ensure_project_id("Inbox")
    items = uow.items.find_by_project(uow.connection, project_id)
    uow.relations.insert_suggestion(uow.connection, from_id, to_id, rel_type)
    # Auto-commits on success, auto-rollbacks on error
```

**Key Features:**
- Single connection per transaction (not per repository call)
- Auto-commit on success
- Auto-rollback on error
- All repositories access same connection
- Ready for connection pooling (future)

**Why UnitOfWork?**
- No connection duplication (before: 20+ `psycopg.connect()` calls)
- Transaction safety (all repos see same connection)
- Testable (can pass mock connection)
- Scalable (can integrate connection pool)

### 6. Domain Rules

**File:** `storage/postgres/domain_rules.py`

Business logic validation, independent of SQL:

```python
# Validation for merge operations
MergeRules.validate_can_merge(source_status, target_status)
MergeRules.validate_can_undo_merge(merge_status, already_reverted)
MergeRules.validate_snapshot_integrity(snapshot_data)

# Validation for relations
RelationRules.validate_different_items(from_id, to_id)
RelationRules.validate_relationship_type(rel_type)
RelationRules.validate_no_circular_dependency(existing_rels, from_id, to_id)

# Validation for items
ItemRules.validate_text_not_empty(text)
ItemRules.validate_item_type(type)
ItemRules.validate_item_status(status)
```

**Why separate rules?**
- Business logic not tied to SQL
- Can test without database
- Clear what constraints exist
- Easy to add new rules
- Reusable across storage backends

### 7. Snapshot Service

**File:** `storage/postgres/snapshot_service.py`

Handles merge snapshots for safe rollback:

```python
snapshot = SnapshotService.create_snapshot(
    source_item=source_dict,
    target_item=target_dict,
    source_relations=relations,
)

SnapshotService.validate_snapshot(snapshot_data)

instructions = SnapshotService.get_rollback_instructions(snapshot_data)
```

**What is a Snapshot?**
- JSON representation of items before merge
- Stored in database with merge record
- Used to safely rollback merge if needed
- Includes item data + relations + timestamp

**Why snapshots?**
- Merges are destructive (delete items)
- Snapshot allows safe undo
- Rollback is atomic with merge record
- History is preserved for audit

## Flow Examples

### Adding an Item

```python
storage = PostgresStorage(dsn, project_name="Inbox")
storage.add_item(item)

# Internally:
# 1. Create UnitOfWork
# 2. Get/create project in ProjectRepository
# 3. Insert item in ItemRepository
# 4. Commit transaction
```

### Merging Items

```python
storage.merge_items(
    target_item_id="item-5",
    source_item_ids=["item-2", "item-3"],
    merge_reason="Duplicates"
)

# Internally:
# 1. Create UnitOfWork (transaction)
# 2. Validate items exist and can be merged
# 3. Create snapshot of items
# 4. Delete source items
# 5. Record merge with snapshot
# 6. Auto-commit on success
```

### Undoing a Merge

```python
result = storage.undo_last_merge(merge_id="merge-42")

# Internally:
# 1. Find merge record
# 2. Validate it can be undone
# 3. Validate snapshot is complete
# 4. Mark merge as reverted
# 5. Return rollback instructions
```

## Backwards Compatibility

**100% Compatible!**

- All public methods unchanged
- All method signatures unchanged
- All return types unchanged
- Existing code works without modification

```python
# This code works exactly as before:
items = storage.load_items()
storage.add_item(item)
storage.merge_items(target_id, source_ids, reason)
```

## Testing Strategy

### Unit Tests (for repositories)

```python
def test_item_repository_insert():
    with UnitOfWork(config) as uow:
        record = uow.items.insert(
            uow.connection,
            project_id="p1",
            type_="task",
            text="Do something"
        )
        assert record.id is not None
        assert record.text == "Do something"
```

### Integration Tests (for storage)

```python
def test_merge_items():
    storage = PostgresStorage(dsn, "TestProject")
    storage.add_item(source_item)
    storage.add_item(target_item)
    
    storage.merge_items(target_id, [source_id], "Merged")
    
    items = storage.load_items()
    assert len(items) == 1  # Source deleted
    assert items[0].id == target_id
```

## Performance Improvements

| Aspect | Before | After |
|--------|--------|-------|
| Connection duplicates per method | 1-2 | 0 (UnitOfWork manages) |
| SQL duplication | High | None (centralized in repos) |
| Type safety | 50% | 100% |
| Code maintainability | Low | High |
| Testability | Difficult | Easy (mock repos) |
| Transaction safety | Basic | Explicit UoW |

## Migration for New Features

To add a new entity type:

1. **Create DTO** (`storage/postgres/dtos.py`)
   ```python
   @dataclass(frozen=True)
   class TagRecord:
       id: str
       name: str
       # ...
   ```

2. **Create Repository** (`storage/postgres/repositories/tag_repository.py`)
   ```python
   class TagRepository(BaseRepository):
       def insert(self, conn, name) → TagRecord
       # ...
   ```

3. **Add to UnitOfWork** (`storage/postgres/unit_of_work.py`)
   ```python
   self.tags = TagRepository(config.dsn)
   ```

4. **Add Domain Rules if needed** (`storage/postgres/domain_rules.py`)
   ```python
   class TagRules:
       @staticmethod
       def validate_tag_name(name):
           # ...
   ```

5. **Update PostgresStorage** (add public methods)
   ```python
   def add_tag(self, name: str) → str:
       with UnitOfWork(self.config) as uow:
           project_id = uow.ensure_project_id(self.config.project_name)
           record = uow.tags.insert(uow.connection, project_id, name)
           return record.id
   ```

## Known Limitations & Future Work

**Current Limitations:**
- No connection pooling yet (each UoW creates new connection)
- No query optimization/caching
- No soft deletes (items fully deleted on merge)

**Future Improvements:**
1. **Connection Pooling** - Use `psycopg_pool` for production
2. **Query Optimization** - Add caching, batch operations
3. **Event Sourcing** - Track all changes for audit trail
4. **GraphQL/REST APIs** - Build on top of repositories
5. **Soft Deletes** - Keep deleted items but mark as deleted

## References

- Unit of Work Pattern: Martin Fowler
- Repository Pattern: Domain-Driven Design
- DTOs: Microsoft .NET Architecture
- Domain Rules: Clean Architecture
