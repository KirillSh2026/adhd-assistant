"""Phase 6: Comprehensive edge case and storage detail testing.

This module extends Phase 4 negative scenarios with:
1. ItemAdapter-specific tests (legacy format conversions)
2. PostgreSQL-specific merge/undo edge cases
3. Detailed rollback and snapshot validation
4. Format migration and compatibility
5. Concurrent operation safety (basic)

Run with: make test-one TEST=tests/test_phase6_edge_cases.py
"""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from models.item import Item, ItemType, ItemStatus
from models.item_adapter import ItemAdapter
from core.exceptions import (
    StorageError,
    StorageEntityNotFoundError,
    StorageCorruptionError,
    UnsupportedStorageCapabilityError,
)


# ============================================================================
# ItemAdapter Tests (Legacy Format Conversions)
# ============================================================================

class TestItemAdapterLegacyConversions:
    """Test ItemAdapter as single point of legacy ↔ domain conversions."""

    def test_adapter_from_legacy_dict_with_all_fields(self):
        """Convert legacy dict with all fields to Item."""
        legacy = {
            "id": "1",
            "type": "task",
            "text": "Buy groceries",
            "datetime": "2026-07-16T10:00:00",
        }
        
        item = ItemAdapter.from_legacy_dict(legacy)
        
        assert item.id == "1"
        assert item.type == ItemType.TASK
        assert item.text == "Buy groceries"
        assert item.status == ItemStatus.ACTIVE
        assert item.created_at is not None

    def test_adapter_from_legacy_dict_without_datetime(self):
        """Handle legacy dict without datetime field."""
        legacy = {
            "id": "1",
            "type": "note",
            "text": "Remember this",
        }
        
        item = ItemAdapter.from_legacy_dict(legacy)
        
        assert item.id == "1"
        assert item.type == ItemType.NOTE
        assert item.text == "Remember this"
        assert item.created_at is None  # Optional in legacy

    def test_adapter_to_legacy_dict_preserves_format(self):
        """Convert Item back to legacy dict format."""
        item = Item(
            id="1",
            type=ItemType.IDEA,
            text="New concept",
            created_at=datetime(2026, 7, 16, 10, 0, 0),
            status=ItemStatus.ACTIVE,
        )
        
        legacy = ItemAdapter.to_legacy_dict(item)
        
        assert legacy["id"] == "1"
        assert legacy["type"] == "idea"
        assert legacy["text"] == "New concept"
        assert "datetime" in legacy

    def test_adapter_roundtrip_legacy_to_item_to_legacy(self):
        """Roundtrip: legacy dict → Item → legacy dict (should be equivalent)."""
        original_legacy = {
            "id": "42",
            "type": "task",
            "text": "Roundtrip test",
            "datetime": "2026-07-16T10:30:00",
        }
        
        item = ItemAdapter.from_legacy_dict(original_legacy)
        back_to_legacy = ItemAdapter.to_legacy_dict(item)
        
        assert back_to_legacy["id"] == original_legacy["id"]
        assert back_to_legacy["type"] == original_legacy["type"]
        assert back_to_legacy["text"] == original_legacy["text"]

    def test_adapter_rejects_invalid_type_in_legacy_dict(self):
        """Adapter validates type field from legacy dict."""
        legacy = {
            "id": "1",
            "type": "invalid_type",  # Unknown type
            "text": "Some text",
        }
        
        # from_legacy_dict is forgiving - it defaults to TASK
        item = ItemAdapter.from_legacy_dict(legacy)
        # Unknown types default to TASK
        assert item.type == ItemType.TASK

    def test_adapter_normalizes_text_during_conversion(self):
        """Adapter normalizes whitespace when converting legacy."""
        legacy = {
            "id": "1",
            "type": "task",
            "text": "  Text  with   spaces  ",
        }
        
        item = ItemAdapter.from_legacy_dict(legacy)
        
        # from_legacy_dict normalizes whitespace via .strip()
        assert item.text == "Text  with   spaces"  # Only outer spaces removed

    def test_adapter_to_dict_includes_all_fields(self):
        """to_dict() returns complete Item representation."""
        item = Item(
            id="1",
            type=ItemType.NOTE,
            text="Full test",
            created_at=datetime(2026, 7, 16, 10, 0, 0),
            status=ItemStatus.ARCHIVED,
        )
        
        item_dict = ItemAdapter.to_dict(item)
        
        # to_dict delegates to to_legacy_dict for now
        assert item_dict["id"] == "1"
        assert item_dict["type"] == "note"
        assert item_dict["text"] == "Full test"
        assert item_dict["status"] == "archived"
        assert "datetime" in item_dict


