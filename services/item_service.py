from __future__ import annotations

from datetime import datetime

from models.item import Item


class ItemService:
    def __init__(self, storage):
        self.storage = storage

    def add_item(self, note_type: str, text: str, created_at: datetime) -> None:
        item = Item.from_input(note_type=note_type, text=text, created_at=created_at)
        self.storage.add_item(item)

    def clear_items(self) -> None:
        self.storage.clear_items()

    def list_items(self, list_type: str) -> list[tuple[int, Item]]:
        items = [item for item in self.storage.load_items() if item.has_text()]

        if list_type in {"task", "note", "idea"}:
            return [
                (index, item)
                for index, item in enumerate(items, start=1)
                if item.type.strip() == list_type
            ]

        if list_type in {"all", ""}:
            return list(enumerate(items, start=1))

        return []