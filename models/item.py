from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Literal


class ItemType(str, Enum):
    """Item type enumeration for domain model."""

    TASK = "task"
    NOTE = "note"
    IDEA = "idea"

    def __str__(self) -> str:
        return self.value


class ItemStatus(str, Enum):
    """Item status enumeration for domain model."""

    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Item:
    """Immutable domain item with strong typing and validation."""

    type: ItemType
    text: str
    id: str | None = None
    created_at: datetime | None = None
    status: ItemStatus = ItemStatus.ACTIVE

    def __post_init__(self) -> None:
        """Validate and normalize text after initialization."""
        if not self.text or not self.text.strip():
            raise ValueError("Item text cannot be empty or whitespace-only")

    @property
    def normalized_text(self) -> str:
        """Get text with normalized whitespace."""
        return " ".join(self.text.split())

    def has_text(self) -> bool:
        """Check if item has non-empty text."""
        return bool(self.text.strip())

    def with_id(self, item_id: str) -> "Item":
        """Return new Item with updated ID (immutability pattern)."""
        return Item(
            type=self.type,
            text=self.text,
            id=item_id,
            created_at=self.created_at,
            status=self.status,
        )

    def with_status(self, status: ItemStatus) -> "Item":
        """Return new Item with updated status (immutability pattern)."""
        return Item(
            type=self.type,
            text=self.text,
            id=self.id,
            created_at=self.created_at,
            status=status,
        )