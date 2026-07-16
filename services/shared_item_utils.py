"""Shared utilities for item service operations."""

from core.exceptions import CliInputError, StorageError
from interfaces.storage import Storage
from models.item import Item

CLI_RELATIONSHIP_TYPES = {
    "related": "relates_to",
    "relates_to": "relates_to",
    "depends_on": "blocked_by",
    "blocked_by": "blocked_by",
    "blocks": "blocks",
    "duplicate_of": "duplicate_of",
}

DISPLAY_RELATIONSHIP_TYPES = {
    "relates_to": "related",
    "blocked_by": "depends_on",
    "blocks": "blocks",
    "duplicate_of": "duplicate_of",
    "subtask_of": "subtask_of",
    "parent_of": "parent_of",
}


class SharedItemUtils:
    """Shared utility methods for item operations."""

    def __init__(self, storage: Storage):
        self.storage = storage

    def get_relation_items(self) -> list[Item]:
        """Load items for relation operations."""
        try:
            return self.storage.load_items_for_relations(include_archived=False)
        except StorageError:
            raise
        except Exception as exc:
            raise StorageError(f"Failed to load relation items: {exc}") from exc

    def build_item_index(self, items: list[Item]) -> dict[str, int]:
        """Build mapping from item ID to index."""
        return {item.id: index for index, item in enumerate(items, start=1) if item.id}

    def resolve_item_by_index(self, item_index: int | None, items: list[Item]) -> Item:
        """Resolve item by display index."""
        if item_index is None:
            raise CliInputError("Item index is required")
        if item_index < 1 or item_index > len(items):
            raise CliInputError(f"Item index out of range: {item_index}")
        return items[item_index - 1]

    def require_item_id(self, item: Item) -> str:
        """Ensure item has ID."""
        if not item.id:
            raise StorageError("Storage item id is missing")
        return item.id

    def to_storage_relationship_type(self, relation_type: str) -> str:
        """Normalize CLI relation type to storage type."""
        normalized = relation_type.strip().lower()
        if normalized not in CLI_RELATIONSHIP_TYPES:
            supported = ", ".join(sorted(CLI_RELATIONSHIP_TYPES))
            raise CliInputError(f"Unsupported relation type: {relation_type}. Supported: {supported}")
        return CLI_RELATIONSHIP_TYPES[normalized]

    def to_display_relationship_type(self, relation_type: str) -> str:
        """Convert storage relation type to display type."""
        return DISPLAY_RELATIONSHIP_TYPES.get(relation_type, relation_type)
