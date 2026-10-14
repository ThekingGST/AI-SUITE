import unittest
import threading

from jarvis_ai.voice.v2.profile import DEFAULT_PROFILES
from shared.language.tts_router import TTSRouter
from jarvis_ai.voice.v2.backends.registry import TTSBackendRegistry
from jarvis_ai.voice.v2.backends.kokoro_backend import KokoroBackend
from jarvis_ai.voice.v2.backends.piper_backend import PiperBackend


class TestTTS(unittest.TestCase):
    def test_tts_router_fallback(self):
        router = TTSRouter()
        default = DEFAULT_PROFILES["jarvis"]
        
        # Test English
        prof = router.resolve_profile("Hello there", default)
        self.assertEqual(prof, default)
        
        # Test non-English but unsure -> English
        prof2 = router.resolve_profile("something ambiguous", default)
        self.assertEqual(prof2, default)
        
    def test_kokoro_backend_init(self):
        backend = KokoroBackend()
        backend.apply_profile(DEFAULT_PROFILES["hindi"])
        self.assertEqual(backend.engine_name(), "kokoro")
        success = backend._load_model()
        self.assertFalse(success) # Should fail because model isn't downloaded yet
        health = backend.get_health()
        self.assertFalse(health.is_available)
        
    def test_piper_backend_init(self):
        backend = PiperBackend()
        backend.apply_profile(DEFAULT_PROFILES["telugu"])
        self.assertEqual(backend.engine_name(), "piper")
        success = backend._load_model()
        self.assertFalse(success) # Should fail because model isn't downloaded yet
        health = backend.get_health()
        self.assertFalse(health.is_available)

    def test_tts_registry(self):
        registry = TTSBackendRegistry()
        backend1 = KokoroBackend()
        registry.register("kokoro", backend1)
        self.assertIs(registry.get_backend("kokoro"), backend1)
        
if __name__ == '__main__':
    unittest.main()
