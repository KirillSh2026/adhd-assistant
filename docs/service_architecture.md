# Service Architecture Guide

## Overview

The ADHD Assistant service layer is organized around **use cases** rather than technical concerns. This provides clear separation of responsibilities and makes the codebase more testable and maintainable.

## Architecture Diagram

```
CLI Layer (app/main.py)
       ↓
   Parse arguments
       ↓
ItemServiceRegistry
│   ├─ .capture  → CaptureService
│   ├─ .list     → ListService
│   ├─ .relation → RelationService
│   └─ .merge    → MergeService
│
Each service uses:
└─ SharedItemUtils + Storage Interface
```

## Services

### 1. CaptureService
**Responsibility**: Item creation and auto-classification

```python
from services.capture_service import CaptureService
from datetime import datetime

capture = CaptureService(storage, classifier)

# Add item with explicit type
capture.add_item("task", "Buy milk", datetime.now())

# Add with auto-classification
classified_type = capture.add_captured_item("buy milk tomorrow", datetime.now())
# Returns: "task" (auto-detected)

# Clear all items
capture.clear_items()
```

**Methods**:
- `add_item(note_type: str, text: str, created_at: datetime) → None`
- `add_captured_item(text: str, created_at: datetime, note_type: str | None = None) → str`
- `clear_items() → None`

**Dependencies**:
- `Storage` interface
- `ItemTypeClassifier` (optional, created if not provided)

---

### 2. ListService
**Responsibility**: Item listing and filtering

```python
from services.list_service import ListService

lister = ListService(storage)

# List all items
all_items = lister.list_items("all")
# Returns: [(1, Item), (2, Item), ...]

# Filter by type
tasks = lister.list_items("task")
notes = lister.list_items("note")
ideas = lister.list_items("idea")
```

**Methods**:
- `list_items(list_type: str) → list[tuple[int, Item]]`
  - `list_type`: "all", "task", "note", "idea"
  - Returns: List of (1-based index, Item) tuples

**Dependencies**:
- `Storage` interface

---

### 3. RelationService
**Responsibility**: Relation operations, suggestions, and clustering

```python
from services.relation_service import RelationService

relations = RelationService(storage, relation_analyzer)

# Suggest relations automatically
suggestions = relations.suggest_relations()
# Saves suggestions to storage and returns formatted data

# Show similarity clusters
clusters = relations.show_clusters()

# List relations (all or for specific item)
all_relations = relations.list_relations()
item_relations = relations.list_relations(item_index=1)

# Manually link items
relations.link_items(
    from_index=1,
    to_index=2,
    relation_type="depends_on",
    reason="Task 2 must complete first"
)

# Confirm a suggested relation
relations.confirm_relation(
    from_index=1,
    to_index=2,
    relation_type="duplicate_of"
)

# Reject a suggested relation
relations.reject_relation(
    from_index=1,
    to_index=2,
    relation_type="related"
)
```

**Methods**:
- `suggest_relations() → list[dict]`
- `show_clusters() → list[dict]`
- `list_relations(item_index: int | None = None) → list[dict]`
- `link_items(from_index: int, to_index: int, relation_type: str, reason: str = "") → None`
- `confirm_relation(from_index: int, to_index: int, relation_type: str) → None`
- `reject_relation(from_index: int, to_index: int, relation_type: str) → None`

**Supported Relation Types**:
- `related` / `relates_to` → Display as "related"
- `depends_on` → Display as "depends_on" (stored as "blocked_by")
- `blocks` → Display as "blocks"
- `duplicate_of` → Display as "duplicate_of"

**Dependencies**:
- `Storage` interface
- `RelationAnalysisService` (optional, created if not provided)
- `SharedItemUtils`

---

### 4. MergeService
**Responsibility**: Item merging and merge history

```python
from services.merge_service import MergeService

merge = MergeService(storage)

# Merge source items into target
merge.merge_items(
    target_index=1,
    source_indices=[2, 3],
    merge_reason="Consolidated duplicate tasks"
)

# List merge history
history = merge.list_merges(limit=10)

# Undo most recent merge
result = merge.undo_merge()

# Undo specific merge
result = merge.undo_merge(merge_id="merge_abc123")
```

