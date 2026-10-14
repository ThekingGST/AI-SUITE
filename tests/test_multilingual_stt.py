import unittest
from unittest.mock import MagicMock, patch

from shared.language.types import Language
from shared.language.detector import LanguageDetector
from shared.models.model_registry import ModelRegistry, ModelCategory, ModelInfo
from jarvis_ai.voice.input.stt.backend_router import STTBackendRouter
from jarvis_ai.voice.input.profile import DEFAULT_PROFILES


class TestMultilingualSTT(unittest.TestCase):
    
    def test_language_enum(self):
        self.assertEqual(Language.from_code("en"), Language.ENGLISH)
        self.assertEqual(Language.from_code("hi"), Language.HINDI)
        self.assertEqual(Language.from_code("te"), Language.TELUGU)
        self.assertEqual(Language.from_code("unknown_code"), Language.UNKNOWN)

    def test_heuristic_language_detector(self):
        detector = LanguageDetector()
        
        # Test English
        res = detector.detect_text("Hello Jarvis, how are you?")
        self.assertEqual(res.language, Language.ENGLISH)
        
        # Test Hindi (Devanagari)
        res = detector.detect_text("जार्विस, मेरा नाम क्या है?")
        self.assertEqual(res.language, Language.HINDI)
        
        # Test Telugu
        res = detector.detect_text("జార్విస్, నా పేరు ఏమిటి?")
        self.assertEqual(res.language, Language.TELUGU)

    def test_model_registry(self):
        registry = ModelRegistry()
        models = registry.list_models()
        self.assertTrue(len(models) > 0)
        
        # Test that we support large-v3-turbo implicitly or explicitly
        # In a real setup, we might have multiple whisper models registered
        whisper_info = registry.get_info("whisper-large-v3-turbo") or registry.get_info("whisper-small")
        if whisper_info:
            self.assertEqual(whisper_info.category, ModelCategory.STT)
            self.assertEqual(whisper_info.gpu_capable, True)

    @patch("jarvis_ai.voice.input.stt.faster_whisper_backend.FASTER_WHISPER_AVAILABLE", False)
    @patch("jarvis_ai.voice.input.stt.vosk_backend.VOSK_AVAILABLE", True)
    def test_stt_backend_router_fallback(self):
        profile = DEFAULT_PROFILES["office"]
        router = STTBackendRouter(profile, preferred_backend="auto")
        
        # If whisper is unavailable, it should fall back to Vosk
        self.assertEqual(router.get_active_backend(), "vosk")

    @patch("jarvis_ai.voice.input.stt.faster_whisper_backend.FASTER_WHISPER_AVAILABLE", True)
    @patch("jarvis_ai.voice.input.stt.vosk_backend.VOSK_AVAILABLE", True)
    def test_stt_backend_router_language_forcing(self):
        profile = DEFAULT_PROFILES["office"]
        router = STTBackendRouter(profile, preferred_backend="auto")
        
        # Test Telugu forcing (should select whisper strictly)
        router.set_language("te")
        self.assertEqual(router.get_active_backend(), "whisper")
        
        # Test English forcing (should allow auto, which selects whisper or vosk)
        router.set_language("en")
        self.assertIn(router.get_active_backend(), ["whisper", "vosk"])
        
    @patch("jarvis_ai.voice.input.stt.faster_whisper_backend.FASTER_WHISPER_AVAILABLE", False)
    @patch("jarvis_ai.voice.input.stt.vosk_backend.VOSK_AVAILABLE", True)
    def test_stt_backend_router_missing_multilingual(self):
        profile = DEFAULT_PROFILES["office"]
        router = STTBackendRouter(profile, preferred_backend="auto")
        
        # Test Hindi forcing when Whisper is missing
        # It should NOT fall back to Vosk. It should fail and set backend to none.
        router.set_language("hi")
        self.assertEqual(router.get_active_backend(), "none")

if __name__ == '__main__':
    unittest.main()
