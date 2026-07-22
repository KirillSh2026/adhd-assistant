from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from models.item import ItemType, ItemStatus


@dataclass(frozen=True)
class ProjectRecord:
    """Immutable DTO representing a project row."""
    id: str
    name: str


@dataclass(frozen=True)
class ItemRecord:
    """Immutable DTO representing an item row."""
    id: str
    project_id: str
    type: ItemType
    text: str
    # Optional fields that may be present in DB rows but not required for DTO
    created_at: Optional[datetime] = None
    status: Optional[ItemStatus] = None


@dataclass(frozen=True)
class RelationRecord:
    """Immutable DTO representing an item_dependency row."""
    id: str
    from_item_id: str
    to_item_id: str
    relationship_type: str
    # Optional fields
    reason: Optional[str] = None
    is_confirmed: bool = False
    created_at: Optional[datetime] = None


@dataclass(frozen=True)
class MergeRecord:
    """Immutable DTO representing an item_merge row."""
    id: str
    target_item_id: str
    source_item_ids: List[str]
    reason: str
    merged_at: datetime
    # Optional
    source_items_snapshot: Optional[str] = None  # JSON string
