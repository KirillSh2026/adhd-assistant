"""Telegram bot layer for ADHD Assistant.

This package provides Telegram bot integration that:
1. Parses Telegram commands and messages
2. Routes to existing services (NO direct storage access)
3. Formats responses for Telegram

Architecture follows the same principle as CLI layer:
- Handler parses input
- Services execute business logic
- Formatter outputs result

Components:
- telegram_handler: Main handler for Telegram updates
- telegram_formatter: Telegram-specific formatting
"""

from .telegram_handler import TelegramHandler
from .telegram_formatter import TelegramFormatter

__all__ = ["TelegramHandler", "TelegramFormatter"]
