from datetime import datetime

from models.item import ItemType
from services.item_service_registry import ItemServiceRegistry
from storage.json_storage import JsonStorage


def test_add_and_list_with_legacy_format(tmp_path):
    path = tmp_path / "notes.json"
    storage = JsonStorage(str(path))
    service = ItemServiceRegistry(storage)

    service.add_item("task", "\u041a\u0443\u043f\u0438\u0442\u044c \u0445\u043b\u0435\u0431", datetime(2026, 1, 1, 10, 0, 0))
    service.add_item("note", "\u0417\u0430\u043c\u0435\u0442\u043a\u0430", datetime(2026, 1, 2, 12, 0, 0))

    items = service.list_items("all")
    assert len(items) == 2
    assert items[0][0] == 1
    assert items[0][1].type == ItemType.TASK
    assert items[0][1].created_at == datetime(2026, 1, 1, 10, 0, 0)


def test_filtering_keeps_order_index_over_filtered_items(tmp_path):
    path = tmp_path / "notes.json"
    storage = JsonStorage(str(path))
    service = ItemServiceRegistry(storage)

    service.add_item("task", "A", datetime(2026, 1, 1, 10, 0, 0))
    service.add_item("note", "B", datetime(2026, 1, 1, 10, 0, 1))
    service.add_item("task", "C", datetime(2026, 1, 1, 10, 0, 2))

    tasks = service.list_items("task")
    assert [(index, item.text) for index, item in tasks] == [(1, "A"), (3, "C")]


def test_add_captured_item_classifies_text(tmp_path):
    path = tmp_path / "notes.json"
    storage = JsonStorage(str(path))
    service = ItemServiceRegistry(storage)

    resolved_type = service.add_captured_item("\u041a\u0443\u043f\u0438\u0442\u044c \u0431\u0438\u043b\u0435\u0442\u044b \u043d\u0430 \u043f\u043e\u0435\u0437\u0434", datetime(2026, 1, 1, 10, 0, 0))

    items = service.list_items("all")
    assert resolved_type == "task"
    assert items[0][1].type == ItemType.TASK
