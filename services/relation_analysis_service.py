from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import re

from models.item import Item


STOP_WORDS = {
    "and",
    "the",
    "for",
    "with",
    "that",
    "this",
    "into",
    "from",
    "как",
    "для",
    "что",
    "это",
    "или",
    "над",
    "под",
    "после",
    "перед",
    "если",
    "когда",
    "чтобы",
    "тоже",
    "потом",
    "надо",
    "нужно",
}


@dataclass(frozen=True)
class RelationSuggestion:
    from_item_id: str
    to_item_id: str
    relationship_type: str
    score: float
    reason: str


@dataclass(frozen=True)
class ItemCluster:
    member_ids: list[str]
    average_score: float


class RelationAnalysisService:
    duplicate_threshold = 0.78
    related_threshold = 0.42

    def suggest_relations(self, items: list[Item]) -> list[RelationSuggestion]:
        suggestions: list[RelationSuggestion] = []
        scored_edges: set[tuple[str, str, str]] = set()

        for left_index, left_item in enumerate(items):
            if not left_item.id or not left_item.has_text():
                continue

            for right_item in items[left_index + 1 :]:
                if not right_item.id or not right_item.has_text():
                    continue

                similarity = self._similarity(left_item.text, right_item.text)
                if self._is_duplicate_candidate(left_item, right_item, similarity):
                    pair = self._ordered_ids(left_item.id, right_item.id)
                    relation_key = (pair[0], pair[1], "duplicate_of")
                    if relation_key not in scored_edges:
                        suggestions.append(
                            RelationSuggestion(
                                from_item_id=pair[0],
                                to_item_id=pair[1],
                                relationship_type="duplicate_of",
                                score=similarity,
                                reason=f"High textual similarity ({similarity:.2f})",
                            )
                        )
                        scored_edges.add(relation_key)
                    continue

                if self._is_related_candidate(left_item, right_item, similarity):
                    pair = self._ordered_ids(left_item.id, right_item.id)
                    relation_key = (pair[0], pair[1], "relates_to")
                    if relation_key not in scored_edges:
                        shared = sorted(self._shared_tokens(left_item.text, right_item.text))
                        reason = (
                            f"Shared concepts: {', '.join(shared[:4])}"
                            if shared
                            else f"Moderate textual similarity ({similarity:.2f})"
                        )
                        suggestions.append(
                            RelationSuggestion(
                                from_item_id=pair[0],
                                to_item_id=pair[1],
                                relationship_type="relates_to",
                                score=similarity,
                                reason=reason,
                            )
                        )
                        scored_edges.add(relation_key)

        suggestions.sort(key=lambda item: (item.relationship_type != "duplicate_of", -item.score))
        return suggestions

    def build_clusters(self, items: list[Item]) -> list[ItemCluster]:
        suggestions = [
            suggestion
            for suggestion in self.suggest_relations(items)
            if suggestion.relationship_type in {"duplicate_of", "relates_to"}
        ]
        adjacency: dict[str, set[str]] = {}
        edge_scores: dict[tuple[str, str], float] = {}

        for suggestion in suggestions:
            adjacency.setdefault(suggestion.from_item_id, set()).add(suggestion.to_item_id)
            adjacency.setdefault(suggestion.to_item_id, set()).add(suggestion.from_item_id)
            edge_scores[self._ordered_ids(suggestion.from_item_id, suggestion.to_item_id)] = suggestion.score

        visited: set[str] = set()
        clusters: list[ItemCluster] = []
        for item in items:
            if not item.id or item.id in visited or item.id not in adjacency:
                continue

            stack = [item.id]
            members: list[str] = []
            while stack:
                current = stack.pop()
                if current in visited:
                    continue
                visited.add(current)
                members.append(current)
                stack.extend(sorted(adjacency.get(current, set()) - visited))

            if len(members) < 2:
                continue

            member_scores = [
                score
                for pair, score in edge_scores.items()
                if pair[0] in members and pair[1] in members
            ]
            average_score = sum(member_scores) / len(member_scores) if member_scores else 0.0
            clusters.append(ItemCluster(member_ids=sorted(members), average_score=average_score))

        clusters.sort(key=lambda cluster: (-len(cluster.member_ids), -cluster.average_score))
        return clusters

    def _is_duplicate_candidate(self, left_item: Item, right_item: Item, similarity: float) -> bool:
        left_text = self._normalize_text(left_item.text)
        right_text = self._normalize_text(right_item.text)
        if left_text == right_text:
            return True
        if left_item.type != right_item.type:
            return False
        if similarity >= self.duplicate_threshold:
            return True
        shorter, longer = sorted((left_text, right_text), key=len)
        if shorter and shorter in longer and len(shorter) / len(longer) >= 0.82:
            return True
        return False

    def _is_related_candidate(self, left_item: Item, right_item: Item, similarity: float) -> bool:
        shared_tokens = self._shared_tokens(left_item.text, right_item.text)
        if similarity >= self.related_threshold and len(shared_tokens) >= 1:
            return True
        return len(shared_tokens) >= 2

    def _shared_tokens(self, left_text: str, right_text: str) -> set[str]:
        return self._tokenize(left_text).intersection(self._tokenize(right_text))

    def _similarity(self, left_text: str, right_text: str) -> float:
        left_normalized = self._normalize_text(left_text)
        right_normalized = self._normalize_text(right_text)
        if not left_normalized or not right_normalized:
            return 0.0

        sequence_ratio = SequenceMatcher(None, left_normalized, right_normalized).ratio()
        left_tokens = self._tokenize(left_normalized)
        right_tokens = self._tokenize(right_normalized)
        union = left_tokens.union(right_tokens)
        jaccard = len(left_tokens.intersection(right_tokens)) / len(union) if union else 0.0
        return round((sequence_ratio * 0.65) + (jaccard * 0.35), 4)

    def _tokenize(self, text: str) -> set[str]:
        return {
            token
            for token in re.findall(r"[a-zA-Zа-яА-Я0-9_]+", text.lower())
            if len(token) > 2 and token not in STOP_WORDS
        }

    def _normalize_text(self, text: str) -> str:
        return " ".join(text.lower().strip().split())

    def _ordered_ids(self, left_id: str, right_id: str) -> tuple[str, str]:
        return (left_id, right_id) if left_id <= right_id else (right_id, left_id)
