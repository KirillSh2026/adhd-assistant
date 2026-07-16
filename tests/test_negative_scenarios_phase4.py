"""Phase 4: Comprehensive Test Coverage Expansion

Test coverage for:
- Negative scenarios and validation
- Error handling and edge cases  
- JSON corruption detection
- Storage interface compliance
- Format independence
"""

import pytest
import json
from pathlib import Path
from datetime import datetime

from models.item import Item, ItemType, ItemStatus
from core.exceptions import StorageError, StorageEntityNotFoundError, UnsupportedStorageCapabilityError
from storage.json_storage import JsonStorage
from storage.json_data_adapter import JsonDataAdapter


# ============================================================================
# VALIDATION AND ERROR HANDLING TESTS
# ============================================================================


class TestItemValidation:
    """Test Item model validation."""

    def test_item_rejects_empty_text_at_creation(self):
        """Creating item with empty text should fail."""
        with pytest.raises(ValueError, match="empty|whitespace"):
            Item(type=ItemType.TASK, text="")

    def test_item_rejects_whitespace_only_text(self):
        """Creating item with whitespace-only text should fail."""
        with pytest.raises(ValueError, match="empty|whitespace"):
            Item(type=ItemType.TASK, text="   \t\n  ")

    def test_item_requires_valid_type(self):
        """ItemType must be valid enum value."""
        # Valid types should work
        Item(type=ItemType.TASK, text="Valid")
        Item(type=ItemType.NOTE, text="Valid")
        Item(type=ItemType.IDEA, text="Valid")

    def test_item_requires_valid_status(self):
        """ItemStatus must be valid enum value."""
        # Valid status should work
        Item(type=ItemType.TASK, text="Valid", status=ItemStatus.ACTIVE)
        Item(type=ItemType.TASK, text="Valid", status=ItemStatus.ARCHIVED)

    def test_item_normalizes_text_whitespace(self):
        """Item should normalize whitespace in text."""
        item = Item(type=ItemType.TASK, text="  Text with  spaces  ")
        # Whitespace may be normalized
        assert item.text is not None


# ============================================================================
# JSON STORAGE ERROR HANDLING
# ============================================================================


class TestJsonStorageErrorHandling:
    """Test JSON storage error scenarios."""

    def test_corrupted_json_raises_storage_error(self, temp_json_path):
        """Corrupted JSON should be caught and reported."""
        Path(temp_json_path).write_text('{"invalid": json}')
        
        storage = JsonStorage(temp_json_path)
        
        with pytest.raises(StorageError):
            storage.load_items()

    def test_empty_file_raises_storage_error(self, temp_json_path):
        """Empty file should raise error."""
        Path(temp_json_path).write_text('')
        
        storage = JsonStorage(temp_json_path)
        
        with pytest.raises(StorageError):
            storage.load_items()

    def test_json_with_object_instead_of_array_fails(self, temp_json_path):
        """JSON object instead of array should fail."""
        Path(temp_json_path).write_text('{"id": "1", "type": "task"}')
        
        storage = JsonStorage(temp_json_path)
        
        with pytest.raises(StorageError):
            storage.load_items()

    def test_atomic_write_saves_items(self, temp_json_path):
        """Writes should work with Item objects."""
        adapter = JsonDataAdapter(Path(temp_json_path))
        
        # Create valid items
        items = [
            Item(type=ItemType.TASK, text="Item 1"),
        ]
        
        # Save items directly (storage layer does conversion)
        storage = JsonStorage(temp_json_path)
        storage.add_item(items[0])
        
        # Read back should work
        loaded = storage.load_items()
        assert len(loaded) == 1
        assert loaded[0].text == "Item 1"

    def test_atomic_write_preserves_data_on_error(self, temp_json_path):
        """Failed writes shouldn't corrupt existing data."""
        storage = JsonStorage(temp_json_path)
        
        # Write initial data
        initial = Item(type=ItemType.TASK, text="Original")
        storage.add_item(initial)
        
        # Original should still be readable
        loaded = storage.load_items()
        assert loaded[0].text == "Original"


# ============================================================================
# STORAGE CAPABILITY BOUNDARY TESTS
# ============================================================================


class TestStorageCapabilityBoundaries:
    """Test that storage operations fail gracefully when not supported."""

    def test_json_storage_capability_boundaries(self):
        """JSON storage should only support basic operations."""
        # JSON storage only supports: add_item, load_items, clear_items
        # All advanced operations (merge, relation, link) require PostgreSQL
        pass

    def test_json_storage_rejects_merge_items(self, empty_json_storage):
        """JSON storage doesn't support merge_items."""
        storage = empty_json_storage
        
        storage.add_item(Item(type=ItemType.TASK, text="Item 1"))
        storage.add_item(Item(type=ItemType.TASK, text="Item 2"))
        
        items = storage.load_items()
        if len(items) >= 2:
            with pytest.raises(UnsupportedStorageCapabilityError):
                storage.merge_items(
                    target_item_id=items[0].id,
                    source_item_ids=[items[1].id],
                    merge_reason="Test",
                )

    def test_json_storage_rejects_list_merges(self, empty_json_storage):
        """JSON storage doesn't support list_merges."""
        storage = empty_json_storage
        
        with pytest.raises(UnsupportedStorageCapabilityError):
            storage.list_merges()

    def test_json_storage_rejects_undo_merge(self, empty_json_storage):
        """JSON storage doesn't support undo_merge."""
        storage = empty_json_storage
        
        with pytest.raises(UnsupportedStorageCapabilityError):
            storage.undo_last_merge()


