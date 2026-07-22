"""Telegram bot handler for ADHD Assistant.

This module handles Telegram updates and routes them to appropriate services.
It follows the same pattern as the CLI layer: parse input → call services → format output.

Architecture:
    Telegram Update
      ▼ (parsed by TelegramHandler)
    Use Case Services (CaptureService, ListService, RelationService, MergeService)
      ▼ (business logic)
    Domain Models (Item, Relation, etc.)
      ▼ (storage via Storage interface)
    JSON or PostgreSQL Backend
      ▼ (persistence)
    TelegramFormatter
      ▼ (Telegram-specific formatting)
    Telegram Message

Key design:
- Handler NEVER imports JsonStorage or PostgresStorage directly
- Handler ONLY imports Storage interface and services
- All business logic delegated to services
- Handler focuses on: parsing, routing, formatting
- Storage is injected via constructor (Dependency Injection pattern)

Args:
    storage: Storage backend instance (JSON or PostgreSQL)
    project_name: Project name for item grouping (default: "Inbox")
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from models.item import Item, ItemType, ItemStatus
from core.exceptions import (
    StorageError,
    StorageError,
    StorageEntityNotFoundError,
    CliInputError,
)
from interfaces.storage import Storage
from services.item_service_registry import ItemServiceRegistry
from telegram_bot.telegram_formatter import TelegramFormatter

logger = logging.getLogger(__name__)


class TelegramHandler:
    """Handles Telegram updates and routes to services.

    This handler:
    1. Parses Telegram commands and messages
    2. Calls appropriate services (no direct storage access)
    3. Formats responses for Telegram
    4. Handles errors gracefully

    Never touches JsonStorage or PostgresStorage directly.
    All operations go through Storage interface via services.
    Storage is injected via constructor for proper dependency management.

    Args:
        storage: Storage backend instance (must implement Storage interface)
        project_name: Project name for item grouping (default: "Inbox")
    """

    def __init__(self, storage: Storage, project_name: str = "Inbox"):
        """Initialize Telegram handler with injected storage.

        Args:
            storage: Storage backend instance (must implement Storage interface)
            project_name: Project name for item grouping (default: "Inbox")
        """
        self.project_name = project_name
        self.storage = storage
        self.services = ItemServiceRegistry(self.storage)
        self.formatter = TelegramFormatter()

    # ========================================================================
    # COMMAND HANDLERS
    # ========================================================================

    def handle_task_command(self, text: str) -> str:
        """Handle task command (text only)."""
        try:
            item = Item(type=ItemType.TASK, text=text, created_at=datetime.now())
            self.services.add_item("task", text, datetime.now())
            return self.formatter.success(f"Task created: {item.text}", item)
        except ValueError as e:
            return self.formatter.error(str(e))

    def handle_note_command(self, text: str) -> str:
        """Handle note command (text only)."""
        try:
            item = Item(type=ItemType.NOTE, text=text, created_at=datetime.now())
            self.services.add_item("note", text, datetime.now())
            return self.formatter.success(f"Note created: {item.text}", item)
        except ValueError as e:
            return self.formatter.error(str(e))

    def handle_idea_command(self, text: str) -> str:
        """Handle idea command (text only)."""
        try:
            item = Item(type=ItemType.IDEA, text=text, created_at=datetime.now())
            self.services.add_item("idea", text, datetime.now())
            return self.formatter.success(f"Idea created: {item.text}", item)
        except ValueError as e:
            return self.formatter.error(str(e))

    def handle_capture_command(self, text: str) -> str:
        """Handle capture command (text only)."""
        try:
            item_type = self.services.add_captured_item(
                text=text,
                created_at=datetime.now(),
            )
        except ValueError as e:
            return self.formatter.error(str(e))

        type_icon = {
            "task": "✅",
            "note": "📝",
            "idea": "💡",
        }.get(item_type, "📌")

        item = Item(id="", type=ItemType(item_type), text=text)
        return self.formatter.success(
            f"{type_icon} Captured as {item_type}: {item.text}",
            item=item,
        )

    # ========================================================================
    # RELATION HANDLERS (placeholder for future implementation)
    # ========================================================================

    def handle_relation_command(self, text: str) -> str:
        """Handle relation command (placeholder)."""
        return self.formatter.info("Relation functionality is not yet implemented.")

    # ========================================================================
    # MESSAGE HANDLERS
    # ========================================================================

    def handle_message(self, text: str) -> Optional[str]:
        """Handle regular message (not a command).

        Route to appropriate handler based on content analysis.

        Args:
            text: User message

        Returns:
            Response or None if should be ignored
        """
        if not text or not text.strip():
            return None

        # Treat regular messages as captures (auto-detect type)
        return self.handle_capture_command(text)

    # ========================================================================
    # LIST & CLEAR HANDLERS
    # ========================================================================

    def handle_list_command(self, list_type: Optional[str] = None) -> str:
        """Handle /list command."""
        # Normalize the input: treat None or empty string as request for all items
        if not list_type:
            service_list_type = ""
        else:
            # Validate the list_type by trying to convert to ItemType
            try:
                item_type_enum = ItemType(list_type.lower())
            except ValueError:
                return self.formatter.error(
                    f"Unknown item type: {list_type}. Use: task, note, idea"
                )
            service_list_type = item_type_enum.value  # which is the same as list_type.lower()

        items_tuples = self.services.list_items(service_list_type)
        items = [item for _, item in items_tuples]
        return self.formatter.list_items(items)

    def handle_clear_command(self) -> str:
        """Handle /clear command."""
        self.services.clear_items()
        return self.formatter.success("All items cleared")

    # ========================================================================
    # ERROR HANDLING
    # ========================================================================

    def handle_start_command(self) -> str:
        """Handle /start command."""
        return self.formatter.welcome_text()

    def handle_help_command(self) -> str:
        """Handle /help command."""
        return self.formatter.help_text()

    def handle_error(self, error: Exception) -> str:
        """Handle unexpected errors gracefully.

        Args:
            error: Exception that occurred

        Returns:
            User-friendly error message for Telegram
        """
        logger.exception("Unexpected error in Telegram handler", exc_info=True)

        if isinstance(error, StorageError):
            return self.formatter.error(
                "Storage error. Please try again later."
            )
        elif isinstance(error, CliInputError):
            return self.formatter.error(f"Invalid input: {str(error)}")
        else:
            return self.formatter.error(
                "Something went wrong. Please try again later."
            )