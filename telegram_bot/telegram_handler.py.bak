"""Telegram bot handler for ADHD Assistant.

This module handles Telegram updates and routes them to appropriate services.
It follows the same pattern as the CLI layer: parse input \u2192 call services \u2192 format output.

Architecture:
    Telegram Update
      \u2193 (parsed by TelegramHandler)
    Use Case Services (CaptureService, ListService, RelationService, MergeService)
      \u2193 (business logic)
    Domain Models (Item, Relation, etc.)
      \u2193 (storage via Storage interface)
    JSON or PostgreSQL Backend
      \u2193 (persistence)
    TelegramFormatter
      \u2193 (Telegram-specific formatting)
    Telegram Message

Key design:
- Handler NEVER imports JsonStorage or PostgresStorage directly
- Handler ONLY imports Storage interface and services
- All business logic delegated to services
- Handler focuses on: parsing, routing, formatting
- Storage is injected via constructor (Dependency Injection pattern)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from models.item import Item, ItemType, ItemStatus
from core.exceptions import (
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
        storage: Storage backend instance (JSON or PostgreSQL)
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
        """Handle /task command: create a task item.

        Args:
            text: Task description

        Returns:
            Formatted response for Telegram
        """
        try:
            if not text or not text.strip():
                return self.formatter.error("Task text cannot be empty")

            self.services.capture.add_item(
                note_type="task",
                text=text,
                created_at=datetime.now(),
            )
            
            item = Item(id="", type=ItemType.TASK, text=text)

            return self.formatter.success(
                f"\u2705 Task created: {item.text}",
                item=item,
            )

        except (StorageError, CliInputError) as e:
            logger.exception("Error creating task")
            return self.formatter.error(f"Failed to create task: {str(e)}")

    def handle_note_command(self, text: str) -> str:
        """Handle /note command: create a note item.

        Args:
            text: Note content

        Returns:
            Formatted response for Telegram
        """
        try:
            if not text or not text.strip():
                return self.formatter.error("Note text cannot be empty")

            self.services.capture.add_item(
                note_type="note",
                text=text,
                created_at=datetime.now(),
            )

            item = Item(id="", type=ItemType.NOTE, text=text)

            return self.formatter.success(
                f"\ud83d\udcdd Note created: {item.text}",
                item=item,
            )

        except (StorageError, CliInputError) as e:
            logger.exception("Error creating note")
            return self.formatter.error(f"Failed to create note: {str(e)}")

    def handle_idea_command(self, text: str) -> str:
        """Handle /idea command: create an idea item.

        Args:
            text: Idea description

        Returns:
            Formatted response for Telegram
        """
        try:
            if not text or not text.strip():
                return self.formatter.error("Idea text cannot be empty")

            self.services.capture.add_item(
                note_type="idea",
                text=text,
                created_at=datetime.now(),
            )

            item = Item(id="", type=ItemType.IDEA, text=text)

            return self.formatter.success(
                f"\ud83d\udca1 Idea created: {item.text}",
                item=item,
            )

        except (StorageError, CliInputError) as e:
            logger.exception("Error creating idea")
            return self.formatter.error(f"Failed to create idea: {str(e)}")

    def handle_capture_command(self, text: str) -> str:
        """Handle /capture command: auto-detect type and create item.

        Args:
            text: Item text (type auto-detected)

        Returns:
            Formatted response for Telegram
        """
        try:
            if not text or not text.strip():
                return self.formatter.error("Text cannot be empty")

            item_type = self.services.capture.add_captured_item(
                text=text,
                created_at=datetime.now(),
            )

            type_icon = {
                "task": "\u2705",
                "note": "\ud83d\udcdd",
                "idea": "\ud83d\udca1",
            }.get(item_type, "\ud83d\udccc")

            item = Item(id="", type=ItemType(item_type), text=text)

            return self.formatter.success(
                f"{type_icon} Captured as {item_type}: {item.text}",
                item=item,
            )

        except (StorageError, CliInputError) as e:
            logger.exception("Error capturing item")
            return self.formatter.error(f"Failed to capture: {str(e)}")

    def handle_list_command(self, list_type: Optional[str] = None) -> str:
        """Handle /list command: list items by type.

        Args:
            list_type: Item type to filter (task/note/idea/all)

        Returns:
            Formatted response for Telegram
        """
        try:
            items_with_indices = self.services.list.list_items(list_type or "all")

            if not items_with_indices:
                return self.formatter.info("No items found")

            # Extract just the Item objects from (index, item) tuples
            items = [item for _, item in items_with_indices]
            
            return self.formatter.list_items(items)

        except (StorageError, CliInputError) as e:
            logger.exception("Error listing items")
            return self.formatter.error(f"Failed to list items: {str(e)}")

    def handle_clear_command(self) -> str:
        """Handle /clear command: remove all items (with confirmation).

        Returns:
            Formatted response for Telegram
        """
        try:
            self.services.capture.clear_items()
            return self.formatter.success("\ud83d\uddd1\ufe0f All items cleared")

        except StorageError as e:
            logger.exception("Error clearing items")
            return self.formatter.error(f"Failed to clear items: {str(e)}")

    def handle_help_command(self) -> str:
        """Handle /help command: show available commands.

        Returns:
            Formatted help text for Telegram
        """
        return self.formatter.help_text()

    def handle_start_command(self) -> str:
        """Handle /start command: welcome message.

        Returns:
            Welcome text for Telegram
        """
        return self.formatter.welcome_text()

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
    # ERROR HANDLING
    # ========================================================================

    def handle_error(self, error: Exception) -> str:
        """Handle unexpected errors gracefully.

        Args:
            error: Exception that occurred

        Returns:
            User-friendly error message for Telegram
        """
        logger.exception("Unexpected error in Telegram handler", exc_info=error)

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
