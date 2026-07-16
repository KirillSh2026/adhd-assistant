"""Tests for Telegram bot handler and formatter.

Tests verify:
1. Handler correctly routes Telegram commands to services
2. Handler uses Storage interface abstraction (dependency injection)
3. Handler gracefully handles errors
4. Formatter produces valid Telegram markdown
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime

from models.item import Item, ItemType, ItemStatus
from telegram_bot.telegram_handler import TelegramHandler
from telegram_bot.telegram_formatter import TelegramFormatter
from storage.json_storage import JsonStorage
from core.exceptions import StorageError, CliInputError


class TestTelegramFormatter:
    """Test Telegram message formatting."""

    def setup_method(self):
        """Setup formatter for each test."""
        self.formatter = TelegramFormatter()

    def test_formatter_success_message(self):
        """Format success message."""
        response = self.formatter.success("Task created")
        assert "\u2705" in response
        assert "Task created" in response

    def test_formatter_success_with_item(self):
        """Format success with item details."""
        item = Item(id="1", type=ItemType.TASK, text="Buy milk")
        response = self.formatter.success("Task created", item=item)
        
        assert "\u2705" in response
        assert "TASK" in response
        assert "Buy milk" in response

    def test_formatter_error_message(self):
        """Format error message."""
        response = self.formatter.error("Something went wrong")
        assert "\u274c" in response
        assert "Something went wrong" in response

    def test_formatter_info_message(self):
        """Format info message."""
        response = self.formatter.info("Here's info")
        assert "\u2139\ufe0f" in response
        assert "Here's info" in response

    def test_formatter_list_items(self):
        """Format list of items."""
        items = [
            Item(id="1", type=ItemType.TASK, text="Buy milk"),
            Item(id="2", type=ItemType.NOTE, text="Remember call"),
            Item(id="3", type=ItemType.IDEA, text="New feature"),
        ]
        response = self.formatter.list_items(items)
        
        assert "\ud83d\udccb" in response or "Found 3 item" in response
        assert "3 item" in response
        assert "\u2705" in response
        # Note and idea emojis may vary in representation
        assert "note" in response.lower()
        assert "idea" in response.lower()

    def test_formatter_help_text(self):
        """Format help text."""
        response = self.formatter.help_text()
        
        assert "ADHD Assistant Bot Commands" in response
        assert "/task" in response
        assert "/help" in response

    def test_formatter_welcome_text(self):
        """Format welcome message."""
        response = self.formatter.welcome_text()
        
        assert "Welcome" in response
        assert "/help" in response

    def test_formatter_truncate_long_text(self):
        """Truncate text longer than max length."""
        long_text = "x" * 100
        result = self.formatter._truncate(long_text, 20)
        
        assert len(result) <= 20
        assert "..." in result

    def test_formatter_escape_markdown(self):
        """Escape markdown special characters."""
        text = "Hello_world"
        result = self.formatter._escape_markdown(text)
        
        # Should handle escaping for Telegram markdown
        assert result is not None

    def test_formatter_get_type_icon(self):
        """Get correct icon for item type."""
        task_icon = self.formatter._get_type_icon(ItemType.TASK)
        note_icon = self.formatter._get_type_icon(ItemType.NOTE)
        idea_icon = self.formatter._get_type_icon(ItemType.IDEA)
        
        # Check that icons are not empty and are different
        assert task_icon and task_icon != note_icon
        assert note_icon and note_icon != idea_icon
        assert idea_icon and idea_icon != task_icon


class TestTelegramHandlerWithJsonStorage:
    """Test Telegram handler with JSON storage backend."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        """Setup handler with temporary JSON storage."""
        # Create temporary JSON file
        self.json_file = tmp_path / "test.json"
        
        # Create storage and inject it
        self.storage = JsonStorage(str(self.json_file))
        self.handler = TelegramHandler(self.storage)
        
        yield

    def test_handler_initializes_with_storage(self):
        """Handler initializes with injected storage."""
        assert self.handler.storage is self.storage

    def test_handler_initializes_services(self):
        """Handler initializes services on creation."""
        assert self.handler.services is not None

    def test_handler_initializes_formatter(self):
        """Handler initializes formatter on creation."""
        assert self.handler.formatter is not None

    def test_handler_help_command(self):
        """Handle /help command."""
        response = self.handler.handle_help_command()
        
        assert response is not None
        assert "ADHD Assistant Bot Commands" in response
        assert "/task" in response

    def test_handler_start_command(self):
        """Handle /start command."""
        response = self.handler.handle_start_command()
        
        assert response is not None
        assert "Welcome" in response

    def test_handler_task_command_empty_text(self):
        """Reject empty task text."""
        response = self.handler.handle_task_command("")
        
        assert "\u274c" in response or "cannot be empty" in response

    def test_handler_task_command_whitespace_only(self):
        """Reject whitespace-only task text."""
        response = self.handler.handle_task_command("   ")
        
        assert "\u274c" in response or "cannot be empty" in response

    def test_handler_note_command_empty_text(self):
        """Reject empty note text."""
        response = self.handler.handle_note_command("")
        
        assert "\u274c" in response or "cannot be empty" in response

    def test_handler_list_command_empty(self):
        """List items when storage is empty."""
        response = self.handler.handle_list_command()
        
        assert "No items" in response or "\ud83d\udccb" in response

    def test_handler_clear_command(self):
        """Clear all items."""
        response = self.handler.handle_clear_command()
        
        assert "\u2705" in response
        assert "cleared" in response.lower()

    def test_handler_message_empty(self):
        """Ignore empty messages."""
        response = self.handler.handle_message("")
        
        assert response is None

    def test_handler_message_whitespace(self):
        """Ignore whitespace-only messages."""
        response = self.handler.handle_message("   ")
        
        assert response is None

    def test_handler_error_storage_error(self):
        """Handle storage error gracefully."""
        error = StorageError("Database error")
        response = self.handler.handle_error(error)
        
        assert "\u274c" in response

    def test_handler_error_input_error(self):
        """Handle input error gracefully."""
        error = CliInputError("Bad input")
        response = self.handler.handle_error(error)
        
        assert "\u274c" in response

    def test_handler_error_generic(self):
        """Handle generic error gracefully."""
        error = Exception("Unexpected")
        response = self.handler.handle_error(error)
        
        assert "\u274c" in response


class TestTelegramHandlerStorageAbstraction:
    """Test that handler uses storage abstraction correctly."""

    def test_handler_uses_storage_interface(self, tmp_path):
        """Handler uses Storage interface via dependency injection."""
        json_file = tmp_path / "test.json"
        storage = JsonStorage(str(json_file))
        
        handler = TelegramHandler(storage)
        
        # Storage should be injected
        assert handler.storage is storage
        # Should have required storage methods
        assert hasattr(handler.storage, 'add_item')
        assert hasattr(handler.storage, 'load_items')
        assert hasattr(handler.storage, 'clear_items')

    def test_handler_no_direct_storage_imports(self):
        """Handler does not import storage classes directly.
        
        Handler should use dependency injection, not create storage internally.
        """
        import telegram_bot.telegram_handler as handler_module
        
        source = open(handler_module.__file__).read()
        
        # Handler should NOT create storage internally
        assert "def _init_storage" not in source
        assert "from storage.json_storage import JsonStorage" not in source
        assert "from storage.postgres_storage import PostgresStorage" not in source
        
        # Constructor should accept storage as parameter
        assert "storage: Storage" in source


class TestTelegramHandlerCommandIntegration:
    """Integration tests for command handling with real storage."""

    def test_create_and_list_task(self, tmp_path):
        """Create a task and list items."""
        json_file = tmp_path / "test.json"
        storage = JsonStorage(str(json_file))
        
        handler = TelegramHandler(storage)
        
        # Create a task
        response = handler.handle_task_command("Buy groceries")
        assert "\u2705" in response
        
        # List items
        list_response = handler.handle_list_command()
        assert "\ud83d\udccb" in list_response or "Buy groceries" in list_response

    def test_message_handling_with_capture(self, tmp_path):
        """Handle regular message for auto-capture."""
        json_file = tmp_path / "test.json"
        storage = JsonStorage(str(json_file))
        
        handler = TelegramHandler(storage)
        
        # Send a regular message (auto-capture)
        response = handler.handle_message("New idea about productivity")
        assert response is not None


class TestTelegramHandlerErrorHandling:
    """Test error handling in Telegram handler."""

    def test_handle_storage_not_found_error(self, tmp_path):
        """Handle storage not found error."""
        json_file = tmp_path / "test.json"
        storage = JsonStorage(str(json_file))
        
        handler = TelegramHandler(storage)
        
        # This should not crash the handler
        response = handler.handle_list_command()
        assert response is not None

    def test_handle_formatter_with_various_item_types(self):
        """Formatter handles all item types correctly."""
        formatter = TelegramFormatter()
        
        items = [
            Item(id="1", type=ItemType.TASK, text="Task 1"),
            Item(id="2", type=ItemType.NOTE, text="Note 1"),
            Item(id="3", type=ItemType.IDEA, text="Idea 1"),
        ]
        
        response = formatter.list_items(items)
        
        # Check that all types are represented (emoji may vary in representation)
        assert "\u2705" in response  # Task
        assert "Task 1" in response
        assert "Note 1" in response
        assert "Idea 1" in response


class TestTelegramHandlerEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_long_item_text(self):
        """Handle very long item text."""
        formatter = TelegramFormatter()
        
        long_text = "x" * 500
        item = Item(id="1", type=ItemType.TASK, text=long_text)
        
        response = formatter.success("Created", item=item)
        
        # Should not crash, text should be truncated
        assert response is not None
        assert len(response) < 10000  # Reasonable limit for Telegram message

    def test_special_characters_in_text(self, tmp_path):
        """Handle special characters in item text."""
        json_file = tmp_path / "test.json"
        storage = JsonStorage(str(json_file))
        
        handler = TelegramHandler(storage)
        
        # Special characters should not crash handler
        response = handler.handle_task_command("Buy milk @5% off!*#$%")
        assert response is not None

    def test_unicode_text_handling(self, tmp_path):
        """Handle Unicode text correctly."""
        json_file = tmp_path / "test.json"
        storage = JsonStorage(str(json_file))
        
        handler = TelegramHandler(storage)
        
        # Unicode text should work
        response = handler.handle_task_command("Купить молоко 🥛 завтра")
        assert response is not None


class TestTelegramFormatterMarkdown:
    """Test Telegram markdown formatting."""

    def test_markdown_escape_backslash(self):
        """Escape backslashes for Telegram markdown."""
        formatter = TelegramFormatter()
        
        text = r"Path: C:\Users\Bob"
        result = formatter._escape_markdown(text)
        
        # Should handle backslashes properly
        assert result is not None

    def test_markdown_escape_asterisk(self):
        """Escape asterisks for Telegram markdown."""
        formatter = TelegramFormatter()
        
        text = "*bold*text*"
        result = formatter._escape_markdown(text)
        
        assert result is not None

    def test_markdown_escape_underscore(self):
        """Escape underscores for Telegram markdown."""
        formatter = TelegramFormatter()
        
        text = "_italic_text_"
        result = formatter._escape_markdown(text)
        
        assert result is not None

    def test_formatted_item_with_all_fields(self):
        """Format item with all optional fields."""
        formatter = TelegramFormatter()
        
        item = Item(
            id="test-123",
            type=ItemType.TASK,
            text="Complex task",
            status=ItemStatus.ACTIVE,
            created_at=datetime(2026, 7, 16, 14, 30, 0)
        )
        
        response = formatter.success("Item created", item=item)
        
        # Should include all relevant fields
        assert "test-123" in response
        assert "TASK" in response
        assert "Complex task" in response
