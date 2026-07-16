"""Tests for specialized use-case services."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from models.item import Item, ItemType
from services.capture_service import CaptureService
from services.item_type_classifier import ItemTypeClassifier
from services.list_service import ListService
from services.merge_service import MergeService
from services.relation_service import RelationService


class TestCaptureService:
    def test_add_item_validates_type(self):
        storage = MagicMock()
        service = CaptureService(storage)
        with pytest.raises(Exception) as exc:
            service.add_item("invalid_type", "text", datetime.now())
        assert "Unsupported item type" in str(exc.value)

    def test_add_captured_item_auto_classifies(self):
        storage = MagicMock()
        classifier = MagicMock(spec=ItemTypeClassifier)
        classifier.classify.return_value = "task"
        service = CaptureService(storage, classifier)

        result = service.add_captured_item("buy milk tomorrow", datetime.now())

        assert result == "task"
        classifier.classify.assert_called_once()

    def test_clear_items_delegates_to_storage(self):
        storage = MagicMock()
        service = CaptureService(storage)
        service.clear_items()
        storage.clear_items.assert_called_once()


class TestListService:
    def test_list_items_all(self):
        storage = MagicMock()
        item1 = Item(type=ItemType.TASK, text="Item 1", created_at=datetime.now())
        item2 = Item(type=ItemType.NOTE, text="Item 2", created_at=datetime.now())
        storage.load_items.return_value = [item1, item2]

        service = ListService(storage)
        result = service.list_items("all")

        assert len(result) == 2
        assert result[0] == (1, item1)
        assert result[1] == (2, item2)

    def test_list_items_filtered_by_type(self):
        storage = MagicMock()
        item1 = Item(type=ItemType.TASK, text="Item 1", created_at=datetime.now())
        item2 = Item(type=ItemType.NOTE, text="Item 2", created_at=datetime.now())
        storage.load_items.return_value = [item1, item2]

        service = ListService(storage)
        result = service.list_items("task")

        assert len(result) == 1
        assert result[0] == (1, item1)


class TestRelationService:
    def test_link_items_normalizes_relation_type(self):
        storage = MagicMock()
        item1 = Item(type=ItemType.TASK, text="Item 1", created_at=datetime.now(), id="1")
        item2 = Item(type=ItemType.TASK, text="Item 2", created_at=datetime.now(), id="2")
        storage.load_items_for_relations.return_value = [item1, item2]

        service = RelationService(storage)
        service.link_items(1, 2, "depends_on")

        storage.upsert_relation.assert_called_once()
        call_kwargs = storage.upsert_relation.call_args[1]
        assert call_kwargs["relationship_type"] == "blocked_by"


class TestMergeService:
    def test_merge_items_validates_sources(self):
        from core.exceptions import CliInputError

        storage = MagicMock()
        service = MergeService(storage)

        with pytest.raises(CliInputError) as exc:
            service.merge_items(1, [])
        assert "At least one source" in str(exc.value)

    def test_merge_items_rejects_duplicate_sources(self):
        from core.exceptions import CliInputError

        storage = MagicMock()
        service = MergeService(storage)

        with pytest.raises(CliInputError) as exc:
            service.merge_items(1, [2, 2])
        assert "unique" in str(exc.value)


class TestItemServiceRegistry:
    def test_registry_delegates_to_capture_service(self):
        from services.item_service_registry import ItemServiceRegistry

        storage = MagicMock()
        classifier = MagicMock(spec=ItemTypeClassifier)
        classifier.classify.return_value = "task"
        registry = ItemServiceRegistry(storage, classifier)

        result = registry.add_captured_item("text", datetime.now())

        assert result == "task"
        classifier.classify.assert_called_once()

    def test_registry_delegates_to_list_service(self):
        from services.item_service_registry import ItemServiceRegistry

        storage = MagicMock()
        item1 = Item(type=ItemType.TASK, text="Item 1", created_at=datetime.now())
        storage.load_items.return_value = [item1]

        registry = ItemServiceRegistry(storage)
        result = registry.list_items("all")

        assert len(result) == 1

    def test_legacy_item_service_still_works(self):
        from services.item_service import ItemService

        storage = MagicMock()
        item1 = Item(type=ItemType.TASK, text="Item 1", created_at=datetime.now())
        storage.load_items.return_value = [item1]

        service = ItemService(storage)
        result = service.list_items("all")

        assert len(result) == 1
