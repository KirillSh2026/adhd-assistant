from __future__ import annotations

from pathlib import Path

from core.exceptions import UnsupportedStorageCapabilityError
from models.item import Item
from storage.json_data_adapter import JsonDataAdapter


class JsonStorage:
    """Storage backend for JSON file format.
    
    ⚠️  LIMITATIONS:
    - Only supports basic item CRUD (add, list, clear)
    - Does NOT support relations, merges, or advanced queries
    - Single-file storage with atomic writes
    - Suitable for simple todo lists; use PostgreSQL for relations
    
    For relation/merge operations, use PostgreSQL backend.
    """

    def __init__(self, path: str | Path = "data/notes.json"):
        """Initialize JSON storage.
        
        Args:
            path: Path to JSON file (str or Path)
            
        Raises:
            StorageError: If path cannot be used
        """
        if isinstance(path, str):
            path = Path(path)
        elif not isinstance(path, Path):
            raise ValueError(f"path must be str or Path, got {type(path)}")
        
        self.adapter = JsonDataAdapter(path)
        self.adapter.ensure_file()

    def load_items(self) -> list[Item]:
        """Load all items from JSON file.
        
        Returns:
            List of Item objects
            
        Raises:
            StorageError: If JSON is corrupted
        """
        return self.adapter.load_items()

    def add_item(self, item: Item) -> None:
        """Add item to JSON storage.
        
        Args:
            item: Item to add
            
        Raises:
            StorageError: If write fails
        """
        items = self.adapter.load_items()
        items.append(item)
        self.adapter.save_items(items)

    def clear_items(self) -> None:
        """Clear all items from storage.
        
        Raises:
            StorageError: If write fails
        """
        self.adapter.save_items([])

    def load_items_for_relations(self, include_archived: bool = False) -> list[Item]:
        """Relations not supported in JSON backend.
        
        Raises:
            UnsupportedStorageCapabilityError: Always
        """
        raise UnsupportedStorageCapabilityError(
            "Relation queries require PostgreSQL backend.\n"
            "JSON backend only stores items, not relations.\n"
            "To use relations, set ADHD_STORAGE_BACKEND=postgres"
        )

    def save_relation_suggestions(self, suggestions: list[dict]) -> int:
        """Relations not supported in JSON backend.
        
        Raises:
            UnsupportedStorageCapabilityError: Always
        """
        raise UnsupportedStorageCapabilityError(
            "Relation suggestions require PostgreSQL backend.\n"
            "To use similarity analysis, set ADHD_STORAGE_BACKEND=postgres"
        )

    def upsert_relation(
        self,
        from_item_id: str,
        to_item_id: str,
        relationship_type: str,
        reason: str,
        is_confirmed: bool,
    ) -> None:
        """Relations not supported in JSON backend.
        
        Raises:
            UnsupportedStorageCapabilityError: Always
        """
        raise UnsupportedStorageCapabilityError(
            "Relation linking requires PostgreSQL backend.\n"
            "To link items, set ADHD_STORAGE_BACKEND=postgres"
        )

    def confirm_relation(self, from_item_id: str, to_item_id: str, relationship_type: str) -> None:
        """Relations not supported in JSON backend.
        
        Raises:
            UnsupportedStorageCapabilityError: Always
        """
        raise UnsupportedStorageCapabilityError(
            "Relation confirmation requires PostgreSQL backend.\n"
            "To confirm relations, set ADHD_STORAGE_BACKEND=postgres"
        )

    def reject_relation(self, from_item_id: str, to_item_id: str, relationship_type: str) -> None:
        """Relations not supported in JSON backend.
        
        Raises:
            UnsupportedStorageCapabilityError: Always
        """
        raise UnsupportedStorageCapabilityError(
            "Relation rejection requires PostgreSQL backend.\n"
            "To reject relations, set ADHD_STORAGE_BACKEND=postgres"
        )

    def list_relations(self, item_id: str | None = None) -> list[dict]:
        """Relations not supported in JSON backend.
        
        Raises:
            UnsupportedStorageCapabilityError: Always
        """
        raise UnsupportedStorageCapabilityError(
            "Relation queries require PostgreSQL backend.\n"
            "To list relations, set ADHD_STORAGE_BACKEND=postgres"
        )

    def merge_items(self, target_item_id: str, source_item_ids: list[str], merge_reason: str) -> None:
        """Merges not supported in JSON backend.
        
        Raises:
            UnsupportedStorageCapabilityError: Always
        """
        raise UnsupportedStorageCapabilityError(
            "Item merging requires PostgreSQL backend.\n"
            "To merge items, set ADHD_STORAGE_BACKEND=postgres"
        )

    def list_merges(self, limit: int = 20) -> list[dict]:
        """Merge history not supported in JSON backend.
        
        Raises:
            UnsupportedStorageCapabilityError: Always
        """
        raise UnsupportedStorageCapabilityError(
            "Merge history requires PostgreSQL backend.\n"
            "To view merges, set ADHD_STORAGE_BACKEND=postgres"
        )

    def undo_last_merge(self, merge_id: str | None = None) -> dict:
        """Merge undo not supported in JSON backend.
        
        Raises:
            UnsupportedStorageCapabilityError: Always
        """
        raise UnsupportedStorageCapabilityError(
            "Merge undo requires PostgreSQL backend.\n"
            "To undo merges, set ADHD_STORAGE_BACKEND=postgres"
        )
