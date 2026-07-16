"""CLI application entry point.

This module serves as the main entry point for the ADHD Assistant CLI.
It handles:
1. Parsing sys.argv into structured command and arguments
2. Service initialization with configured storage backend
3. Exception wrapping for clean error reporting
4. Delegation to CLI dispatcher layer
"""

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.settings import get_settings
from core.exceptions import AppError, ConfigurationError, StorageError
from services.item_service import ItemService
from storage.json_storage import JsonStorage
from cli.parser import parse_command_line
from cli.dispatcher import dispatch_command


def get_service() -> ItemService:
    """Initialize and return the ItemService with configured storage backend.
    
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

        storage = PostgresStorage(dsn=database_url)
    else:
        try:
            storage = JsonStorage(path=notes_path)
        except Exception as e:
            raise StorageError(
                f"Failed to initialize JSON storage at {notes_path}: {e}\n"
                f"Make sure the directory is writable and valid."
            ) from e
    return ItemService(storage=storage)


def main() -> None:
    """Main CLI entry point: parse sys.argv and dispatch to handler.
    
    Raises:
        AppError: On any application error
    """
    parsed = parse_command_line(sys.argv)
    
    if not parsed.command:
        return  # No command provided

    service = get_service()
    dispatch_command(service, parsed.command, parsed.args)


if __name__ == "__main__":
    try:
        main()
    except StorageError as exc:
        print(f"Storage Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except AppError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except Exception as exc:
        print(f"Unexpected error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
