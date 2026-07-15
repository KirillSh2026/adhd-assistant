from __future__ import annotations

from pathlib import Path


def _load_speech_recognition():
    try:
        import speech_recognition as sr
    except ImportError as exc:
        raise RuntimeError(
            "speech_recognition dependency is required for dictation. "
            "Install dependencies with: pip install -r requirements.txt"
        ) from exc
    return sr


class SpeechToTextService:
    def __init__(self, language: str = "ru-RU", timeout: int = 8, phrase_time_limit: int = 30):
        self.language = language
        self.timeout = timeout
        self.phrase_time_limit = phrase_time_limit

    def _recognize(self, recognizer, audio) -> str:
        sr = _load_speech_recognition()
        try:
            text = recognizer.recognize_google(audio, language=self.language)
        except sr.UnknownValueError as exc:
            raise ValueError("Could not recognize speech. Please repeat more clearly.") from exc
        except sr.RequestError as exc:
            raise RuntimeError(f"Speech recognition request failed: {exc}") from exc

        normalized = text.strip()
        if not normalized:
            raise ValueError("Recognized text is empty.")
        return normalized

    def transcribe_audio_file(self, audio_path: str) -> str:
        sr = _load_speech_recognition()
        path = Path(audio_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file does not exist: {audio_path}")

        recognizer = sr.Recognizer()
        with sr.AudioFile(str(path)) as source:
            audio = recognizer.record(source)
        return self._recognize(recognizer=recognizer, audio=audio)

    def transcribe_microphone(self) -> str:
        sr = _load_speech_recognition()
        recognizer = sr.Recognizer()

        try:
            microphone = sr.Microphone()
        except OSError as exc:
            raise RuntimeError(
                "Microphone is unavailable. Connect a microphone or pass an audio file path."
            ) from exc

        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            try:
                audio = recognizer.listen(
                    source,
                    timeout=self.timeout,
                    phrase_time_limit=self.phrase_time_limit,
                )
            except sr.WaitTimeoutError as exc:
                raise ValueError("No speech detected within timeout window.") from exc

        return self._recognize(recognizer=recognizer, audio=audio)
