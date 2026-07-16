# Telegram Bot Integration for ADHD Assistant

## Overview

The Telegram bot layer provides Telegram integration for ADHD Assistant following the **same architectural principles as the CLI layer**.

**Key Design Principle**: The Telegram bot does NOT know about JSON storage or PostgreSQL storage. It only knows about:
1. Storage interface
2. Use case services (CaptureService, ListService, RelationService, MergeService)
3. Domain models (Item, ItemType, ItemStatus)

This ensures **single domain logic** reusable across all interfaces:
- CLI (command-line)
- **Telegram bot** (chat bot)
- Web/REST API (future)
- Mobile app (future)
- Voice interface (future)

## Architecture

```
Telegram Update
  ↓ (Telegram library routes to handlers)
TelegramBotApp
  ↓ (dispatches to)
TelegramHandler
  ├─ Parses command/message
  └─ Calls services (CaptureService, ListService, etc.)
  ↓ (services execute business logic)
ItemServiceRegistry
  ├─ CaptureService
  ├─ ListService
  ├─ RelationService
  └─ MergeService
  ↓ (services use)
Storage interface
  └─ JsonStorage OR PostgresStorage (based on config)
  ↓ (format response)
TelegramFormatter
  ↓ (send back to Telegram)
User receives message in Telegram
```

## Usage

### Installation

```bash
# Install Telegram bot library
pip install python-telegram-bot

# OR add to requirements.txt:
python-telegram-bot>=20.0
```

### Environment Setup

```bash
# Get your bot token from @BotFather on Telegram
export ADHD_TELEGRAM_TOKEN=your_token_here

# Optional: choose storage backend
export ADHD_STORAGE_BACKEND=json  # or postgres

# Optional: PostgreSQL settings (if using postgres backend)
export DATABASE_URL=postgresql://user:pass@localhost:5432/adhd_db

# Optional: JSON storage path
export ADHD_NOTES_PATH=data/notes.json
```

### Running the Bot

**Development (polling - bot checks for updates)**:
```bash
python app/telegram_main.py
```

**Production (webhook - Telegram sends updates to your server)**:
```bash
export ADHD_TELEGRAM_WEBHOOK_URL=https://your-domain.com
python app/telegram_main.py
```

## Available Commands

### Item Creation

```
/task TEXT — Create a task
/note TEXT — Create a note
/idea TEXT — Create an idea
/capture TEXT — Auto-detect type and create
```

**Examples**:
```
/task Buy groceries
/note Remember to call John
/idea New app feature: offline sync
/capture Don't forget the meeting at 3pm
```

### Item Management

```
/list [all|task|note|idea] — List items (default: all)
/clear — Remove all items
```

**Examples**:
```
/list all        # Show all items
/list task       # Show only tasks
/list            # Equivalent to /list all
/clear           # Delete everything
```

### Help

```
/help — Show available commands
/start — Welcome message
```

### Quick Capture