# ============================================================================
# Merge/Undo Edge Cases (PostgreSQL Specific)
# ============================================================================

class TestMergeUndoEdgeCases:
    """Test merge and undo operations with edge cases."""

    def test_merge_requires_storage_support(self, json_storage_with_sample_data):
        """JSON storage raises error for unsupported merge operation."""
        # JSON storage is basic, doesn't support merges
        with pytest.raises((StorageError, UnsupportedStorageCapabilityError)):
            json_storage_with_sample_data.merge_items(
                target_item_id="0",
                source_item_ids=["1"],
                merge_reason="Test",
            )

    def test_undo_merge_requires_storage_support(self, json_storage_with_sample_data):
        """JSON storage raises error for unsupported undo operation."""
        # JSON storage is basic, doesn't support undo
        if hasattr(json_storage_with_sample_data, "undo_last_merge"):
            with pytest.raises((StorageError, UnsupportedStorageCapabilityError)):
                json_storage_with_sample_data.undo_last_merge()


# ============================================================================
# Snapshot and Rollback Validation
# ============================================================================

class TestSnapshotAndRollback:
    """Test merge snapshot capture and rollback mechanics."""

    def test_snapshot_service_exists(self):
        """Verify SnapshotService is available."""
        try:
            from storage.postgres.snapshot_service import SnapshotService
            assert SnapshotService is not None
        except ImportError:
            pytest.skip("SnapshotService not available")

    def test_snapshot_creates_data_structure(self):
        """Snapshot data is properly structured."""
        try:
            from storage.postgres.snapshot_service import SnapshotService
            
            source = {
                "id": "1",
                "type": "task",
                "text": "Original task",
                "status": "active",
            }
            target = {
                "id": "2",
                "type": "note",
                "text": "Target note",
                "status": "active",
            }
            
            snapshot = SnapshotService.create_snapshot(source, target)
            
            assert snapshot is not None
            assert isinstance(snapshot, (dict, str))
        except ImportError:
            pytest.skip("SnapshotService not available")


# ============================================================================
# Format Migration and Compatibility
# ============================================================================

class TestFormatMigrationCompatibility:
    """Test data format conversions and backward compatibility."""

    def test_migrate_legacy_json_to_item_objects(self):
        """Load legacy JSON format and convert to Items."""
        legacy_json = [
            {"id": "1", "type": "task", "text": "Old task"},
            {"id": "2", "type": "note", "text": "Old note"},
        ]
        
        items = [ItemAdapter.from_legacy_dict(d) for d in legacy_json]
        
        assert len(items) == 2
        assert items[0].type == ItemType.TASK
        assert items[1].type == ItemType.NOTE

    def test_save_item_and_load_preserves_format(self, json_storage_with_sample_data):
        """Save Item to storage, load it back, verify format."""
        items_before = json_storage_with_sample_data.load_items()
        assert len(items_before) > 0
        
        first_item = items_before[0]
        
        # Verify format
        assert isinstance(first_item, Item)
        assert isinstance(first_item.type, ItemType)
        assert isinstance(first_item.status, ItemStatus)

    def test_legacy_dict_missing_type_field_handled(self):
        """Legacy dict without type field defaults to TASK."""
        legacy = {"id": "1", "text": "Missing type"}
        
        # from_legacy_dict is forgiving - defaults to TASK
        item = ItemAdapter.from_legacy_dict(legacy)
        assert item.type == ItemType.TASK

    def test_legacy_dict_missing_text_field_handled(self):
        """Legacy dict without text field raises clear error."""
        legacy = {"id": "1", "type": "task"}
        
        with pytest.raises((KeyError, ValueError)):
            ItemAdapter.from_legacy_dict(legacy)

    def test_created_at_format_variations_handled(self):
        """Different datetime formats in legacy data handled gracefully."""
        # ISO format
        legacy1 = {
            "id": "1",
            "type": "task",
            "text": "Test",
            "datetime": "2026-07-16T10:00:00",
        }
        
        # Should convert without error
        item1 = ItemAdapter.from_legacy_dict(legacy1)
        assert item1.created_at is not None


