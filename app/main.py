from datetime import datetime
import os
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from services.item_service import ItemService
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

def main():
    if len(sys.argv) < 2:
        return

    service = get_service()
    note_type = "".join(sys.argv[1])
    text = " ".join(sys.argv[2:])
    if note_type == "list":
        for index, item in service.list_items(text):
            print_item(index=index, item=item)
    elif note_type == "clear":
        service.clear_items()
    elif text:
        service.add_item(note_type=note_type, text=text, created_at=datetime.now())

if __name__ == "__main__":
    main()