Just send any message (that's not a command) to capture it:
```
Buy milk tomorrow
Interesting idea about distributed systems
```

## Command Routing

```
Telegram Update
├─ /start → handle_start_command()
├─ /help → handle_help_command()
├─ /task TEXT → handle_task_command(TEXT)
├─ /note TEXT → handle_note_command(TEXT)
├─ /idea TEXT → handle_idea_command(TEXT)
├─ /capture TEXT → handle_capture_command(TEXT)
├─ /list [TYPE] → handle_list_command(TYPE)
├─ /clear → handle_clear_command()
└─ Plain text → handle_message() → auto-capture
```

## Code Examples

### Creating a Task via Telegram

```
User sends: /task Buy milk

Handler flow:
1. TelegramBotApp.task_handler() receives update
2. Extracts text: "Buy milk"
3. Calls TelegramHandler.handle_task_command("Buy milk")
4. Handler calls services.capture_service.capture_text(..., item_type=ItemType.TASK)
5. Service creates Item with type=TASK, text="Buy milk"
6. Service calls storage.add_item(item)  ← Storage can be JSON or PostgreSQL
7. TelegramFormatter.success() formats response
8. User receives: "✅ Task created: Buy milk"
```

### Listing All Items

```
User sends: /list

Handler flow:
1. TelegramBotApp.list_handler() receives update
2. Calls TelegramHandler.handle_list_command(None)
3. Handler calls services.list_service.list_items("all")
4. Service calls storage.load_items()  ← Storage abstraction
5. Gets list of Item objects
6. TelegramFormatter.list_items() formats as Telegram message
7. User receives formatted list with emojis
```

## Formatting Examples

### Success Message
```
✅ Task created: Buy groceries

✅ TASK
ID: `123e4567-e89b-12d3-a456-426614174000`
Status: active
Text: Buy groceries
Created: 2026-07-16 14:02
```

### Item List
```
📋 Found 3 item(s):

1. ✅ `task` — Buy groceries
2. 📝 `note` — Remember deadline
3. 💡 `idea` — New feature idea
```

### Error Message
```
❌ Task text cannot be empty
```

## Testing

### Unit Tests

```bash
# Test handler logic (mock services)
make test-one TEST=tests/test_telegram_handler.py

# Test formatter (no external deps)
make test-one TEST=tests/test_telegram_formatter.py
```

### Integration Tests

```bash
# Test with real services
make test-one TEST=tests/test_telegram_integration.py
```

### Manual Testing

```bash
# Start bot in development mode
ADHD_TELEGRAM_TOKEN=your_token python app/telegram_main.py

# In Telegram app:
# 1. Find your bot (@username)
# 2. Send /start
# 3. Try commands: /task Buy milk, /list, /help
```

## Storage Independence

The key design feature: **storage abstraction**.

Handler code:
```python
def __init__(self):
    self.storage = self._init_storage()  # Returns Storage interface
    self.services = ItemServiceRegistry(self.storage)
```

Handler NEVER does:
```python
# ❌ BAD: Direct storage access
from storage.json_storage import JsonStorage
items = JsonStorage(...).load_items()

# ❌ BAD: Hardcoded backend
if backend == "json":
    self.storage = JsonStorage(...)
elif backend == "postgres":
    self.storage = PostgresStorage(...)
```

Handler ALWAYS does:
```python
# ✅ GOOD: Storage interface abstraction
from interfaces.storage import Storage

def __init__(self):
    self.storage = self._init_storage()  # Returns Storage
    # Now all operations go through Storage interface
```

## Adding New Commands

### Step 1: Add handler method to TelegramHandler

```python
def handle_search_command(self, query: str) -> str:
    """Search items by text."""
    try:
        # Call service (doesn't know about storage)
        items = self.services.relation_service.search_items(query)
        return self.formatter.list_items(items)
    except StorageError as e:
        return self.formatter.error(f"Search failed: {str(e)}")
```

### Step 2: Add async handler to TelegramBotApp

```python
async def search_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /search command."""
    query = " ".join(context.args) if context.args else ""
    response = self.handler.handle_search_command(query)
    await update.message.reply_text(response, parse_mode="Markdown")
```

### Step 3: Register in TelegramBotApp.build()

```python
async def build(self) -> Application:
    # ... existing handlers ...
    self.app.add_handler(CommandHandler("search", self.search_handler))
    return self.app
```

### Step 4: Add tests

```python
def test_search_command(self):
    """Test /search command."""
    response = self.handler.handle_search_command("milk")
    assert "Found" in response
```

## Common Patterns

### Error Handling

All handlers follow this pattern:
```python
def handle_command(self, args) -> str:
    try:
        # Call service
        result = self.services.some_service.some_operation(args)
        # Format success
        return self.formatter.success(...)
    except (StorageError, CliInputError) as e:
        # Format error
        return self.formatter.error(str(e))
```

### Service Calling

Never import storage directly:
```python
# ✅ GOOD
self.services.capture_service.capture_text(text)

# ❌ BAD
self.storage.add_item(item)  # Handler doesn't do this
```

### Response Formatting

```python
# Use formatter for all output
self.formatter.success(message, item=item)
self.formatter.error(message)
self.formatter.info(message)
self.formatter.list_items(items)
self.formatter.help_text()
```

## Deployment

### Local Development

```bash
export ADHD_TELEGRAM_TOKEN=your_token
python app/telegram_main.py
```

### Docker

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ENV ADHD_TELEGRAM_TOKEN=${TELEGRAM_TOKEN}
ENV ADHD_STORAGE_BACKEND=postgres

CMD ["python", "app/telegram_main.py"]
```

### Systemd Service

```ini
[Unit]
Description=ADHD Assistant Telegram Bot
After=network.target

[Service]
Type=simple
User=adhd-bot
WorkingDirectory=/opt/adhd-assistant
Environment="ADHD_TELEGRAM_TOKEN=YOUR_TOKEN"
Environment="ADHD_STORAGE_BACKEND=postgres"
Environment="DATABASE_URL=postgresql://..."
ExecStart=/usr/bin/python3 app/telegram_main.py

Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Architecture Principles

1. **Single Domain Logic**: All business logic in services, reused across CLI/Telegram/Web
2. **Storage Abstraction**: Handler never imports concrete storage classes
3. **Graceful Degradation**: JSON backend for local use, PostgreSQL for production
4. **Test Isolation**: Handler tests mock services, not storage
5. **User-Friendly Errors**: All errors formatted nicely for Telegram

## Related Files

- `telegram_bot/telegram_handler.py` - Main command handler
- `telegram_bot/telegram_formatter.py` - Telegram message formatting
- `app/telegram_main.py` - Bot entry point
- `services/item_service_registry.py` - Use case services (business logic)
- `interfaces/storage.py` - Storage contract
- `config/settings.py` - Configuration loading

## Future Enhancements

1. **Inline Buttons**: Add keyboard buttons for common actions
2. **Conversation States**: Multi-step command workflows
3. **User Preferences**: Per-user settings (storage backend, language)
4. **Media Support**: Image/document capture
5. **Webhooks**: Event-driven updates (reminders, etc.)
6. **Admin Commands**: Mod panel for server management
7. **Analytics**: Track usage patterns
8. **Notifications**: Send reminders based on item properties

---

**Key Takeaway**: The Telegram bot demonstrates how clean architecture enables code reuse. The same business logic works across CLI, bot, web, and future interfaces without modification.