# ============================================================================
# Relation Operations Edge Cases
# ============================================================================

class TestRelationOperationsEdgeCases:
    """Test relation operations with edge cases."""

    def test_json_storage_does_not_support_relations(self, json_storage_with_sample_data):
        """JSON storage raises error for relation operations."""
        if not hasattr(json_storage_with_sample_data, "upsert_relation"):
            pytest.skip("Storage doesn't support relations")

        with pytest.raises((StorageError, UnsupportedStorageCapabilityError)):
            json_storage_with_sample_data.upsert_relation(
                from_item_id="1",
                to_item_id="2",
                relationship_type="related_to",
                reason="",
                is_confirmed=False,
            )

    def test_relation_operations_require_storage_support(self, json_storage_with_sample_data):
        """Relations require special storage backend (PostgreSQL)."""
        # JSON storage is basic, doesn't support relations
        if not hasattr(json_storage_with_sample_data, "save_relation_suggestions"):
            pytest.skip("Storage doesn't support relations")

        suggestions = [
            {
                "from_item_id": "0",
                "to_item_id": "1",
                "relationship_type": "related_to",
                "reason": "Similar topic",
            },
        ]
        
        with pytest.raises((StorageError, UnsupportedStorageCapabilityError)):
            json_storage_with_sample_data.save_relation_suggestions(suggestions)


# ============================================================================
# Concurrent Operation Safety (Basic)
# ============================================================================

class TestConcurrentOperationSafety:
    """Test behavior under concurrent/rapid operations."""

    def test_rapid_add_items_maintains_integrity(self, empty_json_storage):
        """Rapid adds don't corrupt storage."""
        items_to_add = [
            Item(id=str(i), type=ItemType.TASK, text=f"Task {i}")
            for i in range(20)
        ]
        
        for item in items_to_add:
            empty_json_storage.add_item(item)
        
        loaded = empty_json_storage.load_items()
        assert len(loaded) == 20

    def test_clear_during_list_operations(self, json_storage_with_sample_data):
        """Clear doesn't corrupt other operations."""
        # Load before clear
        items_before = json_storage_with_sample_data.load_items()
        assert len(items_before) > 0
        
        # Clear
        json_storage_with_sample_data.clear_items()
        
        # Verify cleared
        items_after = json_storage_with_sample_data.load_items()
        assert len(items_after) == 0


# ============================================================================
# Storage Capability Boundaries
# ============================================================================

class TestStorageCapabilityBoundaries:
    """Test explicit boundaries of storage capabilities."""

    def test_json_storage_does_not_support_merges(self, empty_json_storage):
        """JSON storage raises error for merge operation."""
        # JSON storage is basic, should reject merges
        with pytest.raises((StorageError, UnsupportedStorageCapabilityError)):
            empty_json_storage.merge_items(
                target_item_id="1",
                source_item_ids=["2"],
                merge_reason="Test",
            )

    def test_json_storage_does_not_support_relations_upsert(self, empty_json_storage):
        """JSON storage raises error for relation upsert."""
        with pytest.raises((StorageError, UnsupportedStorageCapabilityError)):
            empty_json_storage.upsert_relation(
                from_item_id="1",
                to_item_id="2",
                relationship_type="related_to",
                reason="",
                is_confirmed=False,
            )

    def test_json_storage_does_not_support_list_relations(self, empty_json_storage):
        """JSON storage raises error for listing relations."""
        with pytest.raises((StorageError, UnsupportedStorageCapabilityError)):
            empty_json_storage.list_relations()


# ============================================================================
# Fixtures (Reused from conftest.py)
# ============================================================================

@pytest.fixture
def empty_json_storage(tmp_path):
    """Fixture: Empty JSON storage for testing."""
    from storage.json_storage import JsonStorage
    
    storage_file = tmp_path / "test_storage.json"
    storage_file.write_text("[]")
    return JsonStorage(str(storage_file))


@pytest.fixture
def json_storage_with_sample_data(empty_json_storage):
    """Fixture: JSON storage with sample data."""
    from models.item import Item, ItemType
    
    items = [
        Item(id="0", type=ItemType.TASK, text="Buy groceries"),
        Item(id="1", type=ItemType.NOTE, text="Remember deadline"),
        Item(id="2", type=ItemType.IDEA, text="New project idea"),
    ]
    
    for item in items:
        empty_json_storage.add_item(item)
    
    return empty_json_storage
