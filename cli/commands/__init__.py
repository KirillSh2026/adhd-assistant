"""Item management commands (list, clear, add by type)."""

from datetime import datetime

from services.item_service_registry import ItemServiceRegistry
from cli.formatters import print_item
from cli.utils import parse_int
from core.exceptions import CliInputError
from services.item_type_classifier import SUPPORTED_ITEM_TYPES


def list_items(service: ItemServiceRegistry, args: list[str]) -> None:
    """List items, optionally filtering by type."""
    filter_type = args[0].lower() if args else "all"
    
    if filter_type not in ["all", "task", "note", "idea"]:
        raise CliInputError(f"Unknown type '{filter_type}'. Use: all, task, note, or idea")
    
    for index, item in service.list_items(filter_type):
        print_item(index=index, item=item)


def clear_items(service: ItemServiceRegistry, args: list[str]) -> None:
    """Clear all stored items."""
    service.clear_items()


def add_item_by_type(service: ItemServiceRegistry, note_type: str, args: list[str]) -> None:
    """Add item with explicit type."""
    text = " ".join(args).strip()
    if not text:
        raise CliInputError(f"Usage: python app/main.py {note_type} \"text\"")
    
    service.add_item(note_type=note_type, text=text, created_at=datetime.now())
    print(f"Added [{note_type}]: {text}")
