from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Language(Enum):
    """Supported languages in the AI Suite."""
    
    ENGLISH = ("en", "English", "English")
    HINDI = ("hi", "Hindi", "हिन्दी")
    TELUGU = ("te", "Telugu", "తెలుగు")
    UNKNOWN = ("unk", "Unknown", "Unknown")

    def __init__(self, code: str, name_en: str, native_name: str) -> None:
        self.code = code
        self.name_en = name_en
        self.native_name = native_name

    @classmethod
    def from_code(cls, code: str) -> Language:
        """Map a language code (e.g. 'en', 'hi') to the Enum."""
        if not code:
            return cls.UNKNOWN
            
        code = code.lower().strip()
        for lang in cls:
            if lang.code == code:
                return lang
                
        return cls.UNKNOWN


@dataclass
class DetectionResult:
    """Result of language detection."""
    language: Language
    confidence: float
    source: str  # e.g. 'audio', 'text', 'user_override'


@dataclass
class TranscriptionResult:
    """Result of speech-to-text with language metadata."""
    text: str
    language: Language
    language_confidence: float
    is_partial: bool = False
