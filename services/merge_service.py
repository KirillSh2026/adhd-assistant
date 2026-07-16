"""Merge service: item merging and merge history operations."""

from core.exceptions import CliInputError
from interfaces.storage import Storage
from services.shared_item_utils import SharedItemUtils


class MergeService:
    """Handles item merging, merge history, and merge undo operations."""

    def __init__(self, storage: Storage):
        self.storage = storage
        self.utils = SharedItemUtils(storage)

    def merge_items(self, target_index: int, source_indices: list[int], merge_reason: str = "") -> None:
        """Merge source items into target item."""
        if not source_indices:
            raise CliInputError("At least one source item index is required for merge")
        if len(set(source_indices)) != len(source_indices):
            raise CliInputError("Merge source indexes must be unique")

        items = self.utils.get_relation_items()
        target_item = self.utils.resolve_item_by_index(target_index, items)
        source_items = [self.utils.resolve_item_by_index(index, items) for index in source_indices]
        if any(source_item.id == target_item.id for source_item in source_items):
            raise CliInputError("Target item cannot also be a merge source")

        final_reason = merge_reason or "Merged from CLI after review"
        self.storage.merge_items(
            target_item_id=self.utils.require_item_id(target_item),
            source_item_ids=[self.utils.require_item_id(source_item) for source_item in source_items],
            merge_reason=final_reason,
        )

    def list_merges(self, limit: int = 20) -> list[dict]:
        """List recent merge operations."""
        items = self.utils.get_relation_items()
        item_index_by_id = self.utils.build_item_index(items)
        merges = self.storage.list_merges(limit=limit)
        return [
            {
                "merge_id": merge["merge_id"],
                "target_index": item_index_by_id.get(merge["target_item_id"]),
                "target_item_id": merge["target_item_id"],
                "source_indices": [item_index_by_id.get(item_id) for item_id in merge["source_item_ids"]],
                "source_item_ids": merge["source_item_ids"],
                "can_undo": merge["can_undo"],
                "reason": merge["reason"],
                "performed_at": merge["performed_at"],
            }
            for merge in merges
        ]

    def undo_merge(self, merge_id: str | None = None) -> dict:
        """Undo a merge operation."""
        result = self.storage.undo_last_merge(merge_id=merge_id)
        items = self.utils.get_relation_items()
        item_index_by_id = self.utils.build_item_index(items)
        return {
            "merge_id": result["merge_id"],
            "target_index": item_index_by_id.get(result["target_item_id"]),
            "target_item_id": result["target_item_id"],
            "source_indices": [item_index_by_id.get(item_id) for item_id in result["source_item_ids"]],
            "source_item_ids": result["source_item_ids"],
            "reason": result["reason"],
        }
