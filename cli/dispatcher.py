"""CLI command dispatcher - routes commands to appropriate handlers."""

from services.item_service_registry import ItemServiceRegistry
from services.item_type_classifier import SUPPORTED_ITEM_TYPES
from core.exceptions import CliInputError, UnsupportedStorageCapabilityError

from cli.commands import list_items, clear_items, add_item_by_type
from cli.commands.capture_commands import add_from_text_capture, add_from_dictation
from cli.commands.relation_commands import (
    show_suggested_relations,
    show_clusters,
    show_relations,
    link_items,
    confirm_relation,
    reject_relation,
)
from cli.commands.merge_commands import merge_items, list_merges, undo_merge


def dispatch_command(service: ItemServiceRegistry, command: str, args: list[str]) -> None:
    """Route CLI command to appropriate handler with parsed arguments.
    
    Args:
        service: ItemServiceRegistry instance
        command: Command name (already lowercased)
        args: Remaining positional arguments (already stripped)
        
    Raises:
        CliInputError: On invalid arguments
        UnsupportedStorageCapabilityError: If storage backend doesn't support command
    """
    # Map of command strings to handler functions
    COMMANDS = {
        "list": list_items,
        "clear": clear_items,
        "capture": add_from_text_capture,
        "dictate": add_from_dictation,
        "suggest-relations": show_suggested_relations,
        "show-clusters": show_clusters,
        "list-relations": show_relations,
        "link-items": link_items,
        "confirm-relation": confirm_relation,
        "reject-relation": reject_relation,
        "merge-items": merge_items,
        "list-merges": list_merges,
        "undo-merge": undo_merge,
    }

    try:
        handler = COMMANDS.get(command)
        if handler is not None:
            handler(service, args)
        elif command in SUPPORTED_ITEM_TYPES:
            if args:
                add_item_by_type(service, command, args)
            else:
                raise CliInputError(
                    "Unsupported command. Use task, note, idea, capture, dictate, suggest-relations, show-clusters, list-relations, link-items, confirm-relation, reject-relation, merge-items, list-merges, undo-merge, list, or clear."
                )
        elif command:
            raise CliInputError(
                "Unsupported command. Use task, note, idea, capture, dictate, suggest-relations, show-clusters, list-relations, link-items, confirm-relation, reject-relation, merge-items, list-merges, undo-merge, list, or clear."
            )
    except UnsupportedStorageCapabilityError as e:
        # Enhance error message with helpful context
        error_msg = str(e)
        if "PostgreSQL" in error_msg or "postgres" in error_msg:
            raise CliInputError(
                f"❌ This command requires PostgreSQL backend.\n\n"
                f"Details:\n{error_msg}\n\n"
                f"To enable PostgreSQL:\n"
                f"  1. Set up PostgreSQL database\n"
                f"  2. Set DATABASE_URL environment variable\n"
                f"  3. Set ADHD_STORAGE_BACKEND=postgres\n"
                f"  4. Run migrations: make migrate-up"
            ) from e
        else:
            raise CliInputError(f"Storage operation not supported:\n{error_msg}") from e