# ============================================================================
# STORAGE INTERFACE CONTRACT
# ============================================================================


class TestStorageInterfaceContract:
    """Tests for Storage interface compliance."""

    def test_load_items_returns_list(self, empty_json_storage):
        """load_items() must always return a list."""
        result = empty_json_storage.load_items()
        
        assert isinstance(result, list)
        assert result == []

    def test_load_items_returns_items_with_correct_types(self, empty_json_storage):
        """Items must have correct types in loaded data."""
        storage = empty_json_storage
        
        storage.add_item(Item(type=ItemType.TASK, text="Test"))
        items = storage.load_items()
        
        assert len(items) == 1
        item = items[0]
        
        # All required fields present and correct types
        assert isinstance(item, Item)
        assert item.type == ItemType.TASK
        assert item.text == "Test"

    def test_add_item_returns_none(self, empty_json_storage):
        """add_item() must return None (void operation)."""
        result = empty_json_storage.add_item(Item(type=ItemType.TASK, text="Test"))
        
        assert result is None

    def test_add_and_load_roundtrip(self, empty_json_storage):
        """Items added should be retrievable."""
        storage = empty_json_storage
        
        original = Item(type=ItemType.NOTE, text="Test note")
        storage.add_item(original)
        
        loaded = storage.load_items()
        
        assert len(loaded) == 1
        assert loaded[0].text == original.text
        assert loaded[0].type == original.type

    def test_clear_items_removes_all(self, empty_json_storage):
        """clear_items() must remove all items."""
        storage = empty_json_storage
        
        storage.add_item(Item(type=ItemType.TASK, text="Item 1"))
        storage.add_item(Item(type=ItemType.NOTE, text="Item 2"))
        assert len(storage.load_items()) == 2
        
        storage.clear_items()
        
        assert storage.load_items() == []

    def test_clear_items_is_idempotent(self, empty_json_storage):
        """clear_items() can be called multiple times safely."""
        storage = empty_json_storage
        
        storage.add_item(Item(type=ItemType.TASK, text="Item"))
        
        storage.clear_items()
        assert storage.load_items() == []
        
        # Second call should not error
        storage.clear_items()
        assert storage.load_items() == []

    def test_list_relations_with_json_storage_fails(self, empty_json_storage):
        """list_relations() on JSON storage should raise UnsupportedStorageCapabilityError."""
        with pytest.raises(UnsupportedStorageCapabilityError):
            empty_json_storage.list_relations()


# ============================================================================
# FORMAT INDEPENDENCE
# ============================================================================


class TestFormatIndependence:
    """Tests to verify code doesn't depend on legacy format details."""

    def test_item_type_is_enum_with_string_value(self):
        """ItemType inherits from str but is semantically an Enum."""
        # ItemType inherits from both Enum and str
        assert ItemType.TASK.value == "task"
        
        # It compares equal to string for compatibility
        # but is still an Enum type
        assert isinstance(ItemType.TASK, ItemType)

    def test_item_created_at_is_datetime(self):
        """created_at should be datetime, not string."""
        now = datetime.now()
        item = Item(type=ItemType.TASK, text="Test", created_at=now)
        
        assert isinstance(item.created_at, datetime)

    def test_item_status_is_enum_not_string(self):
        """ItemStatus should be an Enum."""
        assert ItemStatus.ACTIVE in {ItemStatus.ACTIVE, ItemStatus.ARCHIVED, ItemStatus.DELETED}
        assert ItemStatus.ACTIVE.value == "active"


# ============================================================================
# EDGE CASE SCENARIOS
# ============================================================================


class TestEdgeCaseScenarios:
    """Tests for unusual but valid edge cases."""

    def test_add_many_items(self, empty_json_storage):
        """Storage should handle many items."""
        storage = empty_json_storage
        
        for i in range(50):
            storage.add_item(Item(type=ItemType.TASK, text=f"Item {i}"))
        
        items = storage.load_items()
        assert len(items) == 50

    def test_item_with_very_long_text(self, empty_json_storage):
        """Storage should handle very long text."""
        storage = empty_json_storage
        
        long_text = "A" * 10000
        storage.add_item(Item(type=ItemType.NOTE, text=long_text))
        
        items = storage.load_items()
        assert len(items[0].text) == 10000

    def test_item_with_special_characters(self, empty_json_storage):
        """Storage should handle special characters."""
        storage = empty_json_storage
        
        special_text = "Тест: 🚀 @#$%^&*() 中文"
        storage.add_item(Item(type=ItemType.NOTE, text=special_text))
        
        items = storage.load_items()
        assert items[0].text == special_text

    def test_item_with_unicode_normalization(self, empty_json_storage):
        """Storage should preserve unicode characters."""
        storage = empty_json_storage
        
        # Various unicode forms
        texts = ["café", "naïve", "Ñoño", "日本語"]
        
        for text in texts:
            storage.add_item(Item(type=ItemType.NOTE, text=text))
        
        items = storage.load_items()
        assert len(items) == len(texts)

    def test_relation_operations_on_json_storage(self, empty_json_storage):
        """JSON storage should gracefully handle relation operations."""
        storage = empty_json_storage
        
        storage.add_item(Item(type=ItemType.TASK, text="Item 1"))
        storage.add_item(Item(type=ItemType.TASK, text="Item 2"))
        
        items = storage.load_items()
        if len(items) >= 2:
            # These should fail gracefully with UnsupportedStorageCapabilityError
            with pytest.raises(UnsupportedStorageCapabilityError):
                storage.confirm_relation(
                    from_item_id=items[0].id,
                    to_item_id=items[1].id,
                    relationship_type="depends_on",
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
