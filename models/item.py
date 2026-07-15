from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Item:
    """Domain item with backward-compatible legacy JSON conversion."""

    type: str
    text: str
    datetime: str | None = None

    @classmethod
    def from_legacy_dict(cls, payload: dict) -> "Item":
        return cls(
            type=str(payload.get("type", "")),
            text=str(payload.get("text", "")),
            datetime=str(payload["datetime"]) if payload.get("datetime") else None,
        )

    @classmethod
    def from_input(cls, note_type: str, text: str, created_at: datetime) -> "Item":
        return cls(
            type=note_type,
            text=text,
            datetime=created_at.strftime("%Y-%m-%d %H:%M:%S"),
        )

    def to_legacy_dict(self) -> dict:
        data = {"type": self.type, "text": self.text}
        if self.datetime:
            data["datetime"] = self.datetime
        return data

    def has_text(self) -> bool:
        return bool(self.text.strip())