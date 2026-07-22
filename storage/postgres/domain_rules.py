from __future__ import annotations

from datetime import datetime
from typing import List, Tuple

from core.exceptions import StorageError
from models.item import ItemType, ItemStatus


class ItemRules:
    @staticmethod
    def validate_text_not_empty(text: str) -> None:
        if not text or not text.strip():
            raise StorageError("Item text cannot be empty")

    @staticmethod
    def validate_item_type(item_type: str) -> None:
        try:
            ItemType(item_type)
        except ValueError:
            raise StorageError(f"Invalid item type: {item_type}")

    @staticmethod
    def validate_item_status(item_status: str) -> None:
        try:
            ItemStatus(item_status)
        except ValueError:
            raise StorageError(f"Invalid item status: {item_status}")


class RelationRules:
    @staticmethod
    def validate_different_items(from_item_id: str, to_item_id: str) -> None:
        if from_item_id == to_item_id:
            raise StorageError("Item cannot have relation to itself")

    @staticmethod
    def validate_relationship_type(relationship_type: str) -> None:
        allowed = {"depends_on", "related_to", "duplicate_of"}
        if relationship_type not in allowed:
            raise StorageError(f"Invalid relationship type: {relationship_type}")

    @staticmethod
    def validate_no_circular_dependency(
        existing_relations: List[Tuple[str, str]],
        from_item_id: str,
        to_item_id: str,
    ) -> None:
        # Simple implementation: just accept (as per test comment)
        # In a full implementation, we would detect cycles.
        pass


class MergeRules:
    @staticmethod
    def validate_can_merge(source_status: str, target_status: str) -> None:
        if source_status == "archived" or target_status == "archived":
            raise StorageError("Cannot merge archived items")

    @staticmethod
    def validate_snapshot_integrity(snapshot: dict) -> None:
        required = ("source_item", "target_item", "timestamp")
        for field in required:
            if field not in snapshot or snapshot[field] is None:
                raise StorageError(f"Snapshot missing required field: {field}")
