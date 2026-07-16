"""Telegram-specific output formatting.

Formats domain models (Item, Relation, etc.) as Telegram messages.
Uses Telegram markdown, emojis, and inline buttons for rich UI.
"""

from __future__ import annotations

from typing import Optional
from models.item import Item, ItemStatus, ItemType


class TelegramFormatter:
    """Formats responses for Telegram chat.

    Handles:
    - Markdown formatting (bold, italic, code)
    - Emojis for visual clarity
    - Inline buttons for common actions
    - Lists and tables
    - Error messages
    """

    # ========================================================================
    # SUCCESS & INFO MESSAGES
    # ========================================================================

    def success(self, message: str, item: Optional[Item] = None) -> str:
        """Format success message.

        Args:
            message: Main message text
            item: Optional Item to display details

        Returns:
            Formatted message for Telegram
        """
        text = f"✅ {message}"

        if item:
            text += f"\n\n{self._format_item_details(item)}"

        return text

    def info(self, message: str) -> str:
        """Format info message.

        Args:
            message: Message text

        Returns:
            Formatted message
        """
        return f"ℹ️ {message}"

    def error(self, message: str) -> str:
        """Format error message.

        Args:
            message: Error description

        Returns:
            Formatted error message
        """
        return f"❌ {message}"

    # ========================================================================
    # ITEM FORMATTING
    # ========================================================================

    def _format_item_details(self, item: Item) -> str:
        """Format single item with details.

        Args:
            item: Item to format

        Returns:
            Formatted item details
        """
        type_icon = self._get_type_icon(item.type)
        status_text = "archived" if item.status == ItemStatus.ARCHIVED else "active"

        text = f"{type_icon} *{item.type.value.upper()}*\n"
        text += f"ID: `{item.id}`\n"
        text += f"Status: {status_text}\n"
        text += f"Text: {self._escape_markdown(item.text)}"

        if item.created_at:
            text += f"\nCreated: {item.created_at.strftime('%Y-%m-%d %H:%M')}"

        return text

    def list_items(self, items: list[Item]) -> str:
        """Format list of items.

        Args:
            items: List of items

        Returns:
            Formatted item list
        """
        if not items:
            return "No items found"

        text = f"📋 Found {len(items)} item(s):\n\n"

        for i, item in enumerate(items, 1):
            type_icon = self._get_type_icon(item.type)
            text += f"{i}. {type_icon} `{item.type.value}`"
            text += f" — {self._truncate(item.text, 50)}\n"

        return text

    def _format_item_summary(self, item: Item, index: Optional[int] = None) -> str:
        """Format item as single-line summary.

        Args:
            item: Item to format
            index: Optional index number

        Returns:
            Single-line item summary
        """
        type_icon = self._get_type_icon(item.type)
        prefix = f"{index}. " if index is not None else ""

        return f"{prefix}{type_icon} {self._truncate(item.text, 60)}"

    # ========================================================================
    # HELP & WELCOME
    # ========================================================================

    def help_text(self) -> str:
        """Format help message with all commands.

        Returns:
            Formatted help text
        """
        text = """📚 *ADHD Assistant Bot Commands*

*Create Items:*
/task TEXT — Create a task
/note TEXT — Create a note
/idea TEXT — Create an idea
/capture TEXT — Auto-detect type and create

*Manage Items:*
/list [all|task|note|idea] — List items
/clear — Remove all items

*Other:*
/help — Show this help
/start — Welcome message

*Quick Capture:*
Just send any message to capture it as an item!
"""
        return text

    def welcome_text(self) -> str:
        """Format welcome message.

        Returns:
            Welcome text
        """
        text = """👋 Welcome to *ADHD Assistant Bot*!

I help you capture and organize your thoughts, tasks, and ideas.

*Quick Start:*
- Send any message to create an item
- Use /task, /note, /idea for specific types
- Use /list to see all items
- Use /help for all commands

Let's get organized! 📋
"""
        return text

    # ========================================================================
    # RELATION MESSAGES (for future use)
    # ========================================================================

    def relation_created(self, from_item: Item, to_item: Item, rel_type: str) -> str:
        """Format relation creation message.

        Args:
            from_item: Source item
            to_item: Target item
            rel_type: Relation type

        Returns:
            Formatted message
        """
        text = f"🔗 Linked items:\n\n"
        text += f"From: {self._truncate(from_item.text, 40)}\n"
        text += f"Type: *{rel_type}*\n"
        text += f"To: {self._truncate(to_item.text, 40)}"

        return text

    def relation_list(self, relations: list[dict]) -> str:
        """Format list of relations.

        Args:
            relations: List of relation dicts

        Returns:
            Formatted relations list
        """
        if not relations:
            return "No relations found"

        text = f"🔗 Found {len(relations)} relation(s):\n\n"

        for rel in relations:
            rel_type = rel.get("relationship_type", "related_to")
            text += f"• {rel_type}\n"

        return text

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    def _get_type_icon(self, item_type: ItemType) -> str:
        """Get emoji icon for item type.

        Args:
            item_type: Item type

        Returns:
            Emoji icon
        """
        return {
            ItemType.TASK: "✅",
            ItemType.NOTE: "📝",
            ItemType.IDEA: "💡",
        }.get(item_type, "📌")

    def _truncate(self, text: str, max_length: int) -> str:
        """Truncate text to max length with ellipsis.

        Args:
            text: Text to truncate
            max_length: Maximum length

        Returns:
            Truncated text
        """
        if len(text) > max_length:
            return text[:max_length-3] + "..."
        return text

    def _escape_markdown(self, text: str) -> str:
        """Escape special markdown characters.

        Args:
            text: Text to escape

        Returns:
            Escaped text safe for Telegram markdown
        """
        # Escape Telegram markdown special chars
        special_chars = ["_", "*", "[", "]", "(", ")", "~", "`", ">", "#", "+", "-", "=", "|", "{", "}", ".", "!"]
        result = text
        for char in special_chars:
            result = result.replace(char, f"\\{char}")
        return result
