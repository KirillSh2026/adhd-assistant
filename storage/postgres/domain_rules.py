"""Domain rules and business logic validation.

These are pure business rules extracted from storage layer.
They are independent of SQL and can be tested without database.

Key principle: Domain rules should NOT know about SQL, repositories, or DTOs.
They only know about domain concepts and constraints.
"""

from datetime import datetime

from core.exceptions import StorageError


class MergeRules:
    """Business rules for item merging operations."""

    @staticmethod
    def validate_can_merge(
        source_status: str,
        target_status: str,
    ) -> None:
        """Validate that items can be merged.

        Business rule: Archived items cannot be merged.

        Args:
            source_status: Status of item being merged from
            target_status: Status of item being merged into

        Raises:
            StorageError: If merge is not allowed
        """
        if source_status == "archived":
            raise StorageError(
                "Cannot merge archived item (source). Restore it first."
            )

        if target_status == "archived":
            raise StorageError(
                "Cannot merge into archived item (target). Restore it first."
            )

    @staticmethod
    def validate_can_undo_merge(
        merge_status: str,
        merge_already_reverted: bool,
    ) -> None:
        """Validate that a merge can be undone.

        Business rule: Only completed merges can be undone (not already reverted).

        Args:
            merge_status: Status of merge record
            merge_already_reverted: Whether merge has already been reverted

        Raises:
            StorageError: If undo is not allowed
        """
        if merge_status != "completed":
            raise StorageError(f"Cannot undo merge with status {merge_status!r}")

        if merge_already_reverted:
            raise StorageError("Merge has already been reverted")

    @staticmethod
    def validate_snapshot_integrity(snapshot_data: dict | None) -> None:
        """Validate that snapshot contains required fields for rollback.

        Business rule: Merge snapshot must contain necessary data for rollback.

        Args:
            snapshot_data: Snapshot dictionary

        Raises:
            StorageError: If snapshot is incomplete or invalid
        """
        if not snapshot_data:
            raise StorageError("Merge snapshot is missing (cannot rollback)")

        required_fields = ["source_item", "target_item", "timestamp"]
        missing = [f for f in required_fields if f not in snapshot_data]

        if missing:
            raise StorageError(
                f"Merge snapshot incomplete (missing: {missing}). Cannot rollback safely."
            )


class RelationRules:
    """Business rules for item relationship operations."""

    @staticmethod
    def validate_different_items(
        from_item_id: str,
        to_item_id: str,
    ) -> None:
        """Validate that relation connects different items.

        Business rule: An item cannot have a relation to itself.

        Args:
            from_item_id: Source item ID
            to_item_id: Target item ID

        Raises:
            StorageError: If items are the same
        """
        if from_item_id == to_item_id:
            raise StorageError("Cannot create relation from item to itself")

    @staticmethod
    def validate_relationship_type(relationship_type: str) -> None:
        """Validate that relationship type is allowed.

        Business rule: Only specific relationship types are allowed.

        Args:
            relationship_type: Type of relationship

        Raises:
            StorageError: If type is invalid
        """
        valid_types = {"related_to", "depends_on", "duplicate_of", "related"}
        if relationship_type not in valid_types:
            raise StorageError(
                f"Invalid relationship type {relationship_type!r}. "
                f"Allowed: {valid_types}"
            )

    @staticmethod
    def validate_no_circular_dependency(
        existing_relations: list[tuple[str, str]],
        from_item_id: str,
        to_item_id: str,
    ) -> None:
        """Validate that new relation doesn't create circular dependency.

        Business rule: Dependencies should form a DAG (no cycles).

        Args:
            existing_relations: List of (from_id, to_id) tuples of existing dependencies
            from_item_id: Source item ID for new relation
            to_item_id: Target item ID for new relation

        Raises:
            StorageError: If cycle would be created
        """
        # Simple check: if there's already a path from to_item to from_item,
        # adding from_item → to_item would create a cycle
        # (full cycle detection requires graph traversal)

        for from_id, to_id in existing_relations:
            if from_id == to_item_id and to_id == from_item_id:
                raise StorageError(
                    f"Cannot create relation: would create circular dependency "
                    f"({from_item_id} → {to_item_id} → {from_item_id})"
                )


class ItemRules:
    """Business rules for item operations."""

    @staticmethod
    def validate_text_not_empty(text: str) -> None:
        """Validate that item text is not empty.

        Business rule: Item text must be provided and non-empty.

        Args:
            text: Item text

        Raises:
            StorageError: If text is empty
        """
        if not text or not text.strip():
            raise StorageError("Item text cannot be empty")

    @staticmethod
    def validate_item_type(item_type: str) -> None:
        """Validate that item type is allowed.

        Business rule: Only specific item types are allowed.

        Args:
            item_type: Item type (task, note, idea)

        Raises:
            StorageError: If type is invalid
        """
        valid_types = {"task", "note", "idea"}
        if item_type not in valid_types:
            raise StorageError(
                f"Invalid item type {item_type!r}. Allowed: {valid_types}"
            )

    @staticmethod
    def validate_item_status(status: str) -> None:
        """Validate that item status is allowed.

        Business rule: Only specific statuses are allowed.

        Args:
            status: Item status

        Raises:
            StorageError: If status is invalid
        """
        valid_statuses = {"active", "archived", "deleted"}
        if status not in valid_statuses:
            raise StorageError(
                f"Invalid item status {status!r}. Allowed: {valid_statuses}"
            )
