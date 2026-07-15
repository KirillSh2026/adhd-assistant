from datetime import datetime
import os
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from services.item_service import ItemService
from services.speech_to_text_service import SpeechToTextService
from services.item_type_classifier import SUPPORTED_ITEM_TYPES
from storage.json_storage import JsonStorage


def get_service() -> ItemService:
    backend = os.getenv("ADHD_STORAGE_BACKEND", "json").strip().lower()
    notes_path = os.getenv("ADHD_NOTES_PATH", "data/notes.json")
    database_url = os.getenv("DATABASE_URL", "")

    if backend == "postgres":
        if not database_url:
            raise ValueError("DATABASE_URL is required when ADHD_STORAGE_BACKEND=postgres")
        from storage.postgres_storage import PostgresStorage

        storage = PostgresStorage(dsn=database_url)
    else:
        storage = JsonStorage(path=notes_path)
    return ItemService(storage=storage)


def print_item(index: int, item) -> None:
    if item.datetime:
        print(f"{index}. ({item.datetime}) [{item.type}]: {item.text}")
    else:
        print(f"{index}. [{item.type}]: {item.text}")


def print_relation(relation: dict) -> None:
    status = "confirmed" if relation["is_confirmed"] else "suggested"
    print(
        f"[{status}] {relation['from_index']} -> {relation['to_index']} "
        f"({relation['relationship_type']}): {relation['reason']}"
    )
    print(f"  from: {relation['from_text']}")
    print(f"  to:   {relation['to_text']}")


def print_suggestion(suggestion: dict) -> None:
    print(
        f"[suggested] {suggestion['from_index']} -> {suggestion['to_index']} "
        f"({suggestion['relationship_type']}, score={suggestion['score']:.2f})"
    )
    print(f"  reason: {suggestion['reason']}")
    print(f"  from:   {suggestion['from_text']}")
    print(f"  to:     {suggestion['to_text']}")


def print_cluster(cluster_number: int, cluster: dict) -> None:
    print(
        f"Cluster {cluster_number} (size={cluster['size']}, avg_score={cluster['average_score']:.2f})"
    )
    for member in cluster["members"]:
        print(f"  {member['index']}. [{member['type']}] {member['text']}")


def add_from_dictation(service: ItemService) -> None:
    args = [arg.strip() for arg in sys.argv[2:] if arg.strip()]
    note_type = None
    audio_path = ""

    if args and args[0].lower() in SUPPORTED_ITEM_TYPES:
        note_type = args[0].lower()
        audio_path = " ".join(args[1:]).strip()
    else:
        audio_path = " ".join(args).strip()

    language = os.getenv("ADHD_DICTATE_LANGUAGE", "ru-RU")
    speech_service = SpeechToTextService(language=language)

    if audio_path:
        text = speech_service.transcribe_audio_file(audio_path)
    else:
        text = speech_service.transcribe_microphone()

    resolved_type = service.add_captured_item(text=text, created_at=datetime.now(), note_type=note_type)
    print(f"Added from dictation: [{resolved_type}] {text}")


def add_from_text_capture(service: ItemService) -> None:
    text = " ".join(sys.argv[2:]).strip()
    if not text:
        raise ValueError('Usage: python app/main.py capture "text to classify"')

    resolved_type = service.add_captured_item(text=text, created_at=datetime.now())
    print(f"Added captured item: [{resolved_type}] {text}")


def show_suggested_relations(service: ItemService) -> None:
    suggestions = service.suggest_relations()
    if not suggestions:
        print("No relation suggestions found.")
        return
    for suggestion in suggestions:
        print_suggestion(suggestion)


def show_clusters(service: ItemService) -> None:
    clusters = service.show_clusters()
    if not clusters:
        print("No clusters found.")
        return
    for index, cluster in enumerate(clusters, start=1):
        print_cluster(index, cluster)


def show_relations(service: ItemService) -> None:
    item_index = int(sys.argv[2]) if len(sys.argv) >= 3 and sys.argv[2].strip() else None
    relations = service.list_relations(item_index=item_index)
    if not relations:
        print("No stored relations found.")
        return
    for relation in relations:
        print_relation(relation)


def link_items(service: ItemService) -> None:
    if len(sys.argv) < 5:
        raise ValueError(
            "Usage: python app/main.py link-items <from_index> <to_index> <related|depends_on|duplicate_of> [reason]"
        )

    from_index = int(sys.argv[2])
    to_index = int(sys.argv[3])
    relation_type = sys.argv[4]
    reason = " ".join(sys.argv[5:]).strip()
    service.link_items(from_index=from_index, to_index=to_index, relation_type=relation_type, reason=reason)
    print(f"Linked items {from_index} -> {to_index} as {relation_type}.")


def confirm_relation(service: ItemService) -> None:
    if len(sys.argv) < 5:
        raise ValueError(
            "Usage: python app/main.py confirm-relation <from_index> <to_index> <related|depends_on|duplicate_of>"
        )

    from_index = int(sys.argv[2])
    to_index = int(sys.argv[3])
    relation_type = sys.argv[4]
    service.confirm_relation(from_index=from_index, to_index=to_index, relation_type=relation_type)
    print(f"Confirmed relation {from_index} -> {to_index} as {relation_type}.")


def merge_items(service: ItemService) -> None:
    if len(sys.argv) < 4:
        raise ValueError(
            "Usage: python app/main.py merge-items <target_index> <source_index> [source_index ...] [--reason text]"
        )

    args = sys.argv[2:]
    reason = ""
    if "--reason" in args:
        marker_index = args.index("--reason")
        reason = " ".join(args[marker_index + 1 :]).strip()
        args = args[:marker_index]

    if len(args) < 2:
        raise ValueError("merge-items requires a target index and at least one source index")

    target_index = int(args[0])
    source_indices = [int(value) for value in args[1:]]
    service.merge_items(target_index=target_index, source_indices=source_indices, merge_reason=reason)
    print(f"Merged items {', '.join(str(index) for index in source_indices)} into {target_index}.")


def main():
    if len(sys.argv) < 2:
        return

    service = get_service()
    command = sys.argv[1].strip().lower()
    text = " ".join(sys.argv[2:]).strip()
    if command == "list":
        for index, item in service.list_items(text):
            print_item(index=index, item=item)
    elif command == "clear":
        service.clear_items()
    elif command == "capture":
        add_from_text_capture(service=service)
    elif command == "dictate":
        add_from_dictation(service=service)
    elif command == "suggest-relations":
        show_suggested_relations(service=service)
    elif command == "show-clusters":
        show_clusters(service=service)
    elif command == "list-relations":
        show_relations(service=service)
    elif command == "link-items":
        link_items(service=service)
    elif command == "confirm-relation":
        confirm_relation(service=service)
    elif command == "merge-items":
        merge_items(service=service)
    elif command in SUPPORTED_ITEM_TYPES and text:
        service.add_item(note_type=command, text=text, created_at=datetime.now())
    elif text:
        raise ValueError(
            "Unsupported command. Use task, note, idea, capture, dictate, suggest-relations, show-clusters, list-relations, link-items, confirm-relation, merge-items, list, or clear."
        )


if __name__ == "__main__":
    main()
