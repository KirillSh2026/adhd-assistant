"""PostgreSQL storage implementation using repository pattern.

This is a refactored version of the monolithic PostgresStorage class.
It now uses:
- UnitOfWork for transaction management
- 4 repositories for data access
- Domain rules for business logic
- SnapshotService for merge safety

The public interface remains 100% compatible with the original version.
All existing code continues to work without changes.

Architecture:
    PostgresStorage (orchestrator)
      ↓
    UnitOfWork (connection + transaction management)
      ↓
    Repositories (data access)
      ├─ ProjectRepository
      ├─ ItemRepository
      ├─ RelationRepository
      └─ MergeRepository
      ↓
    Domain Rules + SnapshotService (business logic)
"""

from __future__ import annotations

from datetime import datetime

from core.exceptions import StorageEntityNotFoundError, StorageError
from models.item import Item, ItemStatus, ItemType
from models.item_adapter import ItemAdapter
from storage.postgres.config import PostgresConfig
from storage.postgres.unit_of_work import UnitOfWork
from storage.postgres.domain_rules import MergeRules, RelationRules, ItemRules
from storage.postgres.snapshot_service import SnapshotService


class PostgresStorage:
    """PostgreSQL storage backend with repository pattern.

    Implements Storage interface while delegating to repositories.
    All connection management is handled by UnitOfWork.
    """

    def __init__(self, dsn: str, project_name: str = "Inbox"):
        """Initialize PostgreSQL storage.

        Args:
            dsn: PostgreSQL connection string
            project_name: Project name for isolation (default: "Inbox")
        """
        self.config = PostgresConfig(dsn=dsn, project_name=project_name)

    # ========================================================================
    # ITEM OPERATIONS
    # ========================================================================

    def load_items(self) -> list[Item]:
        """Load all active items from storage.

        Returns:
            List of Item objects

        Raises:
            StorageError: If database operation fails
        """
        with UnitOfWork(self.config) as uow:
            project_id = uow.ensure_project_id(self.config.project_name)
            item_records = uow.items.find_by_project(
                uow.connection,
                project_id,
                include_archived=False,
            )

            return [
                Item(
                    id=record.id,
                    type=ItemType(record.type),
                    text=record.text,
                    created_at=record.created_at,
                    status=ItemStatus(record.status),
                )
                for record in item_records
            ]

    def load_items_for_relations(self, include_archived: bool = False) -> list[Item]:
        """Load items for relation analysis (optionally including archived).

        Args:
            include_archived: Include archived items (default: False)

        Returns:
            List of Item objects

        Raises:
            StorageError: If database operation fails
        """
        with UnitOfWork(self.config) as uow:
            project_id = uow.ensure_project_id(self.config.project_name)
            item_records = uow.items.find_by_project(
                uow.connection,
                project_id,
                include_archived=include_archived,
            )

            return [
                Item(
                    id=record.id,
                    type=ItemType(record.type),
                    text=record.text,
                    created_at=record.created_at,
                    status=ItemStatus(record.status),
                )
                for record in item_records
            ]

    def add_item(self, item: Item) -> None:
        """Add new item to storage.

        Args:
            item: Item to add

        Raises:
            StorageError: If add fails
        """
        with UnitOfWork(self.config) as uow:
            project_id = uow.ensure_project_id(self.config.project_name)

            created_at = item.created_at or datetime.now()

            uow.items.insert(
                uow.connection,
                project_id=project_id,
                type_=str(item.type),
                text=item.text,
                status=str(item.status),
                source="cli",
                created_at=created_at,
            )

    def clear_items(self) -> None:
        """Clear all items from storage.

        Raises:
            StorageError: If clear fails
        """
        with UnitOfWork(self.config) as uow:
            project_id = uow.ensure_project_id(self.config.project_name)
            uow.items.clear_project(uow.connection, project_id)

    # ========================================================================
    # RELATION OPERATIONS
    # ========================================================================

    def save_relation_suggestions(self, suggestions: list[dict]) -> int:
        """Save batch of relation suggestions (unconfirmed).

        Args:
            suggestions: List of dicts with from_item_id, to_item_id, relationship_type, reason

        Returns:
            Number of suggestions saved

        Raises:
            StorageError: If save fails
        """
        if not suggestions:
            return 0

        with UnitOfWork(self.config) as uow:
            project_id = uow.ensure_project_id(self.config.project_name)

            count = 0
            for suggestion in suggestions:
                from_id = str(suggestion["from_item_id"])
                to_id = str(suggestion["to_item_id"])

                # Validate items exist
                uow.items._assert_item_exists(uow.connection, from_id, project_id)
                uow.items._assert_item_exists(uow.connection, to_id, project_id)

                # Validate business rules
                RelationRules.validate_different_items(from_id, to_id)
                RelationRules.validate_relationship_type(suggestion["relationship_type"])

                # Insert suggestion
                uow.relations.insert_suggestion(
                    uow.connection,
                    from_item_id=from_id,
                    to_item_id=to_id,
                    relationship_type=suggestion["relationship_type"],
                    reason=suggestion.get("reason"),
                )
                count += 1

            return count

    def upsert_relation(
        self,
        from_item_id: str,
        to_item_id: str,
        relationship_type: str,
        reason: str,
        is_confirmed: bool,
    ) -> None:
        """Insert or update a relation.

        Args:
            from_item_id: Source item ID
            to_item_id: Target item ID
            relationship_type: Type of relationship
            reason: Reason/description
            is_confirmed: Whether relation is confirmed

        Raises:
            StorageError: If operation fails
        """
        with UnitOfWork(self.config) as uow:
            project_id = uow.ensure_project_id(self.config.project_name)

            # Validate items exist
            uow.items._assert_item_exists(uow.connection, from_item_id, project_id)
            uow.items._assert_item_exists(uow.connection, to_item_id, project_id)

            # Validate business rules
            RelationRules.validate_different_items(from_item_id, to_item_id)
            RelationRules.validate_relationship_type(relationship_type)

            uow.relations.upsert_relation(
                uow.connection,
                from_item_id=from_item_id,
                to_item_id=to_item_id,
                relationship_type=relationship_type,
                reason=reason,
                is_confirmed=is_confirmed,
            )

    def confirm_relation(
        self,
        from_item_id: str,
        to_item_id: str,
        relationship_type: str,
    ) -> None:
        """Confirm a relation suggestion.

        Args:
            from_item_id: Source item ID
            to_item_id: Target item ID
            relationship_type: Type of relationship

        Raises:
            StorageEntityNotFoundError: If relation not found
            StorageError: If operation fails
        """
        with UnitOfWork(self.config) as uow:
            project_id = uow.ensure_project_id(self.config.project_name)

            # Validate items exist (they should be in DB)
            uow.items._assert_item_exists(uow.connection, from_item_id, project_id)
            uow.items._assert_item_exists(uow.connection, to_item_id, project_id)

            uow.relations.confirm(
                uow.connection,
                from_item_id=from_item_id,
                to_item_id=to_item_id,
                relationship_type=relationship_type,
            )

    def reject_relation(
        self,
        from_item_id: str,
        to_item_id: str,
        relationship_type: str,
    ) -> None:
        """Reject a relation suggestion (delete it).

        Args:
            from_item_id: Source item ID
            to_item_id: Target item ID
            relationship_type: Type of relationship

        Raises:
            StorageEntityNotFoundError: If suggestion not found
            StorageError: If operation fails
        """
        with UnitOfWork(self.config) as uow:
            project_id = uow.ensure_project_id(self.config.project_name)

            # Validate items exist
            uow.items._assert_item_exists(uow.connection, from_item_id, project_id)
            uow.items._assert_item_exists(uow.connection, to_item_id, project_id)

            uow.relations.reject_suggestion(
                uow.connection,
                from_item_id=from_item_id,
                to_item_id=to_item_id,
                relationship_type=relationship_type,
            )

    def list_relations(self, item_id: str | None = None) -> list[dict]:
        """List relations (optionally filtered by item).

        Args:
            item_id: If provided, only return relations involving this item

        Returns:
            List of relation dicts with from_item_id, to_item_id, relationship_type, etc.

        Raises:
            StorageError: If operation fails
        """
        with UnitOfWork(self.config) as uow:
            if item_id:
                relation_records = uow.relations.list_for_item(uow.connection, item_id)
            else:
                relation_records = uow.relations.list_all(uow.connection)

            return [
                {
                    "id": record.id,
                    "from_item_id": record.from_item_id,
                    "to_item_id": record.to_item_id,
                    "relationship_type": record.relationship_type,
                    "reason": record.reason,
                    "is_confirmed": record.is_confirmed,
                    "confirmed_at": record.confirmed_at,
                    "created_at": record.created_at,
                }
                for record in relation_records
            ]

    # ========================================================================
    # MERGE OPERATIONS
    # ========================================================================

    def merge_items(
        self,
        target_item_id: str,
        source_item_ids: list[str],
        merge_reason: str,
    ) -> None:
        """Merge source items into target item.

        Args:
            target_item_id: Target item ID (items merged into this)
            source_item_ids: List of source item IDs (merged from these)
            merge_reason: Reason for merge

        Raises:
            StorageError: If merge fails or violates business rules
        """
        with UnitOfWork(self.config) as uow:
            project_id = uow.ensure_project_id(self.config.project_name)

            # Load all items involved
            target_record = uow.items.find_by_project(uow.connection, project_id)
            target = next((r for r in target_record if r.id == target_item_id), None)

            if not target:
                raise StorageEntityNotFoundError(f"Target item {target_item_id!r} not found")

            source_items = [
                r for r in target_record if r.id in source_item_ids
            ]

            if len(source_items) != len(source_item_ids):
                missing = set(source_item_ids) - {r.id for r in source_items}
                raise StorageEntityNotFoundError(
                    f"Source items not found: {missing}"
                )

            # Validate business rules
            for source in source_items:
                MergeRules.validate_can_merge(source.status, target.status)

            # Capture snapshot BEFORE merging
            snapshot_data = SnapshotService.create_snapshot(
                source_item={
                    "id": source_items[0].id,
                    "type": source_items[0].type,
                    "text": source_items[0].text,
                    "status": source_items[0].status,
                },
                target_item={
                    "id": target.id,
                    "type": target.type,
                    "text": target.text,
                    "status": target.status,
                },
            )

            # Merge logic: delete source items, keep target
            for source in source_items:
                uow.items.delete(uow.connection, source.id)

            # Record merge
            uow.merges.record_merge(
                uow.connection,
                project_id=project_id,
                source_item_id=source_items[0].id,
                target_item_id=target_item_id,
                merge_reason=merge_reason,
                snapshot_data=snapshot_data,
            )

    def list_merges(self, limit: int = 20) -> list[dict]:
        """List merge history.

        Args:
            limit: Maximum records to return

        Returns:
            List of merge dicts

        Raises:
            StorageError: If operation fails
        """
        with UnitOfWork(self.config) as uow:
            project_id = uow.ensure_project_id(self.config.project_name)
            merge_records = uow.merges.list_for_project(
                uow.connection,
                project_id,
                include_reverted=False,
                limit=limit,
            )

            return [
                {
                    "id": record.id,
                    "source_item_id": record.source_item_id,
                    "target_item_id": record.target_item_id,
                    "merge_reason": record.merge_reason,
                    "merged_by": record.merged_by,
                    "created_at": record.created_at,
                    "snapshot_data": record.snapshot_data,
                }
                for record in merge_records
            ]

    def undo_last_merge(self, merge_id: str | None = None) -> dict:
        """Undo a merge operation (rollback from snapshot).

        Args:
            merge_id: Specific merge to undo (default: undo latest)

        Returns:
            Dict with undo results and instructions

        Raises:
            StorageError: If undo fails or merge cannot be reverted
        """
        with UnitOfWork(self.config) as uow:
            project_id = uow.ensure_project_id(self.config.project_name)

            # Find merge to undo
            if merge_id:
                merge = uow.merges.find_by_id(uow.connection, merge_id)
                if not merge:
                    raise StorageEntityNotFoundError(f"Merge {merge_id!r} not found")
            else:
                merge = uow.merges.find_latest_for_project(uow.connection, project_id)
                if not merge:
                    raise StorageEntityNotFoundError("No merges to undo")

            # Validate merge can be undone
            MergeRules.validate_can_undo_merge(merge.status, merge.reverted_at is not None)

            # Validate snapshot
            SnapshotService.validate_snapshot(merge.snapshot_data)

            # Mark merge as reverted
            uow.merges.mark_reverted(uow.connection, merge.id)

            return {
                "merge_id": merge.id,
                "source_item_id": merge.source_item_id,
                "target_item_id": merge.target_item_id,
                "reverted_at": datetime.now().isoformat(),
                "snapshot": merge.snapshot_data,
                "instructions": SnapshotService.get_rollback_instructions(merge.snapshot_data),
            }
