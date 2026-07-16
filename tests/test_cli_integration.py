"""Integration tests for CLI end-to-end flow with argument parsing."""

from cli.parser import parse_command_line
from cli.dispatcher import dispatch_command
from datetime import datetime


class MockServiceForIntegration:
    """Mock service for testing full CLI flow."""
    def __init__(self):
        self.last_added = None
        self.last_action = None

    def add_item(self, note_type: str, text: str, created_at: datetime) -> None:
        self.last_added = (note_type, text, created_at)
        self.last_action = "add_item"

    def add_captured_item(self, text: str, created_at: datetime, note_type: str | None = None) -> str:
        resolved = note_type or ("task" if "купить" in text.lower() else "note")
        self.last_added = (resolved, text, created_at)
        self.last_action = "add_captured_item"
        return resolved

    def list_items(self, list_type: str):
        self.last_action = ("list_items", list_type)
        return []

    def clear_items(self) -> None:
        self.last_action = "clear_items"

    def suggest_relations(self):
        self.last_action = "suggest_relations"
        return []

    def show_clusters(self):
        self.last_action = "show_clusters"
        return []

    def list_relations(self, item_index: int | None = None):
        self.last_action = ("list_relations", item_index)
        return []

    def link_items(self, from_index: int, to_index: int, relation_type: str, reason: str = "") -> None:
        self.last_action = ("link_items", from_index, to_index, relation_type, reason)

    def confirm_relation(self, from_index: int, to_index: int, relation_type: str) -> None:
        self.last_action = ("confirm_relation", from_index, to_index, relation_type)

    def reject_relation(self, from_index: int, to_index: int, relation_type: str) -> None:
        self.last_action = ("reject_relation", from_index, to_index, relation_type)

    def merge_items(self, target_index: int, source_indices: list[int], merge_reason: str = "") -> None:
        self.last_action = ("merge_items", target_index, source_indices, merge_reason)

    def list_merges(self, limit: int = 20):
        self.last_action = ("list_merges", limit)
        return []

    def undo_merge(self, merge_id: str | None = None):
        self.last_action = ("undo_merge", merge_id)
        return {
            "merge_id": merge_id or "m1",
            "target_index": 1,
            "target_item_id": "id1",
            "source_indices": [2],
            "source_item_ids": ["id2"],
            "reason": "test",
        }


def test_parse_and_dispatch_add_task():
    """Test full flow: parse argv -> dispatch -> service call."""
    argv = ["prog", "task", "Buy", "groceries"]
    parsed = parse_command_line(argv)
    
    service = MockServiceForIntegration()
    dispatch_command(service, parsed.command, parsed.args)
    
    assert service.last_action == "add_item"
    note_type, text, _ = service.last_added
    assert note_type == "task"
    assert text == "Buy groceries"


def test_parse_and_dispatch_capture():
    """Test full flow for capture command."""
    argv = ["prog", "capture", "Купить", "хлеб"]
    parsed = parse_command_line(argv)
    
    service = MockServiceForIntegration()
    dispatch_command(service, parsed.command, parsed.args)
    
    assert service.last_action == "add_captured_item"
    note_type, text, _ = service.last_added
    assert note_type == "task"
    assert text == "Купить хлеб"


def test_parse_and_dispatch_list():
    """Test full flow for list command."""
    argv = ["prog", "list", "task"]
    parsed = parse_command_line(argv)
    
    service = MockServiceForIntegration()
    dispatch_command(service, parsed.command, parsed.args)
    
    assert service.last_action == ("list_items", "task")


def test_parse_and_dispatch_link():
    """Test full flow for link-items command."""
    argv = ["prog", "link-items", "2", "5", "depends_on", "First", "task"]
    parsed = parse_command_line(argv)
    
    service = MockServiceForIntegration()
    dispatch_command(service, parsed.command, parsed.args)
    
    assert service.last_action[0] == "link_items"
    assert service.last_action[1] == 2
    assert service.last_action[2] == 5
    assert service.last_action[3] == "depends_on"
    assert service.last_action[4] == "First task"


def test_parse_and_dispatch_merge():
    """Test full flow for merge-items command."""
    argv = ["prog", "merge-items", "1", "2", "3", "--reason", "All", "same"]
    parsed = parse_command_line(argv)
    
    service = MockServiceForIntegration()
    dispatch_command(service, parsed.command, parsed.args)
    
    assert service.last_action[0] == "merge_items"
    assert service.last_action[1] == 1
    assert service.last_action[2] == [2, 3]
    assert service.last_action[3] == "All same"


def test_parse_case_insensitive():
    """Test that command parsing is case-insensitive."""
    argv = ["prog", "TASK", "Something"]
    parsed = parse_command_line(argv)
    
    assert parsed.command == "task"
    assert parsed.args == ["Something"]


def test_parse_preserves_multi_word_args():
    """Test that multi-word arguments are preserved as separate items."""
    argv = ["prog", "capture", "This", "is", "a", "multi-word", "entry"]
    parsed = parse_command_line(argv)
    
    assert parsed.command == "capture"
    assert parsed.args == ["This", "is", "a", "multi-word", "entry"]
