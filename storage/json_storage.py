from __future__ import annotations

import json
from pathlib import Path

from models.item import Item


class JsonStorage:
    def __init__(self, path: str = "data/notes.json"):
        self.path = Path(path)
        self._ensure_file()

    def supports_advanced_relations(self) -> bool:
        return False

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
