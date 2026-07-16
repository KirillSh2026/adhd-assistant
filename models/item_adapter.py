"""Adapter for converting between Item domain model and legacy JSON format."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from models.item import Item, ItemStatus, ItemType


class ItemAdapter:
    """Converts between domain Item and legacy JSON/API formats."""

    @staticmethod
    def from_legacy_dict(payload: dict) -> Item:
        """Convert legacy dict format to domain Item.

        Legacy format:
            {
                "type": "task",
                "text": "Buy milk",
                "datetime": "2026-01-01 10:00:00",  # ISO format string or None
                "id": "uuid-string",  # optional
                "status": "active"  # optional
            }
        """
        type_str = str(payload.get("type", "task")).lower()
        type_val = ItemType.TASK
        if type_str in [t.value for t in ItemType]:
            type_val = ItemType(type_str)

        text = str(payload.get("text", "")).strip()

        created_at = None
        if datetime_str := payload.get("datetime"):
            try:
                created_at = datetime.fromisoformat(str(datetime_str))
            except (ValueError, TypeError):
                pass

        item_id = str(payload["id"]) if payload.get("id") else None

        status_str = str(payload.get("status", "active")).lower()
        status_val = ItemStatus.ACTIVE
        if status_str in [s.value for s in ItemStatus]:
            status_val = ItemStatus(status_str)

        return Item(
            type=type_val,
            text=text,
            id=item_id,
            created_at=created_at,
            status=status_val,
        )

    @staticmethod
    def to_legacy_dict(item: Item) -> dict:
        """Convert domain Item to legacy dict format.

        Returns dict with 'type', 'text', and optional 'datetime', 'id', 'status'.
        """
        data: dict[str, Any] = {
            "type": str(item.type),
            "text": item.text,
        }

        if item.created_at:
            data["datetime"] = item.created_at.isoformat()

        if item.id:
            data["id"] = item.id

        if item.status != ItemStatus.ACTIVE:
            data["status"] = str(item.status)

        return data

    @staticmethod
    def to_dict(item: Item) -> dict:
        """Convert Item to API dict format (same as legacy for now).

        Can be extended later for API-specific formatting.
        """
        return ItemAdapter.to_legacy_dict(item)
