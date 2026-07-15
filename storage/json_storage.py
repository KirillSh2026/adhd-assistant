from __future__ import annotations

import json
from pathlib import Path

from core.exceptions import UnsupportedStorageCapabilityError
from models.item import Item


class JsonStorage:
    def __init__(self, path: str = "data/notes.json"):
        self.path = Path(path)
        self._ensure_file()

    def _ensure_file(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def load_items(self) -> list[Item]:
        with self.path.open("r", encoding="utf-8") as file:
            raw_items = json.load(file)
        return [Item.from_legacy_dict(raw_item) for raw_item in raw_items]

    def save_items(self, items: list[Item]) -> None:
        data = [item.to_legacy_dict() for item in items]
        with self.path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

    def add_item(self, item: Item) -> None:
        items = self.load_items()
        items.append(item)
        self.save_items(items)

    def clear_items(self) -> None:
        self.save_items([])

    def load_items_for_relations(self, include_archived: bool = False) -> list[Item]:
        raise UnsupportedStorageCapabilityError(
            "Relation analysis requires PostgreSQL backend. JSON backend does not store item_dependency/item_merge."
        )

    def save_relation_suggestions(self, suggestions: list[dict]) -> int:
        raise UnsupportedStorageCapabilityError(
            "Relation suggestions persistence requires PostgreSQL backend."
        )

    def upsert_relation(
        self,
        from_item_id: str,
        to_item_id: str,
        relationship_type: str,
        reason: str,
        is_confirmed: bool,
    ) -> None:
        raise UnsupportedStorageCapabilityError("Manual relation linking requires PostgreSQL backend.")

    def confirm_relation(self, from_item_id: str, to_item_id: str, relationship_type: str) -> None:
        raise UnsupportedStorageCapabilityError("Relation confirmation requires PostgreSQL backend.")

    def reject_relation(self, from_item_id: str, to_item_id: str, relationship_type: str) -> None:
        raise UnsupportedStorageCapabilityError("Relation rejection requires PostgreSQL backend.")

    def list_relations(self, item_id: str | None = None) -> list[dict]:
        raise UnsupportedStorageCapabilityError("Listing relations requires PostgreSQL backend.")

    def merge_items(self, target_item_id: str, source_item_ids: list[str], merge_reason: str) -> None:
        raise UnsupportedStorageCapabilityError("Item merge requires PostgreSQL backend.")

    def list_merges(self, limit: int = 20) -> list[dict]:
        raise UnsupportedStorageCapabilityError("Merge history requires PostgreSQL backend.")

    def undo_last_merge(self, merge_id: str | None = None) -> dict:
        raise UnsupportedStorageCapabilityError("Merge rollback requires PostgreSQL backend.")