**Methods**:
- `merge_items(target_index: int, source_indices: list[int], merge_reason: str = "") → None`
- `list_merges(limit: int = 20) → list[dict]`
- `undo_merge(merge_id: str | None = None) → dict`

**Dependencies**:
- `Storage` interface
- `SharedItemUtils`

---

### 5. SharedItemUtils
**Responsibility**: Common utilities for item operations

```python
from services.shared_item_utils import SharedItemUtils

utils = SharedItemUtils(storage)

# Load items suitable for relation operations
items = utils.get_relation_items()

# Build mapping from item ID to display index
index_map = utils.build_item_index(items)
# Returns: {"item_id_1": 1, "item_id_2": 2, ...}

# Resolve item by display index
item = utils.resolve_item_by_index(1, items)

# Ensure item has database ID
item_id = utils.require_item_id(item)

# Normalize CLI relation type to storage type
storage_type = utils.to_storage_relationship_type("depends_on")
# Returns: "blocked_by"

# Convert storage type to display type
display_type = utils.to_display_relationship_type("blocked_by")
# Returns: "depends_on"
```

**Methods** (all public, rarely used directly):
- `get_relation_items() → list[Item]`
- `build_item_index(items: list[Item]) → dict[str, int]`
- `resolve_item_by_index(item_index: int | None, items: list[Item]) → Item`
- `require_item_id(item: Item) → str`
- `to_storage_relationship_type(relation_type: str) → str`
- `to_display_relationship_type(relation_type: str) → str`

---

### 6. ItemServiceRegistry (Facade)
**Responsibility**: Combine and coordinate all services

```python
from services.item_service_registry import ItemServiceRegistry

# Create registry with dependencies
registry = ItemServiceRegistry(storage, classifier, relation_analyzer)

# Access specialized services directly
registry.capture.add_item(...)
registry.list.list_items(...)
registry.relation.link_items(...)
registry.merge.merge_items(...)

# Or use delegated methods (backwards compatible)
registry.add_item(...)      # → registry.capture.add_item()
registry.list_items(...)    # → registry.list.list_items()
registry.link_items(...)    # → registry.relation.link_items()
registry.merge_items(...)   # → registry.merge.merge_items()
```

**Attributes**:
- `capture: CaptureService`
- `list: ListService`
- `relation: RelationService`
- `merge: MergeService`

**Delegated Methods** (for backwards compatibility):
- Item capture: `add_item()`, `add_captured_item()`, `clear_items()`
- Item listing: `list_items()`
- Relations: `suggest_relations()`, `show_clusters()`, `list_relations()`, `link_items()`, `confirm_relation()`, `reject_relation()`
- Merging: `merge_items()`, `list_merges()`, `undo_merge()`

---

## Usage Patterns

### Pattern 1: Direct Service Use (Recommended)
For specific use cases, use the specialized service directly:

```python
from services.capture_service import CaptureService
from datetime import datetime

capture = CaptureService(storage, classifier)
capture.add_item("task", "Buy milk", datetime.now())
```

**Benefits**:
- Clear intent: What operation are you performing?
- Easy to test: Mock only what you need
- Easier to refactor: Services are independent

### Pattern 2: Registry Access
For multiple operations, use the registry:

```python
from services.item_service_registry import ItemServiceRegistry

service = ItemServiceRegistry(storage)

# Add item
service.capture.add_item("task", "Buy milk", datetime.now())

# List items
items = service.list.list_items("task")

# Link items
service.relation.link_items(1, 2, "depends_on")

# Merge items
service.merge.merge_items(1, [2])
```

**Benefits**:
- Single entry point for all operations
- Consistent dependency injection
- Easy to extend with new services

### Pattern 3: Legacy Code (Still Works)
Existing code using `ItemService` continues to work:

```python
from services.item_service import ItemService

service = ItemService(storage)
service.add_item("task", "Buy milk", datetime.now())  # Delegates to capture
service.list_items("task")                            # Delegates to list
service.link_items(1, 2, "depends_on")               # Delegates to relation
service.merge_items(1, [2])                          # Delegates to merge
```

**Note**: `ItemService` now inherits from `ItemServiceRegistry`, so it delegates all methods to the appropriate specialized service.

---

## Testing

### Unit Testing Services
Test each service independently:

```python
from unittest.mock import MagicMock
from services.capture_service import CaptureService
from datetime import datetime

def test_capture_validates_type():
    storage = MagicMock()
    capture = CaptureService(storage)
    
    with pytest.raises(Exception):
        capture.add_item("invalid_type", "text", datetime.now())
```

### Integration Testing
Test multiple services together:

```python
from services.item_service_registry import ItemServiceRegistry

def test_full_workflow(storage):
    service = ItemServiceRegistry(storage)
    
    # Add items
    service.capture.add_item("task", "Item 1", datetime.now())
    service.capture.add_item("task", "Item 2", datetime.now())
    
    # Link them
    items = service.list.list_items("task")
    assert len(items) == 2
    
    service.relation.link_items(1, 2, "depends_on")
    
    # Verify relation
    relations = service.relation.list_relations()
    assert len(relations) > 0
```

---

## Migration Guide

### From Monolithic ItemService to Specialized Services

**Step 1: No changes needed**
- Existing code using `ItemService` continues to work
- All methods delegate to specialized services

**Step 2: Gradual adoption** (optional)
- New code can use specialized services directly
- Mix old and new patterns in same codebase

**Step 3: Full migration** (future)
- Replace all `ItemService` usage with `ItemServiceRegistry`
- Remove `ItemService` class entirely

### Example Migration

**Before**:
```python
from services.item_service import ItemService
from datetime import datetime

service = ItemService(storage)
service.add_item("task", "Buy milk", datetime.now())
service.list_items("task")
service.link_items(1, 2, "depends_on")
```

**After (Option A: Direct services)**:
```python
from services.capture_service import CaptureService
from services.list_service import ListService
from services.relation_service import RelationService
from datetime import datetime

capture = CaptureService(storage)
lister = ListService(storage)
relation = RelationService(storage)

capture.add_item("task", "Buy milk", datetime.now())
lister.list_items("task")
relation.link_items(1, 2, "depends_on")
```

**After (Option B: Registry)**:
```python
from services.item_service_registry import ItemServiceRegistry
from datetime import datetime

service = ItemServiceRegistry(storage)
service.capture.add_item("task", "Buy milk", datetime.now())
service.list.list_items("task")
service.relation.link_items(1, 2, "depends_on")
```

---

## Design Principles

### 1. Single Responsibility
Each service has one clear purpose:
- **CaptureService**: Create items
- **ListService**: List items
- **RelationService**: Manage relations
- **MergeService**: Merge items

### 2. Dependency Injection
Services receive dependencies as constructor parameters, not globals:
```python
capture = CaptureService(storage, classifier)  # ✅ Dependencies injected
```

### 3. Interface-Based Design
Services depend on `Storage` interface, not concrete implementations:
```python
def __init__(self, storage: Storage):  # ✅ Interface-based
    self.storage = storage
```

### 4. Shared Utilities
Common operations extracted to `SharedItemUtils`:
- Reduces duplication
- Easier to maintain
- Consistent behavior across services

### 5. Backwards Compatibility
Legacy code continues to work via `ItemService` inheritance:
- No breaking changes
- Gradual migration possible
- Both old and new patterns coexist

---

## File Structure

```
services/
├── shared_item_utils.py      # Shared utilities (65 lines)
├── capture_service.py        # Item creation (27 lines)
├── list_service.py           # Item listing (23 lines)
├── relation_service.py       # Relations & clustering (157 lines)
├── merge_service.py          # Merging & history (67 lines)
├── item_service_registry.py  # Facade/registry (81 lines)
├── item_service.py           # Legacy wrapper (35 lines, deprecated)
├── item_type_classifier.py   # Auto-classification (unchanged)
├── relation_analysis_service.py # Similarity analysis (unchanged)
└── speech_to_text_service.py # Speech recognition (unchanged)
```

---

## Next Steps

1. **CLI Handler Updates** (optional): Update CLI handlers to use specialized services directly
2. **Additional Services** (optional): Add SearchService, ExportService, etc. following the same pattern
3. **Dependency Injection** (optional): Use a DI framework for larger-scale deployments
4. **API Layer** (future): Services can be reused for REST API without changes

---

## See Also

- [README.md](../README.md) - Project overview
- [.github/copilot-instructions.md](../.github/copilot-instructions.md) - CLI commands
- [docs/database_schema.md](./database_schema.md) - Database design
- [docs/workflows.md](./workflows.md) - Interaction flows
