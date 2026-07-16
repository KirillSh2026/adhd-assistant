"""Merge undo/rollback service.

Handles reverting merge operations:
- Find merge to undo
- Validate undo is allowed
- Validate snapshot integrity
- Build rollback instructions
- Mark merge as reverted
"""

from __future__ import annotations

from datetime import datetime

from core.exceptions import StorageEntityNotFoundError
from storage.postgres.unit_of_work import UnitOfWork
from storage.postgres.domain_rules import MergeRules
from storage.postgres.snapshot_service import SnapshotService


class UndoService:
    """Service for undoing merge operations.
    
    Workflow:
    1. Find merge to undo (by ID or latest)
    2. Validate merge can be undone (not already reverted, etc.)
    3. Validate snapshot is complete and valid
    4. Mark merge as reverted
    5. Return rollback instructions to caller
    """

    @staticmethod
    def undo_last_merge(
        uow: UnitOfWork,
        project_id: str,
        merge_id: str | None = None,
    ) -> dict:
        """Undo a merge operation (mark as reverted).
        
        Args:
            uow: UnitOfWork providing repositories and connection
            project_id: Project ID for isolation
            merge_id: Specific merge to undo (None = latest)
        
        Returns:
            Dict with undo results and rollback instructions:
            {
                "merge_id": str,
                "source_item_id": str,
                "target_item_id": str,
                "reverted_at": str (ISO format),
                "snapshot": dict (original item data),
                "instructions": dict (rollback steps)
            }
        
        Raises:
            StorageEntityNotFoundError: If merge not found or no merges exist
            ValueError: If merge cannot be undone
        """
        # Step 1: Find merge to undo
        merge = UndoService._find_merge_to_undo(uow, project_id, merge_id)
        
        # Step 2: Validate undo is allowed
        MergeRules.validate_can_undo_merge(merge.status, merge.reverted_at is not None)
        
        # Step 3: Validate snapshot
        SnapshotService.validate_snapshot(merge.snapshot_data)
        
        # Step 4: Mark merge as reverted
        uow.merges.mark_reverted(uow.connection, merge.id)
        
        # Step 5: Return results and instructions
        return {
            "merge_id": merge.id,
            "source_item_id": merge.source_item_id,
            "target_item_id": merge.target_item_id,
            "reverted_at": datetime.now().isoformat(),
            "snapshot": merge.snapshot_data,
            "instructions": SnapshotService.get_rollback_instructions(merge.snapshot_data),
        }

    @staticmethod
    def _find_merge_to_undo(
        uow: UnitOfWork,
        project_id: str,
        merge_id: str | None = None,
    ):
        """Find merge to undo (by ID or latest).
        
        Args:
            uow: UnitOfWork providing repositories
            project_id: Project ID for isolation
            merge_id: Specific merge ID (None = find latest)
        
        Returns:
            Merge record
        
        Raises:
            StorageEntityNotFoundError: If merge not found or no merges exist
        """
        if merge_id:
            # Find specific merge by ID
            merge = uow.merges.find_by_id(uow.connection, merge_id)
            if not merge:
                raise StorageEntityNotFoundError(
                    f"Merge {merge_id!r} not found"
                )
        else:
            # Find latest merge for project
            merge = uow.merges.find_latest_for_project(uow.connection, project_id)
            if not merge:
                raise StorageEntityNotFoundError(
                    "No merges found for project to undo"
                )
        
        return merge
