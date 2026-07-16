"""List service: item listing and filtering."""

from interfaces.storage import Storage
from models.item import Item


class ListService:
    """Handles listing and filtering items."""

    def __init__(self, storage: Storage):
        self.storage = storage

    def list_items(self, list_type: str) -> list[tuple[int, Item]]:
        """List items, optionally filtered by type."""
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
