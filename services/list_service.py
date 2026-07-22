"""List service: item listing and filtering."""

from interfaces.storage import Storage
from models.item import Item


class ListService:
    """Handles listing and filtering items."""

    def __init__(self, storage: Storage):
        self.storage = storage

    def list_items(self, list_type: str) -> list[tuple[int, Item]]:
        """List items, optionally filtered by type.

        Note: Items are already validated to have non-empty text in __post_init__,
        so no need to filter by has_text().
        """
        items = self.storage.load_items()

        if list_type in {"task", "note", "idea"}:
            return [
                (index, item)
                for index, item in enumerate(items, start=1)
                if item.type.value == list_type
            ]

        if list_type in {"all", ""}:
            return list(enumerate(items, start=1))

        return []