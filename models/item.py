"""Domain model for Items with strong typing and immutability."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ItemType(str, Enum):
    """Item type enumeration for domain model.
    
    Inherits from str for backward compatibility with legacy JSON format,
    but provides full enum type safety in domain code.
    """

    TASK = "task"
    NOTE = "note"
    IDEA = "idea"

    def __str__(self) -> str:
        return self.value


class ItemStatus(str, Enum):
    """Item status enumeration for domain model.
    
    Inherits from str for backward compatibility with legacy JSON format,
    but provides full enum type safety in domain code.
    """

    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Item:
    """Immutable domain item with strong typing and validation.
    
    Attributes:
        type: Item type (task/note/idea).
        text: Non-empty item text (immutable, validated).
        id: Optional unique identifier (assigned by storage).
        created_at: Optional creation timestamp (assigned by storage or CLI).
        status: Item status (default: ACTIVE).
    
    Invariants:
        - text is non-empty and non-whitespace-only (enforced in __post_init__)
        - All enum fields are properly typed (ItemType, ItemStatus)
        - Dataclass is frozen (immutable) for safety
    """

    type: ItemType
    text: str
    id: str | None = None
    created_at: datetime | None = None
    status: ItemStatus = ItemStatus.ACTIVE

    def __post_init__(self) -> None:
        """Validate text after initialization.
        
        Raises:
            ValueError: If text is empty or whitespace-only.
        """
        if not self.text or not self.text.strip():
            raise ValueError("Item text cannot be empty or whitespace-only")

    @property
    def normalized_text(self) -> str:
        """Get text with normalized whitespace (all extra spaces removed)."""
        return " ".join(self.text.split())

    def with_id(self, item_id: str) -> Item:
        """Return new Item with updated ID (immutability pattern).
        
        Args:
            item_id: New ID to assign.
        
        Returns:
            New Item instance with updated ID.
        """
        return Item(
            type=self.type,
            text=self.text,
            id=item_id,
            created_at=self.created_at,
            status=self.status,
        )

    def with_status(self, status: ItemStatus) -> Item:
        """Return new Item with updated status (immutability pattern).
        
        Args:
            status: New status to assign.
        
        Returns:
            New Item instance with updated status.
        """
        return Item(
            type=self.type,
            text=self.text,
            id=self.id,
            created_at=self.created_at,
            status=status,
        )