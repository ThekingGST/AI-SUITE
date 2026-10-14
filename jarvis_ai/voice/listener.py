from __future__ import annotations

import json
import queue
import threading
from typing import Callable

from config import CONFIG, MODELS_DIR
from utils.logger import LOGGER


class VoiceListener:
    """Continuous Vosk listener that emits recognized phrases from a background thread."""

    def __init__(self, on_text: Callable[[str], None]) -> None:
        self.on_text = on_text
        self._stop = threading.Event()
        self._paused = threading.Event()
        self._thread: threading.Thread | None = None
        self.available = False
        self.error: str | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            self.resume()
            return
        self._stop.clear()
        self.resume()
        self._thread = threading.Thread(target=self._run, name="JarvisVoiceListener", daemon=True)
        self._thread.start()
        LOGGER.info("MIC STARTED")

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
        LOGGER.info("MIC STOPPED")

    def pause(self) -> None:
        self._paused.set()
        LOGGER.info("MIC PAUSED")

    def resume(self) -> None:
        self._paused.clear()
        LOGGER.info("MIC RESUMED")

    def _run(self) -> None:
        try:
            import pyaudio
            from vosk import KaldiRecognizer, Model
        except Exception as exc:
            self.error = f"Voice dependencies unavailable: {exc}"
            LOGGER.warning(self.error)
            LOGGER.info("MIC STOPPED")
            return

        model_path = MODELS_DIR / "vosk-model"
        if not model_path.exists():
            self.error = f"Vosk model missing at {model_path}"
            LOGGER.warning(self.error)
            LOGGER.info("MIC STOPPED")
            return

        audio = None
        stream = None
        try:
            model = Model(str(model_path))
            recognizer = KaldiRecognizer(model, CONFIG.voice.sample_rate)
            recognizer.SetWords(False)
            audio = pyaudio.PyAudio()
            stream = audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=CONFIG.voice.sample_rate,
                input=True,
                frames_per_buffer=CONFIG.voice.frame_size,
            )
            stream.start_stream()
            self.available = True
            LOGGER.info("Voice listener online.")
            while not self._stop.is_set():
                data = stream.read(CONFIG.voice.frame_size, exception_on_overflow=False)
                if recognizer.AcceptWaveform(data):
                    if self._paused.is_set():
                        continue
                    payload = json.loads(recognizer.Result())
                    text = payload.get("text", "").strip()
                    if text:
                        LOGGER.info("VOICE DETECTED: %s", text)
                        self.on_text(text)
        except Exception as exc:
            self.error = str(exc)
            LOGGER.warning("Voice listener failed: %s", exc)
        finally:
            if stream:
                stream.stop_stream()
                stream.close()
            if audio:
                audio.terminate()
            self.available = False
            LOGGER.info("MIC STOPPED")


class TextCommandBus:
    """A simple queue used by UI, tests, and voice recognition to submit commands."""

    def __init__(self) -> None:
        self.queue: queue.Queue[str] = queue.Queue()

    def submit(self, text: str) -> None:
        self.queue.put(text)

    def get(self, timeout: float = 0.1) -> str | None:
        try:
            return self.queue.get(timeout=timeout)
        except queue.Empty:
            return None
