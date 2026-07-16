"""Item merging and merge history commands."""

from services.item_service import ItemService
from cli.formatters import print_merge_entry
from cli.utils import parse_int
from core.exceptions import CliInputError


def merge_items(service: ItemService, args: list[str]) -> None:
    """Merge multiple source items into a target item."""
    if len(args) < 2:
        raise CliInputError(
            "Usage: python app/main.py merge-items <target_index> <source_index> [source_index ...] [--reason text]"
        )
    
    reason = ""
    if "--reason" in args:
        marker_index = args.index("--reason")
        reason = " ".join(args[marker_index + 1:]).strip()
        args = args[:marker_index]
    
    if len(args) < 2:
        raise CliInputError("merge-items requires a target index and at least one source index")
    
    target_index = parse_int(args[0], "target_index")
    source_indices = [parse_int(value, "source_index") for value in args[1:]]
    service.merge_items(target_index=target_index, source_indices=source_indices, merge_reason=reason)
    print(f"Merged items {', '.join(str(index) for index in source_indices)} into {target_index}.")


def list_merges(service: ItemService, args: list[str]) -> None:
    """List recent merge operations with optional limit."""
    limit = parse_int(args[0], "limit") if args else 20
    merges = service.list_merges(limit=limit)
    if not merges:
        print("No merges found.")
        return
    for entry in merges:
        print_merge_entry(entry)


def undo_merge(service: ItemService, args: list[str]) -> None:
    """Undo the most recent merge operation."""
    merge_id = args[0].strip() if args else None
    result = service.undo_merge(merge_id=merge_id)
    target_label = result["target_index"] if result["target_index"] is not None else result["target_item_id"]
    source_labels = [
        str(index if index is not None else item_id)
        for index, item_id in zip(result["source_indices"], result["source_item_ids"])
    ]
    print(
        f"Undo complete for merge {result['merge_id']}: restored sources {', '.join(source_labels)} "
        f"and target {target_label}."
    )
