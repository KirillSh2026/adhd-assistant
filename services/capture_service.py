"""Capture service: item creation and capture from text/dictation."""

from datetime import datetime

from core.exceptions import CliInputError
from interfaces.storage import Storage
from models.item import Item
from services.item_type_classifier import ItemTypeClassifier, SUPPORTED_ITEM_TYPES


class CaptureService:
    """Handles item capture, creation, and bulk clearing."""

    def __init__(
        self,
        storage: Storage,
        classifier: ItemTypeClassifier | None = None,
    ):
        self.storage = storage
        self.classifier = classifier or ItemTypeClassifier()

    def add_item(self, note_type: str, text: str, created_at: datetime) -> None:
        """Add item of specified type."""
        if note_type not in SUPPORTED_ITEM_TYPES:
            raise CliInputError(f"Unsupported item type: {note_type}")
        item = Item.from_input(note_type=note_type, text=text, created_at=created_at)
        self.storage.add_item(item)

    def add_captured_item(self, text: str, created_at: datetime, note_type: str | None = None) -> str:
        """Add item with auto-classification if type not specified."""
        resolved_type = note_type or self.classifier.classify(text)
        self.add_item(note_type=resolved_type, text=text, created_at=created_at)
        return resolved_type

    def clear_items(self) -> None:
        """Clear all items from storage."""
        self.storage.clear_items()
