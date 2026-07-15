from __future__ import annotations

from typing import Protocol

from models.item import Item


class Storage(Protocol):
    def load_items(self) -> list[Item]:
        ...

    def add_item(self, item: Item) -> None:
        ...

    def clear_items(self) -> None:
        ...

    def load_items_for_relations(self, include_archived: bool = False) -> list[Item]:
        ...

    def save_relation_suggestions(self, suggestions: list[dict]) -> int:
        ...

    def upsert_relation(
        self,
        from_item_id: str,
        to_item_id: str,
        relationship_type: str,
        reason: str,
        is_confirmed: bool,
    ) -> None:
        ...

    def confirm_relation(self, from_item_id: str, to_item_id: str, relationship_type: str) -> None:
        ...

    def reject_relation(self, from_item_id: str, to_item_id: str, relationship_type: str) -> None:
        ...

    def list_relations(self, item_id: str | None = None) -> list[dict]:
        ...

    def merge_items(self, target_item_id: str, source_item_ids: list[str], merge_reason: str) -> None:
        ...

    def list_merges(self, limit: int = 20) -> list[dict]:
        ...

    def undo_last_merge(self, merge_id: str | None = None) -> dict:
        ...
