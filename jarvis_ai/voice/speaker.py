from __future__ import annotations

import queue
import re
import threading
import time
from dataclasses import dataclass
from typing import Any

from config import CONFIG, DATA_DIR
from utils.logger import LOGGER

# ---------------------------------------------------------------------------
# Voice-mode persistence
# ---------------------------------------------------------------------------

_VOICE_MODE_FILE = DATA_DIR / "voice_mode.txt"

_MODE_TO_ENGINE = {
    "standard": "pyttsx3",
    "premium": "elevenlabs",
}


def _load_voice_mode() -> str:
    """Load persisted voice mode.  Returns ``'standard'`` or ``'premium'``."""
    try:
        mode = _VOICE_MODE_FILE.read_text(encoding="utf-8").strip().lower()
        if mode in _MODE_TO_ENGINE:
            return mode
    except (FileNotFoundError, OSError):
        pass
    return "standard"


def _save_voice_mode(mode: str) -> None:
    """Persist the current voice mode to disk."""
    try:
        _VOICE_MODE_FILE.write_text(mode, encoding="utf-8")
    except OSError as exc:
        LOGGER.warning("Failed to save voice mode: %s", exc)


# ---------------------------------------------------------------------------
# Speech job
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SpeechJob:
    text: str | None = None
    shutdown: bool = False
    switch_mode: str | None = None  # "standard" or "premium"


# ---------------------------------------------------------------------------
# Speaker
# ---------------------------------------------------------------------------

