"""Merge operation orchestration service.

Coordinates merge_items workflow:
- Load and validate items
- Check business rules
- Capture snapshot
- Execute merge (delete sources, record merge)
- Provide rollback support

Separates orchestration from storage implementation.
All database operations delegated to repositories.
"""

from __future__ import annotations

from core.exceptions import StorageEntityNotFoundError
from storage.postgres.unit_of_work import UnitOfWork
from storage.postgres.domain_rules import MergeRules
from storage.postgres.snapshot_service import SnapshotService


class MergeOrchestrator:
    """Orchestrates merge item operations.
    
    Workflow:
    1. Load target and source items from repository
    2. Validate using domain rules
    3. Capture snapshot for rollback
    4. Delete source items
    5. Record merge with snapshot
    """

    @staticmethod
    def execute_merge(
        uow: UnitOfWork,
        project_id: str,
        target_item_id: str,
        source_item_ids: list[str],
        merge_reason: str,
    ) -> None:
        """Execute merge operation with full validation and snapshot.
        
        Args:
            uow: UnitOfWork providing repositories and connection
            project_id: Project ID for isolation
            target_item_id: Item to merge into (target)
            source_item_ids: Items to merge from (sources)
            merge_reason: Reason for merge (audit trail)
        
        Raises:
            StorageEntityNotFoundError: If items don't exist
            ValueError: If merge violates business rules
        """
        # Step 1: Load target item
        target = MergeOrchestrator._load_target_item(
            uow, project_id, target_item_id
        )
        
        # Step 2: Load source items
        sources = MergeOrchestrator._load_source_items(
            uow, project_id, source_item_ids, target_item_id
        )
        
        # Step 3: Validate merge is allowed
        for source in sources:
            MergeRules.validate_can_merge(source.status, target.status)
        
        # Step 4: Capture snapshot for rollback support
        snapshot_data = SnapshotService.create_snapshot(
            source_item={
                "id": sources[0].id,
                "type": sources[0].type,
                "text": sources[0].text,
                "status": sources[0].status,
            },
            target_item={
                "id": target.id,
                "type": target.type,
                "text": target.text,
                "status": target.status,
            },
        )
        
        # Step 5: Execute merge (delete sources)
        for source in sources:
            uow.items.delete(uow.connection, source.id)
        
        # Step 6: Record merge with snapshot
        uow.merges.record_merge(
            uow.connection,
            project_id=project_id,
            source_item_id=sources[0].id,
            target_item_id=target_item_id,
            merge_reason=merge_reason,
            snapshot_data=snapshot_data,
        )

    @staticmethod
    def _load_target_item(uow: UnitOfWork, project_id: str, target_item_id: str):
        """Load and validate target item exists.
        
        Raises:
            StorageEntityNotFoundError: If target not found
        """
        items = uow.items.find_by_project(uow.connection, project_id, include_archived=True)
        target = next((r for r in items if r.id == target_item_id), None)
        
        if not target:
            raise StorageEntityNotFoundError(
                f"Target item {target_item_id!r} not found in project {project_id!r}"
            )
        
        return target

    @staticmethod
    def _load_source_items(
        uow: UnitOfWork,
        project_id: str,
        source_item_ids: list[str],
        target_item_id: str,
    ):
        """Load and validate all source items exist and are different from target.
        
        Raises:
            StorageEntityNotFoundError: If any source not found or is target
            ValueError: If target is in sources
        """
        if target_item_id in source_item_ids:
            raise ValueError("Target item cannot be in source list for merge")
        
        items = uow.items.find_by_project(uow.connection, project_id, include_archived=True)
        sources = [r for r in items if r.id in source_item_ids]
        
        if len(sources) != len(source_item_ids):
            missing = set(source_item_ids) - {r.id for r in sources}
            raise StorageEntityNotFoundError(
                f"Source items not found: {missing}"
            )
        
        return sources
