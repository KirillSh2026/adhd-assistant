# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Setup and Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Check Python syntax
make check

# Run tests
make test

# Run a single test
make test-one TEST=tests/test_item_service.py::test_add_and_list_with_legacy_format
```

### PostgreSQL/Migrations
```bash
# Initialize PostgreSQL schema
make migrate-up

# Import JSON data to PostgreSQL
make migrate-import-json

# Rollback last JSON import
make migrate-rollback

# Drop all PostgreSQL tables
make migrate-down
```

### CLI Usage
```bash
# Add items by type
python app/main.py task "Купить продукты"
python app/main.py note "Идея для проекта"
python app/main.py idea "Начать медитировать"

# Auto-detect type from text
python app/main.py capture "Купить продукты"
python app/main.py dictate  # from microphone
python app/main.py dictate /path/to/audio.wav  # from file

# List items
python app/main.py list all
python app/main.py list task
python app/main.py list note
python app/main.py list idea

# Clear all items
python app/main.py clear

# Relations (require PostgreSQL backend)
python app/main.py suggest-relations      # Find and save relation suggestions
python app/main.py show-clusters          # Show similarity clusters
python app/main.py list-relations         # List all relations
python app/main.py link-items 1 2 related # Explicitly link items
python app/main.py confirm-relation 1 2 duplicate_of  # Confirm suggested relation
python app/main.py reject-relation 1 2 duplicate_of   # Reject suggested relation

# Merge items (require PostgreSQL backend)
python app/main.py merge-items 1 2 3 --reason "Объединяем дубликаты"
python app/main.py list-merges            # View merge history
python app/main.py undo-merge             # Undo last merge
python app/main.py undo-merge <merge_id>  # Undo specific merge
```

## Architecture Overview

### Layers
1. **CLI Layer** (`app/main.py`, `cli/`) - Entry point and command parsing
2. **Service Layer** (`services/`) - Business logic and use cases
3. **Storage Interface** (`interfaces/storage.py`) - Storage protocol/abstraction
4. **Storage Implementations** (`storage/`) - JSON and PostgreSQL implementations
5. **Models** (`models/`) - Data models (Item, ItemType, ItemStatus)

### Key Components

#### Service Layer (`services/`)
- `ItemServiceRegistry` - Main service facade combining all use cases
- `CaptureService` - Adding items with/without auto-classification
- `ListService` - Listing items with filtering
- `RelationService` - Managing item relationships (links, dependencies)
- `MergeService` - Merging items and maintaining history
- `RelationAnalysisService` - Finding similar items and suggesting relations
- `ItemTypeClassifier` - Auto-detecting item type from text

#### Storage Backends
- **JSON Storage** (`storage/json_storage.py`) - Default, file-based, limited to basic CRUD
- **PostgreSQL Storage** (`storage/postgres/storage.py`) - Full featured with relations, merges, audit

#### Key Limitations
- JSON backend only supports basic item operations (add, list, clear)
- Relations, merges, and clustering require PostgreSQL backend
- Audio files are processed for speech-to-text but not stored

### Configuration
Configuration is handled through environment variables loaded by `config/settings.py`:
- `ADHD_STORAGE_BACKEND` - `json` (default) or `postgres`
- `ADHD_NOTES_PATH` - Path to JSON file (default: `data/notes.json`)
- `DATABASE_URL` - PostgreSQL connection string
- `ADHD_POSTGRES_OPTIONS` - Additional PostgreSQL options (e.g., `sslmode=require`)
- `ADHD_DICTATE_LANGUAGE` - Speech recognition language (default: `ru-RU`)

### Data Models
Items have:
- `id` (string, UUID)
- `type` (task/note/idea)
- `text` (string)
- `created_at` (datetime)
- `status` (pending/archived)

Relationships stored in PostgreSQL:
- `item_dependency` table - links between items (related, depends_on, duplicate_of)
- `item_merge` table - merge history with ability to undo
- `item_audit` table - audit trail of changes

### Extensibility Points
- Add new item types by updating `SUPPORTED_ITEM_TYPES` in `services/item_type_classifier.py`
- Extend storage capabilities by implementing the `Storage` interface
- Add new CLI commands by creating handlers in `cli/commands/` and registering in `cli/dispatcher.py`