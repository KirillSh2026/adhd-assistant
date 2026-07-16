"""Text capture and audio dictation commands."""

from datetime import datetime

from services.item_service_registry import ItemServiceRegistry
from services.speech_to_text_service import SpeechToTextService
from services.item_type_classifier import SUPPORTED_ITEM_TYPES
from config.settings import get_settings
from core.exceptions import CliInputError


def add_from_text_capture(service: ItemServiceRegistry, args: list[str]) -> None:
    """Add item from captured text with automatic type detection."""
    text = " ".join(args).strip()
    if not text:
        raise CliInputError('Usage: python app/main.py capture "text to classify"')
    
    resolved_type = service.add_captured_item(text=text, created_at=datetime.now())
    print(f"Added captured item: [{resolved_type}] {text}")


def add_from_dictation(service: ItemServiceRegistry, args: list[str]) -> None:
    """Add item from audio dictation (microphone or file) with optional explicit type."""
    note_type = None
    audio_path = ""
    
    if args and args[0].lower() in SUPPORTED_ITEM_TYPES:
        note_type = args[0].lower()
        audio_path = " ".join(args[1:]).strip()
    else:
        audio_path = " ".join(args).strip()
    
    language = get_settings().adhd_dictate_language
    speech_service = SpeechToTextService(language=language)
    
    if audio_path:
        text = speech_service.transcribe_audio_file(audio_path)
    else:
        text = speech_service.transcribe_microphone()
    
    resolved_type = service.add_captured_item(text=text, created_at=datetime.now(), note_type=note_type)
    print(f"Added from dictation: [{resolved_type}] {text}")
