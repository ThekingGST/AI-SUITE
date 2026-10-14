from __future__ import annotations

from jarvis_ai.utils.logger import LOGGER
from jarvis_ai.voice.v2.profile import VoiceProfile, DEFAULT_PROFILES
from shared.language.detector import LanguageDetector
from shared.language.types import Language

class TTSRouter:
    def __init__(self):
        self.detector = LanguageDetector()

    def resolve_profile(self, text: str, default_profile: VoiceProfile) -> VoiceProfile:
        """Determines the best voice profile for the given text based on language detection."""
        if not text:
            return default_profile
            
        res = self.detector.detect_text(text)
        if res.language == Language.UNKNOWN or res.language == Language.ENGLISH:
            return default_profile
            
        LOGGER.info("TTSRouter: Detected non-English text (%s, confidence %.2f)", res.language.name, res.confidence)
        
        if res.language == Language.HINDI:
            return DEFAULT_PROFILES.get("hindi", default_profile)
        elif res.language == Language.TELUGU:
            return DEFAULT_PROFILES.get("telugu", default_profile)
            
        return default_profile
