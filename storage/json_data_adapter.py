"""Adapter for JSON file format (legacy and new)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.exceptions import StorageError
from models.item import Item
from models.item_adapter import ItemAdapter


class JsonDataAdapter:
    """Handles all JSON file I/O with error handling and atomic writes."""

    def __init__(self, file_path: Path):
        """Initialize adapter with file path.
        
        Args:
            file_path: Path object pointing to JSON file
            
        Raises:
            StorageError: If file path is invalid
        """
        if not isinstance(file_path, Path):
            raise StorageError(f"file_path must be Path, got {type(file_path)}")
        self.file_path = file_path

    def ensure_file(self) -> None:
        """Ensure JSON file exists and is initialized.
        
        Creates parent directories and initializes empty array if needed.
        """
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self._write_json([])

    def load_items(self) -> list[Item]:
        """Load items from JSON file.
        
        Returns:
            List of Item objects parsed from JSON
            
        Raises:
            StorageError: If JSON is corrupted or file cannot be read
        """
        try:
            content = self.file_path.read_text(encoding="utf-8")
            raw_items = json.loads(content)
            
            if not isinstance(raw_items, list):
                raise StorageError(
                    f"JSON root must be array, got {type(raw_items).__name__}. "
                    f"Expected format: [{{ 'type': 'task', 'text': '...' }}]"
                )
            
            items = []
            for i, raw_item in enumerate(raw_items):
                try:
                    item = ItemAdapter.from_legacy_dict(raw_item)
                    items.append(item)
                except Exception as e:
                    raise StorageError(
                        f"Invalid item at index {i}: {e}. "
                        f"Item: {raw_item}"
                    ) from e
            
            return items
            
        except json.JSONDecodeError as e:
            raise StorageError(
                f"JSON file corrupted at line {e.lineno}, column {e.colno}: {e.msg}\n"
                f"File: {self.file_path}\n"
                f"Consider backing up and manually fixing or deleting the file."
            ) from e
        except FileNotFoundError:
            raise StorageError(f"JSON file not found: {self.file_path}") from None
        except Exception as e:
            raise StorageError(f"Failed to read JSON file {self.file_path}: {e}") from e

    def save_items(self, items: list[Item]) -> None:
        """Save items to JSON file with atomic write.
        
        Uses temporary file + rename pattern to prevent corruption
        if write is interrupted.
        
        Args:
            items: List of Item objects to save
            
        Raises:
            StorageError: If write fails or permissions denied
        """
        try:
            data = [ItemAdapter.to_legacy_dict(item) for item in items]
            self._write_json(data, atomic=True)
        except Exception as e:
            raise StorageError(f"Failed to save JSON file {self.file_path}: {e}") from e

    def _write_json(self, data: list[dict[str, Any]], atomic: bool = False) -> None:
        """Write data to JSON file.
        
        Args:
            data: List of dicts to write as JSON
            atomic: If True, use temp file + atomic rename
            
        Raises:
            StorageError: If write fails
        """
        content = json.dumps(data, ensure_ascii=False, indent=2)
        
        if atomic:
            # Atomic write: write to temp, then rename
            temp_path = self.file_path.with_suffix(".tmp")
            try:
                temp_path.write_text(content, encoding="utf-8")
                temp_path.replace(self.file_path)
            except Exception as e:
                if temp_path.exists():
                    try:
                        temp_path.unlink()
                    except Exception:
                        pass
                raise StorageError(
                    f"Failed to atomically write JSON file: {e}\n"
                    f"Original file: {self.file_path}\n"
                    f"Temp file: {temp_path}"
                ) from e
        else:
            # Direct write for initialization
            try:
                self.file_path.write_text(content, encoding="utf-8")
            except Exception as e:
                raise StorageError(f"Failed to write JSON file: {e}") from e
