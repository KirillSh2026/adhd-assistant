"""Item service registry: facade combining all use-case services."""

from datetime import datetime

from interfaces.storage import Storage
from services.capture_service import CaptureService
from services.item_type_classifier import ItemTypeClassifier
from services.list_service import ListService
from services.merge_service import MergeService
from services.relation_analysis_service import RelationAnalysisService
from services.relation_service import RelationService


class ItemServiceRegistry:
    """
    Facade combining all item service layers.
    Provides backwards compatibility while allowing gradual migration to specialized services.
    """

    def __init__(
        self,
        storage: Storage,
        classifier: ItemTypeClassifier | None = None,
        relation_analyzer: RelationAnalysisService | None = None,
    ):
        self._classifier = classifier or ItemTypeClassifier()
        self._relation_analyzer = relation_analyzer or RelationAnalysisService()

        self.capture = CaptureService(storage, self._classifier)
        self.list = ListService(storage)
        self.relation = RelationService(storage, self._relation_analyzer)
        self.merge = MergeService(storage)

    # Capture delegation methods
    def add_item(self, note_type: str, text: str, created_at: datetime) -> None:
        """Add item of specified type."""
        self.capture.add_item(note_type, text, created_at)

    def add_captured_item(self, text: str, created_at: datetime, note_type: str | None = None) -> str:
        """Add item with auto-classification if type not specified."""
        return self.capture.add_captured_item(text, created_at, note_type)

    def clear_items(self) -> None:
        """Clear all items from storage."""
        self.capture.clear_items()

    # List delegation methods
    def list_items(self, list_type: str):
        """List items, optionally filtered by type."""
        return self.list.list_items(list_type)

    # Relation delegation methods
    def suggest_relations(self):
        """Generate and save relation suggestions."""
        return self.relation.suggest_relations()

    def show_clusters(self):
        """Show similarity clusters."""
        return self.relation.show_clusters()

    def list_relations(self, item_index: int | None = None):
        """List relations, optionally filtered by item."""
        return self.relation.list_relations(item_index)

    def link_items(self, from_index: int, to_index: int, relation_type: str, reason: str = "") -> None:
        """Explicitly link two items."""
        self.relation.link_items(from_index, to_index, relation_type, reason)

    def confirm_relation(self, from_index: int, to_index: int, relation_type: str) -> None:
        """Confirm a suggested relation."""
        self.relation.confirm_relation(from_index, to_index, relation_type)

    def reject_relation(self, from_index: int, to_index: int, relation_type: str) -> None:
        """Reject a suggested relation."""
        self.relation.reject_relation(from_index, to_index, relation_type)

    # Merge delegation methods
    def merge_items(self, target_index: int, source_indices: list[int], merge_reason: str = "") -> None:
        """Merge source items into target item."""
        self.merge.merge_items(target_index, source_indices, merge_reason)

    def list_merges(self, limit: int = 20):
        """List recent merge operations."""
        return self.merge.list_merges(limit)

    def undo_merge(self, merge_id: str | None = None):
        """Undo a merge operation."""
        return self.merge.undo_merge(merge_id)
