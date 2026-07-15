from config.settings import AppSettings


def test_settings_reads_environment(monkeypatch):
    monkeypatch.setenv("ADHD_STORAGE_BACKEND", "postgres")
    monkeypatch.setenv("ADHD_NOTES_PATH", "custom/notes.json")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/app")
    monkeypatch.setenv("ADHD_DICTATE_LANGUAGE", "en-US")

    settings = AppSettings()

    assert settings.adhd_storage_backend == "postgres"
    assert settings.adhd_notes_path == "custom/notes.json"
    assert settings.database_url == "postgresql://user:pass@localhost:5432/app"
    assert settings.adhd_dictate_language == "en-US"
