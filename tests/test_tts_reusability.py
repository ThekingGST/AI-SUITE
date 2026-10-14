import unittest
import time
import threading

from jarvis_ai.voice.v2.speech_manager import SpeechManager
from jarvis_ai.voice.v2.events import VoiceEventBus, VoiceEvent
from jarvis_ai.voice.v2.backends.registry import TTSBackendRegistry
from jarvis_ai.voice.v2.profile import DEFAULT_PROFILES
from jarvis_ai.voice.v2.types import SpeechPriority
from shared.language.detector import get_detector

# Note: In a real test, we might want to mock the backend, but we can also rely
# on a mock registry or Edge-TTS failing gracefully/pyttsx3 responding.
# For isolation, we'll register a mock backend.
from jarvis_ai.voice.v2.backends.base import TTSBackend
from jarvis_ai.voice.v2.capabilities import BackendCapabilities, BackendHealth

class MockTTSBackend(TTSBackend):
    def __init__(self):
        self._health = BackendHealth()
        self._caps = BackendCapabilities(supports_streaming=False, offline=True)
        self.speak_calls = 0

    def initialize(self):
        self._health.record_success()

    def speak(self, text: str, abort: threading.Event = None):
        self.speak_calls += 1
        time.sleep(0.1)  # Simulate short speech

    def get_capabilities(self):
        return self._caps

    def get_health(self):
        return self._health

    def is_available(self):
        return self._health.is_available

    def engine_name(self):
        return "mock_tts"

    def close(self):
        pass


class TestTTSReusability(unittest.TestCase):
    def setUp(self):
        self.registry = TTSBackendRegistry()
        self.mock_backend = MockTTSBackend()
        self.registry.register("edge-tts", self.mock_backend) # override default
        self.registry.register("pyttsx3", self.mock_backend)
        
        self.bus = VoiceEventBus()
        self.sm = SpeechManager(self.registry, self.bus)
        self.sm.set_profile(DEFAULT_PROFILES['natural'])
        self.sm.start()
        
        self.finished_events = 0
        self.bus.subscribe(VoiceEvent.SPEECH_FINISHED, self._on_finished)

    def _on_finished(self, payload):
        if payload.data.get("job_id") != "stream_end":
            self.finished_events += 1

    def tearDown(self):
        self.sm.close()

    def test_consecutive_tts_responses(self):
        # Enqueue 3 responses in a row
        self.sm.enqueue("Test one", SpeechPriority.NORMAL)
        self.sm.enqueue("Test two", SpeechPriority.NORMAL)
        self.sm.enqueue("Test three", SpeechPriority.NORMAL)
        
        # Give worker thread time to process all 3
        time.sleep(1.0)
        
        self.assertEqual(self.mock_backend.speak_calls, 3)
        self.assertEqual(self.finished_events, 3)
        self.assertTrue(self.sm.is_idle)

    def test_language_detector_singleton(self):
        d1 = get_detector()
        d2 = get_detector()
        self.assertIs(d1, d2)
        
        # Make sure it can process english correctly
        res_en = d1.detect_text("Jarvis, how are you?")
        self.assertEqual(res_en.language.code, "en")
        
        # Make sure it can process hindi correctly
        res_hi = d1.detect_text("जार्विस, मेरा नाम क्या है?")
        self.assertEqual(res_hi.language.code, "hi")
        
        # Make sure it can process telugu correctly
        res_te = d1.detect_text("జార్విస్, నా పేరు ఏమిటి?")
        self.assertEqual(res_te.language.code, "te")

if __name__ == '__main__':
    unittest.main()
