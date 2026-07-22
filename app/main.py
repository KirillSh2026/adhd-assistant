"""CLI application entry point.

This module serves as the main entry point for the ADHD Assistant CLI.
It handles:
1. Parsing sys.argv into structured command and arguments
2. Service initialization with configured storage backend
3. Exception wrapping for clean error reporting
4. Delegation to CLI dispatcher layer
"""
import sys
from pathlib import Path

# Ensure the project root is in the Python path so that `core` can be imported
# when the script is executed directly (e.g., `python app/main.py`).
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.exceptions import AppError, StorageError
from cli.parser import parse_command_line
from cli.dispatcher import dispatch_command
from config.factory import get_service


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
    except (StorageError, AppError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
