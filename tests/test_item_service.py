from datetime import datetime

from services.item_service import ItemService
from storage.json_storage import JsonStorage


def test_add_and_list_with_legacy_format(tmp_path):
    path = tmp_path / "notes.json"
    storage = JsonStorage(str(path))
    service = ItemService(storage)

    service.add_item("task", "Купить хлеб", datetime(2026, 1, 1, 10, 0, 0))
    service.add_item("note", "Заметка", datetime(2026, 1, 2, 12, 0, 0))

    items = service.list_items("all")
    assert len(items) == 2
    assert items[0][0] == 1
    assert items[0][1].type == "task"
    assert items[0][1].datetime == "2026-01-01 10:00:00"


def test_filtering_keeps_order_index_over_filtered_items(tmp_path):
    path = tmp_path / "notes.json"
    storage = JsonStorage(str(path))
    service = ItemService(storage)

    service.add_item("task", "A", datetime(2026, 1, 1, 10, 0, 0))
    service.add_item("note", "B", datetime(2026, 1, 1, 10, 0, 1))
    service.add_item("task", "C", datetime(2026, 1, 1, 10, 0, 2))

    tasks = service.list_items("task")
    assert [(index, item.text) for index, item in tasks] == [(1, "A"), (3, "C")]


def test_add_captured_item_classifies_text(tmp_path):
    path = tmp_path / "notes.json"
    storage = JsonStorage(str(path))
    service = ItemService(storage)

    resolved_type = service.add_captured_item("Купить билеты на поезд", datetime(2026, 1, 1, 10, 0, 0))

    items = service.list_items("all")
    assert resolved_type == "task"
    assert items[0][1].type == "task"
