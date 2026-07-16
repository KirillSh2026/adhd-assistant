"""PostgreSQL storage implementation using repository pattern.

This is the refactored version of PostgreSQL storage after Phase 5.
It now uses:
- UnitOfWork for transaction management
- 4 repositories for data access
- MergeOrchestrator for merge coordination
- UndoService for rollback operations
- Domain rules for business logic validation
- SnapshotService for merge safety

The public interface remains 100% compatible with the original version.
All existing code continues to work without changes.

IMPORTANT: This is NOT a storage backend in the traditional sense anymore.
It's a thin facade over orchestration services + repositories + UnitOfWork.
Business logic lives in services and domain rules, not here.

Architecture:
    PostgresStorage (orchestrator facade)
      ↓
    UnitOfWork (transaction + connection management)
      ↓
    Repositories (data access layer)
      ├─ ProjectRepository
      ├─ ItemRepository
      ├─ RelationRepository
      └─ MergeRepository
      ↓
    Orchestration Services (business workflows)
      ├─ MergeOrchestrator (merge_items flow)
      └─ UndoService (undo_last_merge flow)
      
    Domain Services (reusable logic)
      ├─ Domain Rules (business validation)
      └─ SnapshotService (merge snapshots)
"""

from __future__ import annotations

from datetime import datetime

from core.exceptions import StorageEntityNotFoundError, StorageError
from models.item import Item, ItemStatus, ItemType
from storage.postgres.config import PostgresConfig
from storage.postgres.unit_of_work import UnitOfWork
from storage.postgres.domain_rules import MergeRules, RelationRules, ItemRules
from storage.postgres.snapshot_service import SnapshotService
from storage.postgres.merge_orchestrator import MergeOrchestrator
from storage.postgres.undo_service import UndoService


