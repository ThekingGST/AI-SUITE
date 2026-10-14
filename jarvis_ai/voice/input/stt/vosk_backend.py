from __future__ import annotations

import json
from pathlib import Path

from jarvis_ai.config import CONFIG, MODELS_DIR
from jarvis_ai.utils.logger import LOGGER
from jarvis_ai.voice.input.events import AudioEvent
from jarvis_ai.voice.input.profile import AudioProfile
from jarvis_ai.voice.input.stt.base import STTBackend

try:
    from vosk import KaldiRecognizer, Model
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False


class VoskBackend(STTBackend):
    """Local, offline Speech-to-Text using Vosk."""

    def __init__(self, profile: AudioProfile, sample_rate: int = 16000) -> None:
        super().__init__(profile)
        self.sample_rate = sample_rate
        
        if not VOSK_AVAILABLE:
            raise ImportError("vosk is not installed.")
            
        model_path = MODELS_DIR / "vosk-model"
        if not model_path.exists():
            raise FileNotFoundError(f"Vosk model missing at {model_path}")
            
        try:
            self._model = Model(str(model_path))
            self._recognizer = KaldiRecognizer(self._model, self.sample_rate)
            self._recognizer.SetWords(False)
            LOGGER.info("VoskBackend initialized successfully.")
        except Exception as exc:
            raise RuntimeError(f"Failed to load Vosk model: {exc}")

    def process_audio_chunk(self, data: bytes) -> None:
        import threading
        import time
        self._trace_count = getattr(self, "_trace_count", 0) + 1
        try:
            if self._recognizer.AcceptWaveform(data):
                # Full result available
                raw_result = self._recognizer.Result()
                payload = json.loads(raw_result)
                text = payload.get("text", "").strip()
                if text and self.event_bus:

                    self.event_bus.emit(AudioEvent.RECOGNITION_FINISHED, {"text": text})
            else:
                # Partial result
                partial = json.loads(self._recognizer.PartialResult())
                partial_text = partial.get("partial", "").strip()
                if partial_text:
                    if self.event_bus:
                        self.event_bus.emit(AudioEvent.PARTIAL_TRANSCRIPT, {"text": partial_text})
        except Exception as exc:
            LOGGER.warning("VoskBackend processing error: %s", exc)
            if self.event_bus:
                self.event_bus.emit(AudioEvent.RECOGNITION_FAILED, {"error": str(exc)})

    def finalize_recognition(self) -> None:
        """Force finalize current utterance if VAD decides speech ended."""
        try:
            raw_result = self._recognizer.FinalResult()
            LOGGER.info("RAW RESULT:\n%s", raw_result)
            
            payload = json.loads(raw_result)
            text = payload.get("text", "").strip()
            LOGGER.info("Parsed transcript: '%s'", text)
            
            if not text:
                LOGGER.info("Parsed transcript was empty because payload did not contain text or it was all whitespace.")
            
            if text and self.event_bus:
                LOGGER.info("Vosk:\nFinal transcript: %s", text)
                LOGGER.info("Emitting RecognitionFinished\nTranscript:\n%s", text)
                self.event_bus.emit(AudioEvent.RECOGNITION_FINISHED, {"text": text})
        except Exception as exc:
            LOGGER.warning("VoskBackend finalize error: %s", exc)
