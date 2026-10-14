from __future__ import annotations

from typing import Optional, List
from jarvis_ai.utils.logger import LOGGER
from shared.language.types import Language, DetectionResult


class LanguageDetector:
    """Unified language detector handling text using lingua-py or a fallback heuristic."""
    
    def __init__(self, languages: Optional[List[Language]] = None) -> None:
        self.languages = languages or [
            Language.ENGLISH, 
            Language.HINDI, 
            Language.TELUGU
        ]
        self._lingua_detector = None
        self._initialized = False

    def _init_lingua(self) -> None:
        if self._initialized:
            return
            
        try:
            from lingua import LanguageDetectorBuilder, Language as LinguaLang
            
            # Map our enum to lingua's enum
            lingua_langs = []
            lang_map = {
                Language.ENGLISH: LinguaLang.ENGLISH,
                Language.HINDI: LinguaLang.HINDI,
                Language.TELUGU: LinguaLang.TELUGU,
            }
            
            for lang in self.languages:
                if lang in lang_map:
                    lingua_langs.append(lang_map[lang])
                    
            if lingua_langs:
                self._lingua_detector = LanguageDetectorBuilder.from_languages(*lingua_langs).build()
                LOGGER.info("LanguageDetector: Initialized lingua-py detector.")
            else:
                LOGGER.warning("LanguageDetector: No supported languages mapped to lingua.")
                
        except (ImportError, AttributeError) as e:
            LOGGER.warning("LanguageDetector: lingua initialization failed (%s). Using fallback heuristic.", e)
            
        self._initialized = True

    def detect_text(self, text: str) -> DetectionResult:
        """Detect the language of the given text."""
        if not text or not text.strip():
            return DetectionResult(language=Language.UNKNOWN, confidence=0.0, source="text")
            
        self._init_lingua()
        
        if self._lingua_detector:
            return self._detect_with_lingua(text)
        else:
            return self._detect_heuristic(text)

    def _detect_with_lingua(self, text: str) -> DetectionResult:
        try:
            from lingua import Language as LinguaLang
            
            # Map lingua's enum back to our enum
            reverse_map = {
                LinguaLang.ENGLISH: Language.ENGLISH,
                LinguaLang.HINDI: Language.HINDI,
                LinguaLang.TELUGU: Language.TELUGU,
            }
            
            lingua_result = self._lingua_detector.detect_language_of(text)
            
            if lingua_result and lingua_result in reverse_map:
                lang = reverse_map[lingua_result]
                # Lingua doesn't expose confidence directly in detect_language_of, 
                # but we can assume high confidence if it matched.
                # (Can use compute_language_confidence_values for floats).
                LOGGER.debug("LanguageDetector: lingua detected %s", lang.name)
                return DetectionResult(language=lang, confidence=0.9, source="text")
                
            return DetectionResult(language=Language.UNKNOWN, confidence=0.0, source="text")
            
        except Exception as e:
            LOGGER.error("LanguageDetector: lingua error: %s", e)
            return self._detect_heuristic(text)

    def _detect_heuristic(self, text: str) -> DetectionResult:
        """Fallback character-set heuristic."""
        
        counts = {
            Language.HINDI: 0,
            Language.TELUGU: 0,
            Language.ENGLISH: 0
        }
        
        for char in text:
            code = ord(char)
            if 0x0900 <= code <= 0x097F:
                counts[Language.HINDI] += 1
            elif 0x0C00 <= code <= 0x0C7F:
                counts[Language.TELUGU] += 1
            elif 0x0041 <= code <= 0x005A or 0x0061 <= code <= 0x007A:
                counts[Language.ENGLISH] += 1
                
        # Find the max count
        best_lang = max(counts, key=counts.get)
        max_count = counts[best_lang]
        
        if max_count == 0:
            return DetectionResult(language=Language.UNKNOWN, confidence=0.0, source="text")
            
        # Very rough confidence based on fraction of categorized characters
        total_categorized = sum(counts.values())
        confidence = float(max_count) / float(total_categorized) if total_categorized > 0 else 0.0
        
        LOGGER.debug("LanguageDetector: heuristic detected %s with %.2f confidence", best_lang.name, confidence)
        return DetectionResult(language=best_lang, confidence=confidence, source="text")


# ---------------------------------------------------------------------------
# Global Singleton Instance
# ---------------------------------------------------------------------------
_GLOBAL_DETECTOR: Optional[LanguageDetector] = None

def get_detector() -> LanguageDetector:
    """Retrieve or create the shared global LanguageDetector instance."""
    global _GLOBAL_DETECTOR
    if _GLOBAL_DETECTOR is None:
        _GLOBAL_DETECTOR = LanguageDetector()
    return _GLOBAL_DETECTOR
