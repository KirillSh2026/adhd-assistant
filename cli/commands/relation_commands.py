"""Relation and dependency management commands."""

from services.item_service import ItemService
from cli.formatters import print_relation, print_suggestion, print_cluster
from cli.utils import parse_int
from core.exceptions import CliInputError


def show_suggested_relations(service: ItemService, args: list[str]) -> None:
    """Show suggested relations based on similarity analysis."""
    suggestions = service.suggest_relations()
    if not suggestions:
        print("No relation suggestions found.")
        return
    for suggestion in suggestions:
        print_suggestion(suggestion)


def show_clusters(service: ItemService, args: list[str]) -> None:
    """Show similarity clusters of related items."""
    clusters = service.show_clusters()
    if not clusters:
        print("No clusters found.")
        return
    for index, cluster in enumerate(clusters, start=1):
        print_cluster(index, cluster)


def show_relations(service: ItemService, args: list[str]) -> None:
    """List stored relations for an item or all relations."""
    item_index = parse_int(args[0], "item_index") if args else None
    relations = service.list_relations(item_index=item_index)
    if not relations:
        print("No stored relations found.")
        return
    for relation in relations:
        print_relation(relation)


def link_items(service: ItemService, args: list[str]) -> None:
    """Explicitly link two items with a relation."""
    if len(args) < 3:
        raise CliInputError(
            "Usage: python app/main.py link-items <from_index> <to_index> <related|depends_on|duplicate_of> [reason]"
        )
    
    from_index = parse_int(args[0], "from_index")
    to_index = parse_int(args[1], "to_index")
    relation_type = args[2]
    reason = " ".join(args[3:]).strip()
    service.link_items(from_index=from_index, to_index=to_index, relation_type=relation_type, reason=reason)
    print(f"Linked items {from_index} -> {to_index} as {relation_type}.")


def confirm_relation(service: ItemService, args: list[str]) -> None:
    """Confirm a suggested relation."""
    if len(args) < 3:
        raise CliInputError(
            "Usage: python app/main.py confirm-relation <from_index> <to_index> <related|depends_on|duplicate_of>"
        )
    
    from_index = parse_int(args[0], "from_index")
    to_index = parse_int(args[1], "to_index")
    relation_type = args[2]
    service.confirm_relation(from_index=from_index, to_index=to_index, relation_type=relation_type)
    print(f"Confirmed relation {from_index} -> {to_index} as {relation_type}.")


def reject_relation(service: ItemService, args: list[str]) -> None:
    """Reject a suggested relation."""
    if len(args) < 3:
        raise CliInputError(
            "Usage: python app/main.py reject-relation <from_index> <to_index> <related|depends_on|duplicate_of>"
        )
    
    from_index = parse_int(args[0], "from_index")
    to_index = parse_int(args[1], "to_index")
    relation_type = args[2]
    service.reject_relation(from_index=from_index, to_index=to_index, relation_type=relation_type)
    print(f"Rejected suggested relation {from_index} -> {to_index} as {relation_type}.")
