import unittest
from unittest.mock import patch

from jarvis_ai.voice.input.stt.faster_whisper_backend import FasterWhisperBackend
from jarvis_ai.voice.input.profile import AudioProfile
from jarvis_ai.voice.v2.backends.kokoro_backend import KokoroBackend
from jarvis_ai.voice.v2.backends.piper_backend import PiperBackend

class TestModelLifecycle(unittest.TestCase):
    @patch("jarvis_ai.voice.input.stt.faster_whisper_backend.FASTER_WHISPER_AVAILABLE", False)
    def test_whisper_missing_model(self):
        profile = AudioProfile(name="test")
        backend = FasterWhisperBackend(profile)
        # Attempting to load without the package/model should fail gracefully
        with self.assertRaises(ImportError):
            backend._load_model()
        # Should not crash if close is called
        backend.close()

    def test_kokoro_lifecycle(self):
        backend = KokoroBackend()
        success = backend._load_model()
        self.assertFalse(success)
        backend.close()

    def test_piper_lifecycle(self):
        backend = PiperBackend()
        success = backend._load_model()
        self.assertFalse(success)
        backend.close()

if __name__ == '__main__':
    unittest.main()
