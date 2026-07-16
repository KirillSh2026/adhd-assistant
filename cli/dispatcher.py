"""CLI command dispatcher - routes commands to appropriate handlers."""

from services.item_service import ItemService
from services.item_type_classifier import SUPPORTED_ITEM_TYPES
from core.exceptions import CliInputError

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


def dispatch_command(service: ItemService, command: str, args: list[str]) -> None:
    """Route CLI command to appropriate handler with parsed arguments.
    
    Args:
        service: ItemService instance
        command: Command name (already lowercased)
        args: Remaining positional arguments (already stripped)
    """
    if command == "list":
        list_items(service, args)
    elif command == "clear":
        clear_items(service, args)
    elif command == "capture":
        add_from_text_capture(service, args)
    elif command == "dictate":
        add_from_dictation(service, args)
    elif command == "suggest-relations":
        show_suggested_relations(service, args)
    elif command == "show-clusters":
        show_clusters(service, args)
    elif command == "list-relations":
        show_relations(service, args)
    elif command == "link-items":
        link_items(service, args)
    elif command == "confirm-relation":
        confirm_relation(service, args)
    elif command == "reject-relation":
        reject_relation(service, args)
    elif command == "merge-items":
        merge_items(service, args)
    elif command == "list-merges":
        list_merges(service, args)
    elif command == "undo-merge":
        undo_merge(service, args)
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
