from __future__ import annotations

from datetime import datetime

from models.item import Item
from services.item_type_classifier import ItemTypeClassifier, SUPPORTED_ITEM_TYPES
from services.relation_analysis_service import ItemCluster, RelationAnalysisService, RelationSuggestion


CLI_RELATIONSHIP_TYPES = {
    "related": "relates_to",
    "relates_to": "relates_to",
    "depends_on": "blocked_by",
    "blocked_by": "blocked_by",
    "blocks": "blocks",
    "duplicate_of": "duplicate_of",
}

DISPLAY_RELATIONSHIP_TYPES = {
    "relates_to": "related",
    "blocked_by": "depends_on",
    "blocks": "blocks",
    "duplicate_of": "duplicate_of",
    "subtask_of": "subtask_of",
    "parent_of": "parent_of",
}


class ItemService:
    def __init__(
        self,
        storage,
        classifier: ItemTypeClassifier | None = None,
        relation_analyzer: RelationAnalysisService | None = None,
    ):
        self.storage = storage
        self.classifier = classifier or ItemTypeClassifier()
        self.relation_analyzer = relation_analyzer or RelationAnalysisService()

    def add_item(self, note_type: str, text: str, created_at: datetime) -> None:
        if note_type not in SUPPORTED_ITEM_TYPES:
            raise ValueError(f"Unsupported item type: {note_type}")
        item = Item.from_input(note_type=note_type, text=text, created_at=created_at)
        self.storage.add_item(item)

    def add_captured_item(self, text: str, created_at: datetime, note_type: str | None = None) -> str:
        resolved_type = note_type or self.classifier.classify(text)
        self.add_item(note_type=resolved_type, text=text, created_at=created_at)
        return resolved_type

    def clear_items(self) -> None:
        self.storage.clear_items()

    def list_items(self, list_type: str) -> list[tuple[int, Item]]:
        items = [item for item in self.storage.load_items() if item.has_text()]

        if list_type in {"task", "note", "idea"}:
            return [
                (index, item)
                for index, item in enumerate(items, start=1)
                if item.type.strip() == list_type
            ]

        if list_type in {"all", ""}:
            return list(enumerate(items, start=1))

        return []

    def suggest_relations(self) -> list[dict]:
        items = self._get_relation_items()
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
        item_index_by_id = self._build_item_index(items)
        return [self._format_suggestion(suggestion, item_index_by_id, items) for suggestion in suggestions]

    def show_clusters(self) -> list[dict]:
        items = self._get_relation_items()
        item_index_by_id = self._build_item_index(items)
        items_by_id = {item.id: item for item in items if item.id}
        clusters = self.relation_analyzer.build_clusters(items)
        return [self._format_cluster(cluster, item_index_by_id, items_by_id) for cluster in clusters]

    def list_relations(self, item_index: int | None = None) -> list[dict]:
        self._require_advanced_storage()
        items = self._get_relation_items()
        item_index_by_id = self._build_item_index(items)
        item_id = self._resolve_item_by_index(item_index, items).id if item_index is not None else None
        relations = self.storage.list_relations(item_id=item_id)
        formatted: list[dict] = []
        for relation in relations:
            formatted.append(
                {
                    "from_index": item_index_by_id.get(relation["from_item_id"]),
                    "to_index": item_index_by_id.get(relation["to_item_id"]),
                    "relationship_type": self._to_display_relationship_type(relation["relationship_type"]),
                    "is_confirmed": relation["is_confirmed"],
                    "reason": relation["reason"],
                    "from_text": relation["from_text"],
                    "to_text": relation["to_text"],
                    "created_at": relation["created_at"],
                }
            )
        return formatted

    def link_items(self, from_index: int, to_index: int, relation_type: str, reason: str = "") -> None:
        items = self._get_relation_items()
        from_item = self._resolve_item_by_index(from_index, items)
        to_item = self._resolve_item_by_index(to_index, items)
        storage_relation_type = self._to_storage_relationship_type(relation_type)
        final_reason = reason or f"Linked manually as {self._to_display_relationship_type(storage_relation_type)}"
        self.storage.upsert_relation(
            from_item_id=self._require_item_id(from_item),
            to_item_id=self._require_item_id(to_item),
            relationship_type=storage_relation_type,
            reason=final_reason,
            is_confirmed=True,
        )

    def confirm_relation(self, from_index: int, to_index: int, relation_type: str) -> None:
        items = self._get_relation_items()
        from_item = self._resolve_item_by_index(from_index, items)
        to_item = self._resolve_item_by_index(to_index, items)
        storage_relation_type = self._to_storage_relationship_type(relation_type)
        self.storage.confirm_relation(
            from_item_id=self._require_item_id(from_item),
            to_item_id=self._require_item_id(to_item),
            relationship_type=storage_relation_type,
        )

    def reject_relation(self, from_index: int, to_index: int, relation_type: str) -> None:
        items = self._get_relation_items()
        from_item = self._resolve_item_by_index(from_index, items)
        to_item = self._resolve_item_by_index(to_index, items)
        storage_relation_type = self._to_storage_relationship_type(relation_type)
        self.storage.reject_relation(
            from_item_id=self._require_item_id(from_item),
            to_item_id=self._require_item_id(to_item),
            relationship_type=storage_relation_type,
        )

    def merge_items(self, target_index: int, source_indices: list[int], merge_reason: str = "") -> None:
        if not source_indices:
            raise ValueError("At least one source item index is required for merge")
        if len(set(source_indices)) != len(source_indices):
            raise ValueError("Merge source indexes must be unique")

        items = self._get_relation_items()
        target_item = self._resolve_item_by_index(target_index, items)
        source_items = [self._resolve_item_by_index(index, items) for index in source_indices]
        if any(source_item.id == target_item.id for source_item in source_items):
            raise ValueError("Target item cannot also be a merge source")

        final_reason = merge_reason or "Merged from CLI after review"
        self.storage.merge_items(
            target_item_id=self._require_item_id(target_item),
            source_item_ids=[self._require_item_id(source_item) for source_item in source_items],
            merge_reason=final_reason,
        )

    def list_merges(self, limit: int = 20) -> list[dict]:
        self._require_advanced_storage()
        items = self._get_relation_items()
        item_index_by_id = self._build_item_index(items)
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
        self._require_advanced_storage()
        result = self.storage.undo_last_merge(merge_id=merge_id)
        items = self._get_relation_items()
        item_index_by_id = self._build_item_index(items)
        return {
            "merge_id": result["merge_id"],
            "target_index": item_index_by_id.get(result["target_item_id"]),
            "target_item_id": result["target_item_id"],
            "source_indices": [item_index_by_id.get(item_id) for item_id in result["source_item_ids"]],
            "source_item_ids": result["source_item_ids"],
            "reason": result["reason"],
        }

    def _format_suggestion(
        self,
        suggestion: RelationSuggestion,
        item_index_by_id: dict[str, int],
        items: list[Item],
    ) -> dict:
        items_by_id = {item.id: item for item in items if item.id}
        return {
            "from_index": item_index_by_id[suggestion.from_item_id],
            "to_index": item_index_by_id[suggestion.to_item_id],
            "relationship_type": self._to_display_relationship_type(suggestion.relationship_type),
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

    def _get_relation_items(self) -> list[Item]:
        self._require_advanced_storage()
        return self.storage.load_items_for_relations(include_archived=False)

    def _build_item_index(self, items: list[Item]) -> dict[str, int]:
        return {item.id: index for index, item in enumerate(items, start=1) if item.id}

    def _resolve_item_by_index(self, item_index: int | None, items: list[Item]) -> Item:
        if item_index is None:
            raise ValueError("Item index is required")
        if item_index < 1 or item_index > len(items):
            raise ValueError(f"Item index out of range: {item_index}")
        return items[item_index - 1]

    def _require_advanced_storage(self) -> None:
        supports_relations = getattr(self.storage, "supports_advanced_relations", lambda: False)
        if not supports_relations():
            raise RuntimeError(
                "This command requires PostgreSQL backend because it persists relations in item_dependency and item_merge."
            )

    def _require_item_id(self, item: Item) -> str:
        if not item.id:
            raise RuntimeError("Storage item id is missing")
        return item.id

    def _to_storage_relationship_type(self, relation_type: str) -> str:
        normalized = relation_type.strip().lower()
        if normalized not in CLI_RELATIONSHIP_TYPES:
            supported = ", ".join(sorted(CLI_RELATIONSHIP_TYPES))
            raise ValueError(f"Unsupported relation type: {relation_type}. Supported: {supported}")
        return CLI_RELATIONSHIP_TYPES[normalized]

    def _to_display_relationship_type(self, relation_type: str) -> str:
        return DISPLAY_RELATIONSHIP_TYPES.get(relation_type, relation_type)