class Speaker:
    """Queue-based TTS manager with ElevenLabs primary + pyttsx3 failover.

    pyttsx3/SAPI objects are created and used only on the worker thread. Other
    threads communicate by queueing SpeechJob objects, which keeps UI and
    command routing asynchronous and avoids COM ownership problems.

    The public interface (speak, say, is_speaking, enabled, recently_spoke,
    interrupt, close) is **identical** to the original pyttsx3-only Speaker.
    """

    def __init__(self) -> None:
        self._queue: queue.Queue[SpeechJob] = queue.Queue()
        self._state_lock = threading.RLock()
        self._enabled = True
        self._speaking = False
        self._last_spoken_at = 0.0
        self._ready = threading.Event()
        self._tts_manager: Any | None = None
        self._voice_mode: str = _load_voice_mode()
        self._thread = threading.Thread(target=self._run, name="JarvisTTSWorker", daemon=True)
        self._thread.start()
        self.speak("Systems online.")

    # -- public properties ----------------------------------------------------

    @property
    def enabled(self) -> bool:
        with self._state_lock:
            return self._enabled

    @property
    def is_speaking(self) -> bool:
        with self._state_lock:
            return self._speaking

    @property
    def active_engine_name(self) -> str:
        """Name of the TTS engine that handled the last utterance."""
        if self._tts_manager:
            return self._tts_manager.active_engine_name
        return "initializing"

    @property
    def voice_mode(self) -> str:
        """Current voice mode: ``'standard'`` or ``'premium'``."""
        return self._voice_mode

    # -- public methods -------------------------------------------------------

    def set_enabled(self, enabled: bool) -> None:
        """Mute/unmute audio output while keeping UI and microphone active."""
        with self._state_lock:
            self._enabled = enabled
        if enabled:
            LOGGER.info("TTS unmuted.")
        else:
            LOGGER.info("TTS muted.")
            self._clear_pending()

    def set_voice_mode(self, mode: str) -> None:
        """Switch between ``'standard'`` (pyttsx3) and ``'premium'`` (ElevenLabs).

        Persists the choice to disk and reinitialises the TTS engine on the
        worker thread.  Safe to call from any thread.
        """
        if mode not in _MODE_TO_ENGINE:
            LOGGER.warning("Unknown voice mode: %s", mode)
            return
        if mode == self._voice_mode:
            return
        self._voice_mode = mode
        _save_voice_mode(mode)
        self._queue.put(SpeechJob(switch_mode=mode))

    def say(self, text: str) -> None:
        self.speak(text)

    def speak(self, text: str) -> None:
        """Centralized async TTS gateway used by every assistant response."""
        cleaned = self._clean_text(text)
        if not cleaned:
            return
        print("QUEUEING SPEECH:", cleaned)
        LOGGER.info("Speaker enabled: %s", self.enabled)
        if not self.enabled:
            LOGGER.info("TTS muted.")
            return
        LOGGER.info("Speaking response...")
        self._queue.put(SpeechJob(text=cleaned))
        LOGGER.info("Speech queue active.")
        LOGGER.info("Queue size: %s", self._queue.qsize())

    def recently_spoke(self, seconds: float = 1.0) -> bool:
        with self._state_lock:
            return self._speaking or (time.time() - self._last_spoken_at) < seconds

    def interrupt(self) -> None:
        """Clear pending speech. The engine itself remains worker-thread owned."""
        self._clear_pending()
        LOGGER.info("Speech queue cleared.")

    def close(self) -> None:
        self._queue.put(SpeechJob(shutdown=True))
        self._thread.join(timeout=4)

    # -- internal helpers -----------------------------------------------------

    def _clear_pending(self) -> None:
        try:
            while True:
                self._queue.get_nowait()
        except queue.Empty:
            return

    @staticmethod
    def _clean_text(text: str) -> str:
        cleaned = re.sub(r"<[^>]+>", " ", text)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    # -- worker thread --------------------------------------------------------

    def _run(self) -> None:
        try:
            from voice.tts.tts_manager import TTSManager

            engine = _MODE_TO_ENGINE.get(self._voice_mode, "pyttsx3")
            manager = TTSManager(
                tts_engine=engine,
                elevenlabs_api_key=CONFIG.voice.elevenlabs_api_key,
                elevenlabs_voice_id=CONFIG.voice.elevenlabs_voice_id,
            )
            manager.initialize()
            self._tts_manager = manager
            self._ready.set()
            LOGGER.info("TTS initialized successfully (mode: %s).", self._voice_mode)
            self._process_queue()
        except Exception as exc:
            LOGGER.exception("TTS worker failed: %s", exc)
            self._ready.set()
            self._process_queue_without_audio()
        finally:
            if self._tts_manager:
                try:
                    self._tts_manager.close()
                except Exception as exc:
                    LOGGER.warning("TTS manager close failed: %s", exc)

    def _process_queue(self) -> None:
        while True:
            job = self._queue.get()
            print("WORKER GOT:", job.text if job.text else ("mode:" + job.switch_mode if job.switch_mode else "shutdown"))
            if job.shutdown:
                break
            if job.switch_mode:
                self._handle_mode_switch(job.switch_mode)
                continue
            if not job.text:
                continue
            if not self.enabled:
                LOGGER.info("TTS muted.")
                continue
            try:
                with self._state_lock:
                    self._speaking = True
                LOGGER.info("Speaking response...")
                LOGGER.info("SPEAK START")
                time.sleep(0.22)
                print("WORKER SAY:", job.text)
                self._tts_manager.speak(job.text)
                print("WORKER SPEAK COMPLETE:", job.text)
                LOGGER.info("SPEAK END")
            except Exception as exc:
                LOGGER.exception("TTS exception while speaking: %s", exc)
            finally:
                with self._state_lock:
                    self._speaking = False
                    self._last_spoken_at = time.time()

    def _process_queue_without_audio(self) -> None:
        while True:
            job = self._queue.get()
            if job.shutdown:
                break
            if job.switch_mode:
                self._handle_mode_switch(job.switch_mode)
                continue
            if job.text:
                LOGGER.warning("TTS unavailable; dropped speech: %s", job.text)

    def _handle_mode_switch(self, mode: str) -> None:
        """Tear down the current TTS stack and rebuild for the new mode.

        Runs on the worker thread so COM/pyttsx3/pygame lifecycle is safe.
        """
        from voice.tts.tts_manager import TTSManager

        engine = _MODE_TO_ENGINE.get(mode, "pyttsx3")
        LOGGER.info("Switching voice mode: %s (engine: %s)", mode, engine)

        # Close old manager first (required for pyttsx3 COM cleanup).
        if self._tts_manager:
            try:
                self._tts_manager.close()
            except Exception as exc:
                LOGGER.warning("TTS close during mode switch: %s", exc)
            self._tts_manager = None

        # Build new manager.
        manager = TTSManager(
            tts_engine=engine,
            elevenlabs_api_key=CONFIG.voice.elevenlabs_api_key,
            elevenlabs_voice_id=CONFIG.voice.elevenlabs_voice_id,
        )
        manager.initialize()
        self._tts_manager = manager
        LOGGER.info("Voice mode active: %s (%s)", mode, manager.active_engine_name)
