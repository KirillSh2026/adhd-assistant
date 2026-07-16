"""Output formatting for CLI commands."""


def print_item(index: int, item) -> None:
    """Format and print an individual item."""
    if item.created_at:
        print(f"{index}. ({item.created_at.strftime('%Y-%m-%d %H:%M:%S')}) [{item.type}]: {item.text}")
    else:
        print(f"{index}. [{item.type}]: {item.text}")


def print_relation(relation: dict) -> None:
    """Format and print a relation between items."""
    status = "confirmed" if relation["is_confirmed"] else "suggested"
    print(
        f"[{status}] {relation['from_index']} -> {relation['to_index']} "
        f"({relation['relationship_type']}): {relation['reason']}"
    )
    print(f"  from: {relation['from_text']}")
    print(f"  to:   {relation['to_text']}")


def print_suggestion(suggestion: dict) -> None:
    """Format and print a relation suggestion with similarity score."""
    print(
        f"[suggested] {suggestion['from_index']} -> {suggestion['to_index']} "
        f"({suggestion['relationship_type']}, score={suggestion['score']:.2f})"
    )
    print(f"  reason: {suggestion['reason']}")
    print(f"  from:   {suggestion['from_text']}")
    print(f"  to:     {suggestion['to_text']}")


def print_cluster(cluster_number: int, cluster: dict) -> None:
    """Format and print a similarity cluster."""
    print(
        f"Cluster {cluster_number} (size={cluster['size']}, avg_score={cluster['average_score']:.2f})"
    )
    for member in cluster["members"]:
        print(f"  {member['index']}. [{member['type']}] {member['text']}")


def print_merge_entry(entry: dict) -> None:
    """Format and print a merge history entry."""
    target_label = entry["target_index"] if entry["target_index"] is not None else entry["target_item_id"]
    source_labels = [
        str(index if index is not None else item_id)
        for index, item_id in zip(entry["source_indices"], entry["source_item_ids"])
    ]
    undo_flag = "undoable" if entry["can_undo"] else "locked"
    print(
        f"[{undo_flag}] merge={entry['merge_id']} target={target_label} "
        f"sources={','.join(source_labels)} at {entry['performed_at']}"
    )
    print(f"  reason: {entry['reason']}")
