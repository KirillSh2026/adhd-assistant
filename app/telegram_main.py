"""Entry point for ADHD Assistant Telegram bot.

This is the main executable for running the Telegram bot.

Usage:
    python app/telegram_main.py

Environment variables:
    ADHD_TELEGRAM_TOKEN: Telegram bot token (required)
    ADHD_STORAGE_BACKEND: json or postgres (default: json)
    ADHD_NOTES_PATH: Path to JSON storage (default: data/notes.json)
    DATABASE_URL: PostgreSQL connection string (if using postgres backend)
    ADHD_DICTATE_LANGUAGE: Language for speech-to-text (default: ru)

Example:
    export ADHD_TELEGRAM_TOKEN=your_token_here
    python app/telegram_main.py

For testing/development:
    ADHD_TELEGRAM_TOKEN=test_token python app/telegram_main.py --dry-run
"""

import logging
import os
import sys
from typing import Optional

# Try to import telegram library
try:
    from telegram import Update
    from telegram.ext import (
        Application,
        CommandHandler,
        MessageHandler,
        filters,
        ContextTypes,
    )
except ImportError:
    print("ERROR: python-telegram-bot library not found.")
    print("Install it with: pip install python-telegram-bot")
    sys.exit(1)

from config.settings import get_settings
from core.exceptions import ConfigurationError, StorageError
from interfaces.storage import Storage
from storage.json_storage import JsonStorage
from telegram_bot.telegram_handler import TelegramHandler

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def get_storage() -> Storage:
    """Initialize and return the configured storage backend.
    
    Raises:
        ConfigurationError: If backend configuration is invalid
        StorageError: If storage initialization fails
    """
    settings = get_settings()
    backend = settings.adhd_storage_backend
    notes_path = settings.adhd_notes_path
    database_url = settings.database_url.strip()

    if backend == "postgres":
        if not database_url:
            raise ConfigurationError("DATABASE_URL is required when ADHD_STORAGE_BACKEND=postgres")
        from storage.postgres_storage import PostgresStorage
        return PostgresStorage(dsn=database_url)
    else:
        try:
            return JsonStorage(path=notes_path)
        except Exception as e:
            raise StorageError(
                f"Failed to initialize JSON storage at {notes_path}: {e}\n"
                f"Make sure the directory is writable and valid."
            ) from e


class TelegramBotApp:
    """Telegram bot application wrapper.

    Manages bot lifecycle and message routing.
    """

    def __init__(self, token: str, storage: Storage, project_name: str = "Inbox"):
        """Initialize bot application.

        Args:
            token: Telegram bot token
            storage: Storage backend instance
            project_name: Project name for item grouping
        """
        self.token = token
        self.storage = storage
        self.handler = TelegramHandler(storage, project_name)
        self.app = None

    async def start_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        response = self.handler.handle_start_command()
        await update.message.reply_text(response, parse_mode="Markdown")

    async def help_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        response = self.handler.handle_help_command()
        await update.message.reply_text(response, parse_mode="Markdown")

    async def task_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /task command."""
        text = " ".join(context.args) if context.args else ""
        response = self.handler.handle_task_command(text)
        await update.message.reply_text(response, parse_mode="Markdown")

    async def note_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /note command."""
        text = " ".join(context.args) if context.args else ""
        response = self.handler.handle_note_command(text)
        await update.message.reply_text(response, parse_mode="Markdown")

    async def idea_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /idea command."""
        text = " ".join(context.args) if context.args else ""
        response = self.handler.handle_idea_command(text)
        await update.message.reply_text(response, parse_mode="Markdown")

    async def capture_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /capture command."""
        text = " ".join(context.args) if context.args else ""
        response = self.handler.handle_capture_command(text)
        await update.message.reply_text(response, parse_mode="Markdown")

    async def list_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /list command."""
        list_type = context.args[0] if context.args else None
        response = self.handler.handle_list_command(list_type)
        await update.message.reply_text(response, parse_mode="Markdown")

    async def clear_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /clear command (with confirmation)."""
        response = self.handler.handle_clear_command()
        await update.message.reply_text(response, parse_mode="Markdown")

    async def message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle regular messages."""
        text = update.message.text
        response = self.handler.handle_message(text)

        if response:
            await update.message.reply_text(response, parse_mode="Markdown")

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle errors."""
        logger.error(f"Update {update} caused error {context.error}")

        if update and update.message:
            response = self.handler.handle_error(context.error)
            await update.message.reply_text(response, parse_mode="Markdown")

    async def build(self) -> Application:
        """Build and configure bot application.

        Returns:
            Configured Application instance
        """
        self.app = Application.builder().token(self.token).build()

        # Command handlers
        self.app.add_handler(CommandHandler("start", self.start_handler))
        self.app.add_handler(CommandHandler("help", self.help_handler))
        self.app.add_handler(CommandHandler("task", self.task_handler))
        self.app.add_handler(CommandHandler("note", self.note_handler))
        self.app.add_handler(CommandHandler("idea", self.idea_handler))
        self.app.add_handler(CommandHandler("capture", self.capture_handler))
        self.app.add_handler(CommandHandler("list", self.list_handler))
        self.app.add_handler(CommandHandler("clear", self.clear_handler))

        # Message handler (for text messages that aren't commands)
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.message_handler))

        # Error handler
        self.app.add_error_handler(self.error_handler)

        return self.app

    async def run_polling(self) -> None:
        """Run bot with polling (for development/local testing).

        Requires ADHD_TELEGRAM_TOKEN environment variable.
        """
        logger.info("Starting bot with polling...")
        app = await self.build()

        await app.initialize()
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)

        logger.info("Bot started. Press Ctrl+C to stop.")
        try:
            await app.updater.idle()
        except KeyboardInterrupt:
            logger.info("Bot stopped")
        finally:
            await app.updater.stop()
            await app.stop()
            await app.shutdown()

    async def run_webhook(self, webhook_url: str, port: int = 8080) -> None:
        """Run bot with webhook (for production).

        Args:
            webhook_url: URL where Telegram will send updates
            port: Local port to listen on
        """
        logger.info(f"Starting bot with webhook: {webhook_url}")
        app = await self.build()

        await app.initialize()
        await app.start()
        await app.updater.start_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=self.token,
            webhook_url=f"{webhook_url}/{self.token}",
        )

        logger.info(f"Bot started on port {port}")


async def main() -> None:
    """Main entry point for Telegram bot."""
    settings = get_settings()

    # Get bot token
    token = os.environ.get("ADHD_TELEGRAM_TOKEN")
    if not token:
        logger.error(
            "ERROR: ADHD_TELEGRAM_TOKEN not set. "
            "Set it with: export ADHD_TELEGRAM_TOKEN=your_token_here"
        )
        sys.exit(1)

    # Initialize storage
    storage = get_storage()

    # Create bot app with injected storage
    bot_app = TelegramBotApp(token, storage)

    # Run with polling (development) or webhook (production)
    webhook_url = os.environ.get("ADHD_TELEGRAM_WEBHOOK_URL")
    if webhook_url:
        await bot_app.run_webhook(webhook_url)
    else:
        await bot_app.run_polling()


if __name__ == "__main__":
    import asyncio

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot interrupted")
        sys.exit(0)
