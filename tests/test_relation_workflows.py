from datetime import datetime

import pytest

from models.item import Item
from services.item_service import ItemService


class FakeAdvancedStorage:
    def __init__(self):
        self.items = [
            Item(id="1", type="task", text="Купить молоко и хлеб", datetime="2026-01-01 10:00:00"),
            Item(id="2", type="task", text="Купить молоко и хлеб вечером", datetime="2026-01-01 10:05:00"),
            Item(id="3", type="note", text="Сегодня было много отвлечений", datetime="2026-01-01 10:10:00"),
        ]
        self.saved_suggestions = []
        self.upsert_calls = []
        self.confirm_calls = []
        self.merge_calls = []

    def supports_advanced_relations(self) -> bool:
        return True

    def load_items(self):
        return self.items

    def load_items_for_relations(self, include_archived: bool = False):
        return self.items

    def save_relation_suggestions(self, suggestions: list[dict]) -> int:
        self.saved_suggestions = suggestions
        return len(suggestions)

    def upsert_relation(
        self,
        from_item_id: str,
        to_item_id: str,
        relationship_type: str,
        reason: str,
        is_confirmed: bool,
    ) -> None:
        self.upsert_calls.append((from_item_id, to_item_id, relationship_type, reason, is_confirmed))

    def confirm_relation(self, from_item_id: str, to_item_id: str, relationship_type: str) -> None:
        self.confirm_calls.append((from_item_id, to_item_id, relationship_type))

    def list_relations(self, item_id: str | None = None) -> list[dict]:
        return [
            {
                "from_item_id": "1",
                "to_item_id": "2",
                "relationship_type": "duplicate_of",
                "reason": "High textual similarity; score=0.88",
                "is_confirmed": False,
                "created_at": "2026-01-01 10:11:00",
                "from_text": self.items[0].text,
                "to_text": self.items[1].text,
            }
        ]

    def merge_items(self, target_item_id: str, source_item_ids: list[str], merge_reason: str) -> None:
        self.merge_calls.append((target_item_id, source_item_ids, merge_reason))


def test_suggest_relations_persists_suggestions():
    storage = FakeAdvancedStorage()
    service = ItemService(storage)

    suggestions = service.suggest_relations()

    assert suggestions
    assert storage.saved_suggestions
    assert suggestions[0]["relationship_type"] in {"duplicate_of", "related"}


def test_show_clusters_groups_related_items():
    storage = FakeAdvancedStorage()
    service = ItemService(storage)

    clusters = service.show_clusters()

    assert len(clusters) == 1
    assert [member["index"] for member in clusters[0]["members"]] == [1, 2]


def test_link_items_maps_depends_on_to_blocked_by():
    storage = FakeAdvancedStorage()
    service = ItemService(storage)

    service.link_items(1, 2, "depends_on", "Нужна база перед отчетом")

    assert storage.upsert_calls == [
        ("1", "2", "blocked_by", "Нужна база перед отчетом", True)
    ]


def test_confirm_relation_uses_resolved_indexes():
    storage = FakeAdvancedStorage()
    service = ItemService(storage)

    service.confirm_relation(1, 2, "duplicate_of")

    assert storage.confirm_calls == [("1", "2", "duplicate_of")]


def test_merge_items_passes_ids_and_reason():
    storage = FakeAdvancedStorage()
    service = ItemService(storage)

    service.merge_items(1, [2], "Объединяем дубликаты")

    assert storage.merge_calls == [("1", ["2"], "Объединяем дубликаты")]


def test_json_storage_rejects_advanced_relation_commands(tmp_path):
    from storage.json_storage import JsonStorage

    service = ItemService(JsonStorage(str(tmp_path / "notes.json")))

    with pytest.raises(RuntimeError):
        service.suggest_relations()

    with pytest.raises(RuntimeError):
        service.link_items(1, 2, "related")


def test_regular_add_item_still_works_with_classifier_changes(tmp_path):
    from storage.json_storage import JsonStorage

    service = ItemService(JsonStorage(str(tmp_path / "notes.json")))
    service.add_item("task", "Купить хлеб", datetime(2026, 1, 1, 12, 0, 0))

    items = service.list_items("all")
    assert items[0][1].type == "task"
