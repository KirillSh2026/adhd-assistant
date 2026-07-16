"""Tests for CLI layer (command handlers, formatters, dispatcher)."""

import io
import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from cli.dispatcher import dispatch_command
from cli.formatters import print_item, print_relation, print_suggestion, print_cluster, print_merge_entry
from cli.utils import parse_int
from core.exceptions import CliInputError


class MockItem:
    """Mock item for formatter tests."""
    def __init__(self, item_type: str, text: str, created_at=None):
        self.type = item_type
        self.text = text
        self.created_at = created_at


def test_parse_int_valid() -> None:
    """Test parse_int with valid integer string."""
    result = parse_int("42", "test_arg")
    assert result == 42


def test_parse_int_invalid() -> None:
    """Test parse_int with invalid input."""
    with pytest.raises(CliInputError) as exc_info:
        parse_int("not_a_number", "test_arg")
    assert "test_arg must be an integer" in str(exc_info.value)


def test_print_item_without_datetime(capsys) -> None:
    """Test formatting item without datetime."""
    item = MockItem("task", "Buy milk")
    print_item(1, item)
    captured = capsys.readouterr()
    assert "1. [task]: Buy milk" in captured.out


def test_print_item_with_datetime(capsys) -> None:
    """Test formatting item with datetime."""
    dt = datetime(2026, 7, 16, 10, 30, 0)
    item = MockItem("note", "Test note", created_at=dt)
    print_item(2, item)
    captured = capsys.readouterr()
    assert "2. (2026-07-16 10:30:00) [note]: Test note" in captured.out


def test_print_relation(capsys) -> None:
    """Test formatting relation."""
    relation = {
        "from_index": 1,
        "to_index": 2,
        "relationship_type": "depends_on",
        "reason": "Task 2 blocks task 1",
        "is_confirmed": True,
        "from_text": "Buy milk",
        "to_text": "Check store hours",
    }
    print_relation(relation)
    captured = capsys.readouterr()
    assert "[confirmed] 1 -> 2 (depends_on): Task 2 blocks task 1" in captured.out
    assert "from: Buy milk" in captured.out
    assert "to:   Check store hours" in captured.out


def test_print_suggestion(capsys) -> None:
    """Test formatting suggestion."""
    suggestion = {
        "from_index": 1,
        "to_index": 3,
        "relationship_type": "duplicate_of",
        "score": 0.85,
        "reason": "Very similar text",
        "from_text": "Buy groceries",
        "to_text": "Purchase items",
    }
    print_suggestion(suggestion)
    captured = capsys.readouterr()
    assert "[suggested] 1 -> 3 (duplicate_of, score=0.85)" in captured.out
    assert "reason: Very similar text" in captured.out


def test_print_cluster(capsys) -> None:
    """Test formatting similarity cluster."""
    cluster = {
        "size": 2,
        "average_score": 0.82,
        "members": [
            {"index": 1, "type": "task", "text": "Buy milk"},
            {"index": 3, "type": "task", "text": "Purchase dairy"},
        ],
    }
    print_cluster(1, cluster)
    captured = capsys.readouterr()
    assert "Cluster 1 (size=2, avg_score=0.82)" in captured.out
    assert "1. [task] Buy milk" in captured.out
    assert "3. [task] Purchase dairy" in captured.out


def test_print_merge_entry(capsys) -> None:
    """Test formatting merge history entry."""
    entry = {
        "merge_id": "m123",
        "target_index": 1,
        "target_item_id": None,
        "source_indices": [2, 3],
        "source_item_ids": [None, None],
        "performed_at": "2026-07-16 10:00:00",
        "reason": "Duplicates",
        "can_undo": True,
    }
    print_merge_entry(entry)
    captured = capsys.readouterr()
    assert "[undoable]" in captured.out
    assert "merge=m123 target=1 sources=2,3" in captured.out
    assert "reason: Duplicates" in captured.out


def test_print_merge_entry_locked(capsys) -> None:
    """Test formatting merge entry marked as locked."""
    entry = {
        "merge_id": "m123",
        "target_index": 1,
        "target_item_id": None,
        "source_indices": [2],
        "source_item_ids": [None],
        "performed_at": "2026-07-16 10:00:00",
        "reason": "Merged",
        "can_undo": False,
    }
    print_merge_entry(entry)
    captured = capsys.readouterr()
    assert "[locked]" in captured.out


def test_dispatch_command_list(monkeypatch) -> None:
    """Test dispatcher routes to list command."""
    service = MagicMock()
    service.list_items.return_value = [(1, MockItem("task", "Test"))]
    
    dispatch_command(service, "list", ["all"])
    service.list_items.assert_called_once_with("all")


def test_dispatch_command_clear(monkeypatch) -> None:
    """Test dispatcher routes to clear command."""
    service = MagicMock()
    
    dispatch_command(service, "clear", [])
    service.clear_items.assert_called_once()


def test_dispatch_command_task_type(monkeypatch) -> None:
    """Test dispatcher routes explicit type command."""
    service = MagicMock()
    
    dispatch_command(service, "task", ["Buy", "milk"])
    service.add_item.assert_called_once()
    call_args = service.add_item.call_args
    assert call_args[1]["note_type"] == "task"
    assert call_args[1]["text"] == "Buy milk"


def test_dispatch_command_task_type_empty_text(monkeypatch) -> None:
    """Test dispatcher rejects task command without text."""
    service = MagicMock()
    
    with pytest.raises(CliInputError):
        dispatch_command(service, "task", [])


def test_dispatch_command_invalid_command() -> None:
    """Test dispatcher rejects unknown command."""
    service = MagicMock()
    
    with pytest.raises(CliInputError):
        dispatch_command(service, "unknown-command", [])


def test_dispatch_command_empty() -> None:
    """Test dispatcher handles empty command gracefully."""
    service = MagicMock()
    dispatch_command(service, "", [])  # Should not raise
    service.assert_not_called()
