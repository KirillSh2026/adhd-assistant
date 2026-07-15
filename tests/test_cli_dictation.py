from datetime import datetime

import app.main as cli_main


class FakeService:
    def __init__(self):
        self.calls = []
        self.link_calls = []
        self.confirm_calls = []
        self.merge_calls = []
        self.relations_result = []
        self.suggestions_result = []
        self.clusters_result = []

    def add_item(self, note_type: str, text: str, created_at: datetime) -> None:
        self.calls.append((note_type, text, created_at))

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
        raise AssertionError("clear_items should not be called in dictation tests")

    def list_items(self, list_type: str):
        raise AssertionError("list_items should not be called in dictation tests")

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

    def merge_items(self, target_index: int, source_indices: list[int], merge_reason: str = "") -> None:
        self.merge_calls.append((target_index, source_indices, merge_reason))


def test_dictate_from_file_adds_item(monkeypatch):
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

    monkeypatch.setattr(cli_main, "get_service", lambda: fake_service)
    monkeypatch.setattr(cli_main, "SpeechToTextService", FakeSpeechToTextService)
    monkeypatch.setattr(cli_main.sys, "argv", ["main.py", "dictate", "voice.wav"])

    cli_main.main()

    assert len(fake_service.calls) == 1
    note_type, text, created_at = fake_service.calls[0]
    assert note_type == "task"
    assert text == "Купить молоко"
    assert isinstance(created_at, datetime)


def test_dictate_from_microphone_adds_item(monkeypatch):
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

    monkeypatch.setattr(cli_main, "get_service", lambda: fake_service)
    monkeypatch.setattr(cli_main, "SpeechToTextService", FakeSpeechToTextService)
    monkeypatch.setattr(cli_main.sys, "argv", ["main.py", "dictate"])

    cli_main.main()

    assert len(fake_service.calls) == 1
    note_type, text, created_at = fake_service.calls[0]
    assert note_type == "idea"
    assert text == "Идея на потом"
    assert isinstance(created_at, datetime)


def test_capture_text_auto_classifies_item(monkeypatch):
    fake_service = FakeService()

    monkeypatch.setattr(cli_main, "get_service", lambda: fake_service)
    monkeypatch.setattr(cli_main.sys, "argv", ["main.py", "capture", "Купить", "лекарства"])

    cli_main.main()

    assert len(fake_service.calls) == 1
    note_type, text, created_at = fake_service.calls[0]
    assert note_type == "task"
    assert text == "Купить лекарства"
    assert isinstance(created_at, datetime)


def test_dictate_allows_manual_type_override(monkeypatch):
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

    monkeypatch.setattr(cli_main, "get_service", lambda: fake_service)
    monkeypatch.setattr(cli_main, "SpeechToTextService", FakeSpeechToTextService)
    monkeypatch.setattr(cli_main.sys, "argv", ["main.py", "dictate", "task", "voice.wav"])

    cli_main.main()

    assert len(fake_service.calls) == 1
    note_type, text, created_at = fake_service.calls[0]
    assert note_type == "task"
    assert text == "Идея на потом"
    assert isinstance(created_at, datetime)


def test_link_items_passes_relation_arguments(monkeypatch):
    fake_service = FakeService()

    monkeypatch.setattr(cli_main, "get_service", lambda: fake_service)
    monkeypatch.setattr(
        cli_main.sys,
        "argv",
        ["main.py", "link-items", "2", "5", "depends_on", "Нужно", "сначала", "закончить", "базу"],
    )

    cli_main.main()

    assert fake_service.link_calls == [(2, 5, "depends_on", "Нужно сначала закончить базу")]


def test_merge_items_parses_reason(monkeypatch):
    fake_service = FakeService()

    monkeypatch.setattr(cli_main, "get_service", lambda: fake_service)
    monkeypatch.setattr(
        cli_main.sys,
        "argv",
        ["main.py", "merge-items", "2", "4", "6", "--reason", "Объединяем", "дубликаты"],
    )

    cli_main.main()

    assert fake_service.merge_calls == [(2, [4, 6], "Объединяем дубликаты")]
