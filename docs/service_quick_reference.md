# Using Specialized Services: Quick Reference

## Quick Start

### 1. Capture Items
```python
from services.capture_service import CaptureService
from datetime import datetime

capture = CaptureService(storage, classifier)

# Add with explicit type
capture.add_item("task", "Buy milk", datetime.now())

# Add with auto-classification
item_type = capture.add_captured_item("buy milk tomorrow", datetime.now())
```

### 2. List Items
```python
from services.list_service import ListService

lister = ListService(storage)

# All items
items = lister.list_items("all")

# By type
tasks = lister.list_items("task")
```

### 3. Manage Relations
```python
from services.relation_service import RelationService

relations = RelationService(storage, analyzer)

# Suggestions
suggestions = relations.suggest_relations()

# Link items
relations.link_items(1, 2, "depends_on", "Task 2 first")

# Confirm suggestion
relations.confirm_relation(1, 2, "duplicate_of")
```

### 4. Merge Items
```python
from services.merge_service import MergeService

merge = MergeService(storage)

# Merge items
merge.merge_items(1, [2, 3], "Consolidated duplicates")

# View history
history = merge.list_merges()

# Undo merge
merge.undo_merge()
```

## Via Registry (Recommended)
```python
from services.item_service_registry import ItemServiceRegistry
from datetime import datetime

service = ItemServiceRegistry(storage, classifier, analyzer)

# Direct service access
service.capture.add_item("task", "Buy milk", datetime.now())
service.list.list_items("task")
service.relation.link_items(1, 2, "depends_on")
service.merge.merge_items(1, [2])

# Or use delegated methods (old style still works)
service.add_item("task", "Buy milk", datetime.now())
service.list_items("task")
```

## Testing

### Unit Test
```python
from unittest.mock import MagicMock
from services.capture_service import CaptureService

def test_capture():
    storage = MagicMock()
    capture = CaptureService(storage)
    capture.add_item("task", "Test", datetime.now())
    assert storage.add_item.called
```

### Integration Test
```python
def test_workflow(storage_with_items):
    service = ItemServiceRegistry(storage_with_items)
    
    # List
    items = service.list.list_items("task")
    assert len(items) > 0
    
    # Link
    service.relation.link_items(1, 2, "depends_on")
    
    # Verify
    rels = service.relation.list_relations(1)
    assert len(rels) > 0
```

## Migration

### Before (Monolithic)
```python
service = ItemService(storage)
service.add_item(...)
service.list_items(...)
service.link_items(...)
```

### After (Specialized)
```python
service = ItemServiceRegistry(storage)
service.capture.add_item(...)
service.list.list_items(...)
service.relation.link_items(...)
```

**Note**: Old code still works—`ItemService` now delegates to `ItemServiceRegistry`.

## Key Points

✅ **Each service has one clear responsibility**
✅ **Services receive dependencies as parameters**
✅ **All services work with `Storage` interface**
✅ **SharedItemUtils provides common operations**
✅ **Fully testable without mocking sys.argv**
✅ **Backwards compatible with existing code**

## See Also

- [docs/service_architecture.md](../docs/service_architecture.md) - Full reference
- [tests/test_use_case_services.py](../tests/test_use_case_services.py) - Example tests
