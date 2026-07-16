"""Tests for CLI command handlers - argument parsing and execution without sys.argv."""

from datetime import datetime

from cli.commands import capture_commands
from cli.commands import relation_commands
from cli.commands import merge_commands
from cli.commands import list_items, clear_items, add_item_by_type


class FakeService:
    def __init__(self):
        self.calls = []
        self.link_calls = []
        self.confirm_calls = []
        self.reject_calls = []
        self.merge_calls = []
        self.list_merges_calls = []
        self.undo_merge_calls = []
        self.relations_result = []
        self.suggestions_result = []
        self.clusters_result = []
        self.merges_result = []

    def add_item(self, note_type: str, text: str) -> None:
        self.calls.append((note_type, text))

    def add_captured_item(self, text: str, created_at: datetime, note_type: str | None = None) -> str:
        if note_type is None:
            if "купить" in text.lower():
                note_type = "task"
            elif "идея" in text.lower():
                note_type = "idea"
            else:
                note_type = "note"
        self.calls.append((note_type, text, created_at))
        return note_type

    def clear_items(self) -> None:
        raise AssertionError("clear_items should not be called in these tests")

    def list_items(self, list_type: str):
        raise AssertionError("list_items should not be called in these tests")

    def suggest_relations(self):
        return self.suggestions_result

    def show_clusters(self):
        return self.clusters_result

    def list_relations(self, item_index: int | None = None):
        self.calls.append(("list_relations", item_index, None))
        return self.relations_result

    def link_items(self, from_index: int, to_index: int, relation_type: str, reason: str = "") -> None:
        self.link_calls.append((from_index, to_index, relation_type, reason))

    def confirm_relation(self, from_index: int, to_index: int, relation_type: str) -> None:
        self.confirm_calls.append((from_index, to_index, relation_type))

    def reject_relation(self, from_index: int, to_index: int, relation_type: str) -> None:
        self.reject_calls.append((from_index, to_index, relation_type))

    def merge_items(self, target_index: int, source_indices: list[int], merge_reason: str = "") -> None:
        self.merge_calls.append((target_index, source_indices, merge_reason))

    def list_merges(self, limit: int = 20):
        self.list_merges_calls.append(limit)
        return self.merges_result

    def undo_merge(self, merge_id: str | None = None):
        self.undo_merge_calls.append(merge_id)
        return {
            "merge_id": merge_id or "m1",
            "target_index": 1,
            "target_item_id": "id1",
            "source_indices": [2],
            "source_item_ids": ["id2"],
            "reason": "test",
        }


def test_dictate_from_file_adds_item(monkeypatch):
    """Test dictation from audio file with automatic type classification."""
    fake_service = FakeService()

    class FakeSpeechToTextService:
        def __init__(self, language: str = "ru-RU", timeout: int = 8, phrase_time_limit: int = 30):
            self.language = language
            self.timeout = timeout
            self.phrase_time_limit = phrase_time_limit

        def transcribe_audio_file(self, audio_path: str) -> str:
            assert audio_path == "voice.wav"
            return "Купить молоко"

        def transcribe_microphone(self) -> str:
            raise AssertionError("Microphone branch should not be used")

    monkeypatch.setattr(capture_commands, "SpeechToTextService", FakeSpeechToTextService)
    capture_commands.add_from_dictation(fake_service, ["voice.wav"])

    assert len(fake_service.calls) == 1
    note_type, text, created_at = fake_service.calls[0]
    assert note_type == "task"
    assert text == "Купить молоко"
    assert isinstance(created_at, datetime)