class PostgresStorage:
    """PostgreSQL storage backend with thin orchestration layer.

    This class implements the Storage interface but delegates nearly all
    operations to orchestration services and repositories.
    
    Key invariants:
    1. All data access goes through UnitOfWork
    2. All business logic goes through services (Orchestrators, DomainRules)
    3. All database transactions are scoped to UnitOfWork context manager
    4. No stored procedures or complex SQL in this class
    
    Public API (all operations):
    - load_items() → list[Item]
    - load_items_for_relations(include_archived=False) → list[Item]
    - add_item(item: Item) → None
    - clear_items() → None
    - save_relation_suggestions(suggestions: list[dict]) → int
    - upsert_relation(from_item_id, to_item_id, relationship_type, reason, is_confirmed) → None
    - confirm_relation(from_item_id, to_item_id, relationship_type) → None
    - reject_relation(from_item_id, to_item_id, relationship_type) → None
    - list_relations(item_id: str | None = None) → list[dict]
    - merge_items(target_item_id, source_item_ids, merge_reason) → None
    - list_merges(limit=20) → list[dict]
    - undo_last_merge(merge_id: str | None = None) → dict
    """

    def __init__(self, dsn: str, project_name: str = "Inbox"):
        """Initialize PostgreSQL storage.

        Args:
            dsn: PostgreSQL connection string
            project_name: Project name for isolation (default: "Inbox")
        """
        self.config = PostgresConfig(dsn=dsn, project_name=project_name)

    # ========================================================================
    # ITEM OPERATIONS (READ)
    # ========================================================================

    def load_items(self) -> list[Item]:
        """Load all active items from storage.

        Returns:
            List of Item objects (excluding archived)

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

    # ========================================================================
    # ITEM OPERATIONS (WRITE)
    # ========================================================================

    def add_item(self, item: Item) -> None:
        """Add a new item to storage.

        Args:
            item: Item to add (must have non-empty text, valid type/status)

        Raises:
            StorageError: If add fails
            ValueError: If item validation fails
        """
        with UnitOfWork(self.config) as uow:
            project_id = uow.ensure_project_id(self.config.project_name)
            
            # Validate item before storage
            ItemRules.validate_item_type(item.type)
            ItemRules.validate_item_status(item.status)
            
            # Insert through repository
            uow.items.insert(
                uow.connection,
                project_id=project_id,
                item_type=item.type.value,
                text=item.text,
                created_at=item.created_at,
                status=item.status.value,
            )

    def clear_items(self) -> None:
        """Clear all items from storage for this project.

        Raises:
            StorageError: If clear fails
        """
        with UnitOfWork(self.config) as uow:
            project_id = uow.ensure_project_id(self.config.project_name)
            uow.items.delete_all_by_project(uow.connection, project_id)

    # ========================================================================
    # RELATION OPERATIONS (SUGGESTIONS & BATCH)
    # ========================================================================

    def save_relation_suggestions(self, suggestions: list[dict]) -> int:
        """Save batch of relation suggestions (unconfirmed).

        Args:
            suggestions: List of suggestion dicts with keys:
                - from_item_id: str (source item)
                - to_item_id: str (target item)
                - relationship_type: str (type of relation)
                - reason: str (optional, why suggested)

        Returns:
            Number of suggestions saved

        Raises:
            StorageError: If save fails
            ValueError: If suggestion violates business rules
        """
        with UnitOfWork(self.config) as uow:
            project_id = uow.ensure_project_id(self.config.project_name)
            
            count = 0
            for suggestion in suggestions:
                # Validate
                RelationRules.validate_different_items(
                    suggestion["from_item_id"],
                    suggestion["to_item_id"],
                )
                RelationRules.validate_relationship_type(suggestion["relationship_type"])
                
                # Save as unconfirmed suggestion
                uow.relations.insert_suggestion(
                    uow.connection,
                    project_id=project_id,
                    from_item_id=suggestion["from_item_id"],
                    to_item_id=suggestion["to_item_id"],
                    relationship_type=suggestion["relationship_type"],
                    reason=suggestion.get("reason", ""),
                )
                count += 1
            
            return count

    # ========================================================================
    # RELATION OPERATIONS (CONFIRMED RELATIONS)
    # ========================================================================

    def upsert_relation(
        self,
        from_item_id: str,
        to_item_id: str,
        relationship_type: str,
        reason: str = "",
        is_confirmed: bool = False,
    ) -> None:
        """Create or update a confirmed relation between items.

        Args:
            from_item_id: Source item ID
            to_item_id: Target item ID
            relationship_type: Type of relation (depends_on, related_to, duplicate_of, etc.)
            reason: Optional description of the relation
            is_confirmed: Whether this is a user-confirmed relation (default: False)

        Raises:
            StorageError: If operation fails
            ValueError: If items are same or type is invalid
        """
        with UnitOfWork(self.config) as uow:
            project_id = uow.ensure_project_id(self.config.project_name)
            
            # Validate before storage
            RelationRules.validate_different_items(from_item_id, to_item_id)
            RelationRules.validate_relationship_type(relationship_type)
            
            # Create or update relation
            uow.relations.upsert_relation(
                uow.connection,
                project_id=project_id,
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
        """Mark a relation as confirmed by user.

        Args:
            from_item_id: Source item ID
            to_item_id: Target item ID
            relationship_type: Relation type

        Raises:
            StorageEntityNotFoundError: If relation not found
            StorageError: If update fails
        """
        with UnitOfWork(self.config) as uow:
            project_id = uow.ensure_project_id(self.config.project_name)
            
            uow.relations.confirm_relation(
                uow.connection,
                project_id=project_id,
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
        """Remove an unconfirmed relation suggestion.

        Args:
            from_item_id: Source item ID
            to_item_id: Target item ID
            relationship_type: Relation type

        Raises:
            StorageEntityNotFoundError: If relation not found
            StorageError: If delete fails
        """
        with UnitOfWork(self.config) as uow:
            project_id = uow.ensure_project_id(self.config.project_name)
            
            uow.relations.reject_relation(
                uow.connection,
                project_id=project_id,
                from_item_id=from_item_id,
                to_item_id=to_item_id,
                relationship_type=relationship_type,
            )

    def list_relations(self, item_id: str | None = None) -> list[dict]:
        """List confirmed relations in this project.

        Args:
            item_id: Optional item ID to filter relations for (default: all)

        Returns:
            List of relation dicts:
            {
                "from_item_id": str,
                "to_item_id": str,
                "relationship_type": str,
                "is_confirmed": bool,
                "reason": str,
            }

        Raises:
            StorageError: If query fails
        """
        with UnitOfWork(self.config) as uow:
            project_id = uow.ensure_project_id(self.config.project_name)
            
            relations = uow.relations.find_for_project(
                uow.connection,
                project_id,
                item_id=item_id,
            )
            
            return [
                {
                    "from_item_id": r.from_item_id,
                    "to_item_id": r.to_item_id,
                    "relationship_type": r.relationship_type,
                    "is_confirmed": r.is_confirmed,
                    "reason": r.reason,
                }
                for r in relations
            ]

    # ========================================================================
    # MERGE OPERATIONS (ORCHESTRATED)
    # ========================================================================

    def merge_items(
        self,
        target_item_id: str,
        source_item_ids: list[str],
        merge_reason: str,
    ) -> None:
        """Merge source items into target item (DESTRUCTIVE).

        Workflow (orchestrated by MergeOrchestrator):
        1. Load target and source items
        2. Validate merge is allowed (status checks, etc.)
        3. Capture snapshot for rollback support
        4. Delete source items from storage
        5. Record merge operation with snapshot

        Args:
            target_item_id: Item to merge into (preserved)
            source_item_ids: Items to merge from (deleted)
            merge_reason: Reason for merge (audit trail, user reference)

        Raises:
            StorageEntityNotFoundError: If target or source not found
            ValueError: If merge violates business rules
            StorageError: If operation fails
        """
        with UnitOfWork(self.config) as uow:
            project_id = uow.ensure_project_id(self.config.project_name)
            
            # Delegate to MergeOrchestrator for full workflow
            MergeOrchestrator.execute_merge(
                uow,
                project_id=project_id,
                target_item_id=target_item_id,
                source_item_ids=source_item_ids,
                merge_reason=merge_reason,
            )

    def list_merges(self, limit: int = 20) -> list[dict]:
        """List merge operations (audit trail).

        Args:
            limit: Maximum merges to return (default: 20)

        Returns:
            List of merge records:
            {
                "id": str,
                "source_item_id": str,
                "target_item_id": str,
                "merge_reason": str,
                "created_at": str (ISO format) | None,
                "reverted_at": str (ISO format) | None,
            }

        Raises:
            StorageError: If query fails
        """
        with UnitOfWork(self.config) as uow:
            project_id = uow.ensure_project_id(self.config.project_name)
            
            merges = uow.merges.find_for_project(
                uow.connection,
                project_id,
                limit=limit,
            )
            
            return [
                {
                    "id": m.id,
                    "source_item_id": m.source_item_id,
                    "target_item_id": m.target_item_id,
                    "merge_reason": m.merge_reason,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                    "reverted_at": m.reverted_at.isoformat() if m.reverted_at else None,
                }
                for m in merges
            ]

    def undo_last_merge(self, merge_id: str | None = None) -> dict:
        """Undo a merge operation (mark as reverted, provide rollback info).

        Workflow (orchestrated by UndoService):
        1. Find merge to undo (by ID or latest)
        2. Validate undo is allowed (not already reverted)
        3. Validate snapshot is complete
        4. Mark merge as reverted
        5. Return rollback instructions

        Args:
            merge_id: Specific merge to undo (None = undo latest)

        Returns:
            Dict with undo results:
            {
                "merge_id": str,
                "source_item_id": str,
                "target_item_id": str,
                "reverted_at": str (ISO format),
                "snapshot": dict (original item data),
                "instructions": dict (rollback steps),
            }

        Raises:
            StorageEntityNotFoundError: If merge not found or no merges exist
            ValueError: If merge cannot be undone (already reverted, etc.)
            StorageError: If operation fails
        """
        with UnitOfWork(self.config) as uow:
            project_id = uow.ensure_project_id(self.config.project_name)
            
            # Delegate to UndoService for full workflow
            return UndoService.undo_last_merge(
                uow,
                project_id=project_id,
                merge_id=merge_id,
            )
