"""Relation service: managing item relationships, suggestions, and clustering."""

from interfaces.storage import Storage
from models.item import Item
from services.relation_analysis_service import ItemCluster, RelationAnalysisService, RelationSuggestion
from services.shared_item_utils import SharedItemUtils


class RelationService:
    """Handles item relation operations: suggestions, clustering, linking, and confirmation."""

    def __init__(
        self,
        storage: Storage,
        relation_analyzer: RelationAnalysisService | None = None,
    ):
        self.storage = storage
        self.relation_analyzer = relation_analyzer or RelationAnalysisService()
        self.utils = SharedItemUtils(storage)

    def suggest_relations(self) -> list[dict]:
        """Generate and save relation suggestions."""
        items = self.utils.get_relation_items()
        suggestions = self.relation_analyzer.suggest_relations(items)
        serialized = [
            {
                "from_item_id": suggestion.from_item_id,
                "to_item_id": suggestion.to_item_id,
                "relationship_type": suggestion.relationship_type,
                "reason": f"{suggestion.reason}; score={suggestion.score:.2f}",
            }
            for suggestion in suggestions
        ]
        self.storage.save_relation_suggestions(serialized)
        item_index_by_id = self.utils.build_item_index(items)
        return [self._format_suggestion(suggestion, item_index_by_id, items) for suggestion in suggestions]

    def show_clusters(self) -> list[dict]:
        """Show similarity clusters."""
        items = self.utils.get_relation_items()
        item_index_by_id = self.utils.build_item_index(items)
        items_by_id = {item.id: item for item in items if item.id}
        clusters = self.relation_analyzer.build_clusters(items)
        return [self._format_cluster(cluster, item_index_by_id, items_by_id) for cluster in clusters]

    def list_relations(self, item_index: int | None = None) -> list[dict]:
        """List relations, optionally filtered by item."""
        items = self.utils.get_relation_items()
        item_index_by_id = self.utils.build_item_index(items)
        item_id = self.utils.resolve_item_by_index(item_index, items).id if item_index is not None else None
        relations = self.storage.list_relations(item_id=item_id)
        formatted: list[dict] = []
        for relation in relations:
            formatted.append(
                {
                    "from_index": item_index_by_id.get(relation["from_item_id"]),
                    "to_index": item_index_by_id.get(relation["to_item_id"]),
                    "relationship_type": self.utils.to_display_relationship_type(
                        relation["relationship_type"]
                    ),
                    "is_confirmed": relation["is_confirmed"],
                    "reason": relation["reason"],
                    "from_text": relation["from_text"],
                    "to_text": relation["to_text"],
                    "created_at": relation["created_at"],
                }
            )
        return formatted

    def link_items(self, from_index: int, to_index: int, relation_type: str, reason: str = "") -> None:
        """Explicitly link two items."""
        items = self.utils.get_relation_items()
        from_item = self.utils.resolve_item_by_index(from_index, items)
        to_item = self.utils.resolve_item_by_index(to_index, items)
        storage_relation_type = self.utils.to_storage_relationship_type(relation_type)
        final_reason = reason or f"Linked manually as {self.utils.to_display_relationship_type(storage_relation_type)}"
        self.storage.upsert_relation(
            from_item_id=self.utils.require_item_id(from_item),
            to_item_id=self.utils.require_item_id(to_item),
            relationship_type=storage_relation_type,
            reason=final_reason,
            is_confirmed=True,
        )

    def confirm_relation(self, from_index: int, to_index: int, relation_type: str) -> None:
        """Confirm a suggested relation."""
        items = self.utils.get_relation_items()
        from_item = self.utils.resolve_item_by_index(from_index, items)
        to_item = self.utils.resolve_item_by_index(to_index, items)
        storage_relation_type = self.utils.to_storage_relationship_type(relation_type)
        self.storage.confirm_relation(
            from_item_id=self.utils.require_item_id(from_item),
            to_item_id=self.utils.require_item_id(to_item),
            relationship_type=storage_relation_type,
        )

    def reject_relation(self, from_index: int, to_index: int, relation_type: str) -> None:
        """Reject a suggested relation."""
        items = self.utils.get_relation_items()
        from_item = self.utils.resolve_item_by_index(from_index, items)
        to_item = self.utils.resolve_item_by_index(to_index, items)
        storage_relation_type = self.utils.to_storage_relationship_type(relation_type)
        self.storage.reject_relation(
            from_item_id=self.utils.require_item_id(from_item),
            to_item_id=self.utils.require_item_id(to_item),
            relationship_type=storage_relation_type,
        )

    def _format_suggestion(
        self,
        suggestion: RelationSuggestion,
        item_index_by_id: dict[str, int],
        items: list[Item],
    ) -> dict:
        """Format suggestion for display."""
        items_by_id = {item.id: item for item in items if item.id}
        return {
            "from_index": item_index_by_id[suggestion.from_item_id],
            "to_index": item_index_by_id[suggestion.to_item_id],
            "relationship_type": self.utils.to_display_relationship_type(suggestion.relationship_type),
            "score": suggestion.score,
            "reason": suggestion.reason,
            "from_text": items_by_id[suggestion.from_item_id].text,
            "to_text": items_by_id[suggestion.to_item_id].text,
        }

    def _format_cluster(
        self,
        cluster: ItemCluster,
        item_index_by_id: dict[str, int],
        items_by_id: dict[str, Item],
    ) -> dict:
        """Format cluster for display."""
        members = [
            {
                "index": item_index_by_id[item_id],
                "type": items_by_id[item_id].type,
                "text": items_by_id[item_id].text,
            }
            for item_id in cluster.member_ids
        ]
        members.sort(key=lambda member: member["index"])
        return {
            "size": len(members),
            "average_score": cluster.average_score,
            "members": members,
        }