def test_dictate_from_microphone_adds_item(monkeypatch):
    """Test dictation from microphone with automatic type classification."""
    fake_service = FakeService()

    class FakeSpeechToTextService:
        def __init__(self, language: str = "ru-RU", timeout: int = 8, phrase_time_limit: int = 30):
            self.language = language
            self.timeout = timeout
            self.phrase_time_limit = phrase_time_limit

        def transcribe_audio_file(self, audio_path: str) -> str:
            raise AssertionError("File branch should not be used")

        def transcribe_microphone(self) -> str:
            return "Идея на потом"

    monkeypatch.setattr(capture_commands, "SpeechToTextService", FakeSpeechToTextService)
    capture_commands.add_from_dictation(fake_service, [])

    assert len(fake_service.calls) == 1
    note_type, text, created_at = fake_service.calls[0]
    assert note_type == "idea"
    assert text == "Идея на потом"
    assert isinstance(created_at, datetime)


def test_capture_text_auto_classifies_item():
    """Test text capture with automatic type classification."""
    fake_service = FakeService()
    capture_commands.add_from_text_capture(fake_service, ["Купить", "лекарства"])

    assert len(fake_service.calls) == 1
    note_type, text, created_at = fake_service.calls[0]
    assert note_type == "task"
    assert text == "Купить лекарства"
    assert isinstance(created_at, datetime)


def test_dictate_allows_manual_type_override(monkeypatch):
    """Test dictation with explicit type override."""
    fake_service = FakeService()

    class FakeSpeechToTextService:
        def __init__(self, language: str = "ru-RU", timeout: int = 8, phrase_time_limit: int = 30):
            self.language = language
            self.timeout = timeout
            self.phrase_time_limit = phrase_time_limit

        def transcribe_audio_file(self, audio_path: str) -> str:
            assert audio_path == "voice.wav"
            return "Идея на потом"

        def transcribe_microphone(self) -> str:
            raise AssertionError("Microphone branch should not be used")

    monkeypatch.setattr(capture_commands, "SpeechToTextService", FakeSpeechToTextService)
    capture_commands.add_from_dictation(fake_service, ["task", "voice.wav"])

    assert len(fake_service.calls) == 1
    note_type, text, created_at = fake_service.calls[0]
    assert note_type == "task"
    assert text == "Идея на потом"
    assert isinstance(created_at, datetime)


def test_link_items_passes_relation_arguments():
    """Test link-items parses and passes arguments correctly."""
    fake_service = FakeService()
    relation_commands.link_items(fake_service, ["2", "5", "depends_on", "Сначала", "нужна", "база"])

    assert len(fake_service.link_calls) == 1
    from_index, to_index, rel_type, reason = fake_service.link_calls[0]
    assert from_index == 2
    assert to_index == 5
    assert rel_type == "depends_on"
    assert reason == "Сначала нужна база"


def test_merge_items_parses_reason():
    """Test merge-items extracts and passes reason correctly."""
    fake_service = FakeService()
    merge_commands.merge_items(fake_service, ["1", "3", "--reason", "Объединяем", "дубликаты"])

    assert len(fake_service.merge_calls) == 1
    target_index, source_indices, reason = fake_service.merge_calls[0]
    assert target_index == 1
    assert source_indices == [3]
    assert reason == "Объединяем дубликаты"


def test_reject_relation_passes_relation_arguments():
    """Test reject-relation passes arguments correctly."""
    fake_service = FakeService()
    relation_commands.reject_relation(fake_service, ["1", "3", "duplicate_of"])

    assert len(fake_service.reject_calls) == 1
    from_index, to_index, rel_type = fake_service.reject_calls[0]
    assert from_index == 1
    assert to_index == 3
    assert rel_type == "duplicate_of"


def test_undo_merge_passes_merge_id():
    """Test undo-merge passes merge_id correctly."""
    fake_service = FakeService()
    merge_commands.undo_merge(fake_service, ["merge123"])

    assert len(fake_service.undo_merge_calls) == 1
    assert fake_service.undo_merge_calls[0] == "merge123"


def test_list_merges_parses_limit():
    """Test list-merges parses limit argument correctly."""
    fake_service = FakeService()
    merge_commands.list_merges(fake_service, ["50"])

    assert len(fake_service.list_merges_calls) == 1
    assert fake_service.list_merges_calls[0] == 50
