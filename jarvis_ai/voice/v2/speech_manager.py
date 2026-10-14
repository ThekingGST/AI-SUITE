from __future__ import annotations

import re
import threading
import time
from typing import Iterator

from jarvis_ai.config import CONFIG
from jarvis_ai.utils.logger import LOGGER
from jarvis_ai.voice.v2.backends.base import AbortedError
from jarvis_ai.voice.v2.backends.registry import TTSBackendRegistry
from jarvis_ai.voice.v2.events import VoiceEvent, VoiceEventBus
from jarvis_ai.voice.v2.profile import DEFAULT_PROFILES, VoiceProfile
from jarvis_ai.voice.v2.queue import PrioritySpeechQueue
from jarvis_ai.voice.v2.state import VoiceState, VoiceStateMachine
from jarvis_ai.voice.v2.types import AbortController, SpeechJob, SpeechPriority


class SpeechManager:
    """Centralized speech output controller for Voice System 2.0.

    The ONLY component that interfaces with TTS backends.  All speech
    requests flow through this manager via ``enqueue()``.

    Responsibilities:
    - Priority queue management
    - Worker thread lifecycle
    - Backend dispatch with failover
    - Cooperative cancellation via AbortController
    - Event emission for UI and mic synchronization
    - Streaming sentence pipelining
    """

    def __init__(
        self,
        registry: TTSBackendRegistry,
        event_bus: VoiceEventBus,
        state_machine: VoiceStateMachine | None = None,
    ) -> None:
        self._registry = registry
        self._event_bus = event_bus
        self.state_machine = state_machine or VoiceStateMachine()
        self._queue = PrioritySpeechQueue()
        self._abort = AbortController()
        self._state_lock = threading.RLock()
        self._profile: VoiceProfile = DEFAULT_PROFILES["natural"]
        self._enabled = True
        self._speaking = False
        self._last_spoken_at = 0.0
        self._current_job: SpeechJob | None = None
        self._ready = threading.Event()
        self._thread: threading.Thread | None = None

    # -- Public properties -----------------------------------------------------

    @property
    def enabled(self) -> bool:
        with self._state_lock:
            return self._enabled

    @property
    def is_speaking(self) -> bool:
        with self._state_lock:
            return self._speaking

    @property
    def queue_depth(self) -> int:
        return self._queue.depth

    @property
    def is_aborted(self) -> bool:
        """True if the current operation has been cancelled."""
        return self._abort.is_aborted

    @property
    def is_idle(self) -> bool:
        with self._state_lock:
            return not self._speaking and self._queue.empty
            
    @property
    def is_streaming(self) -> bool:
        with self._state_lock:
            return getattr(self, "_is_streaming_session", False)

    def recently_spoke(self, seconds: float = 1.0) -> bool:
        with self._state_lock:
            return self._speaking or (time.time() - self._last_spoken_at) < seconds

    @property
    def active_profile_name(self) -> str:
        with self._state_lock:
            return self._profile.name

    @property
    def voice_mode(self) -> str:
        """Compatibility: returns 'premium' if not offline."""
        with self._state_lock:
            return "standard" if self._profile.require_offline else "premium"

    # -- Public methods --------------------------------------------------------

    def set_streaming_session(self, active: bool) -> None:
        """Mark whether an LLM stream is currently actively feeding the queue."""
        with self._state_lock:
            self._is_streaming_session = active
        
        # If the stream finished, and we have no pending/active speech, 
        # trigger a finished event so the UI knows it's finally clear to resume the mic.
        if not active and self.is_idle:
            self._event_bus.emit(VoiceEvent.SPEECH_FINISHED, {"job_id": "stream_end"})

    def set_enabled(self, enabled: bool) -> None:
        with self._state_lock:
            self._enabled = enabled
        if not enabled:
            LOGGER.info("SpeechManager: muted. Interrupting active speech.")
            self.interrupt()
        else:
            LOGGER.info("SpeechManager: unmuted.")

    def enqueue(self, text: str, priority: SpeechPriority = SpeechPriority.NORMAL) -> SpeechJob | None:
        """Enqueue text for speech.  Returns the SpeechJob or None if muted."""
        cleaned = self._clean_text(text)
        if not cleaned:
            return None
        if not self.enabled:
            LOGGER.info("SpeechManager: muted, dropping: %s", cleaned[:50])
            return None
            
        # If we are idle, transition to THINKING/STREAMING
        # (This is a simplified transition for now just to track basic flow)
        if self.state_machine.state == VoiceState.IDLE:
            self.state_machine.transition(VoiceState.STREAMING)
            
        job = self._queue.put(cleaned, priority, self._abort.event)
        import time
        import threading

        return job

    def interrupt(self) -> None:
        """Stop current speech and flush the queue."""
        LOGGER.info("SpeechManager: interrupt requested.")
        self.state_machine.transition(VoiceState.INTERRUPTED)
        self._abort.abort()
        drained = self._queue.drain()
        if drained:
            LOGGER.info("SpeechManager: drained %d pending jobs.", len(drained))
        self._event_bus.emit(VoiceEvent.SPEECH_INTERRUPTED)
        self.state_machine.transition(VoiceState.IDLE)

    def set_profile(self, profile: VoiceProfile) -> None:
        """Change the active voice profile."""
        with self._state_lock:
            self._profile = profile
        LOGGER.info("SpeechManager: Profile set to '%s'", profile.name)
        self._event_bus.emit(VoiceEvent.STATE_CHANGED, {"profile": profile.name})

    def start(self) -> None:
        """Start the speech worker thread."""
        if self._thread and self._thread.is_alive():
            return
            
        if self.state_machine.state == VoiceState.OFF:
            self.state_machine.transition(VoiceState.IDLE)
            
        self._thread = threading.Thread(
            target=self._run, name="SpeechManagerWorker", daemon=True
        )
        self._thread.start()

    def close(self) -> None:
        """Shutdown the speech worker."""
        self._queue.put_control(shutdown=True)
        if self._thread:
            self._thread.join(timeout=4)
        self._registry.close_all()

    # -- Internal: worker thread -----------------------------------------------

    def _run(self) -> None:
        """Worker thread main loop."""
        # Initialize all registered backends on the worker thread
        backends = self._registry.get_all_backends()
        for name, backend in backends.items():
            if hasattr(backend, "initialize"):
                try:
                    backend.initialize()
                    LOGGER.info("SpeechManager: initialized backend '%s'", name)
                except Exception as exc:
                    LOGGER.exception("SpeechManager: init failed for '%s': %s", name, exc)

        self._ready.set()
        LOGGER.info("SpeechManager: worker ready.")

        while True:
            job = self._queue.get(timeout=0.2)
            if job is None:
                continue

            if job.is_shutdown:
                LOGGER.info("SpeechManager: shutdown received.")
                break

            # Handle control jobs if we add any other than shutdown
            if job.switch_backend:
                pass # Legacy switch_backend is ignored, profile handles it

            if not job.text:
                continue

            if not self.enabled:
                LOGGER.info("SpeechManager: muted, skipping job %s", job.job_id)
                continue

            self._speak_job(job)

    def _speak_job(self, job: SpeechJob) -> None:
        """Execute a single speech job with failover."""
        # Reset abort for this utterance
        self._abort.reset()

        with self._state_lock:
            self._speaking = True
            self._current_job = job

        self.state_machine.transition(VoiceState.SPEAKING)
        
        self._event_bus.emit(VoiceEvent.SPEECH_STARTED, {
            "text": job.text, "job_id": job.job_id
        })

        try:
            time.sleep(0.15)  # Brief settling delay for mic sync
            
            with self._state_lock:
                profile = self._profile
                
            # Dynamic Backend Resolution
            resolved = False
            for backend_name in profile.fallback_chain:
                backend = self._registry.get_backend(backend_name)
                if not backend:
                    continue
                    
                health = backend.get_health()
                if not health.is_available:
                    continue
                    
                caps = backend.get_capabilities()
                if profile.require_offline and not caps.offline:
                    continue
                    
                try:
                    # Inform event bus of the selected backend
                    self._event_bus.emit(VoiceEvent.BACKEND_CHANGED, {"backend": backend_name})
                    if hasattr(backend, "apply_profile"):
                        backend.apply_profile(profile)
                        
                    import threading

                        
                    backend.speak(job.text, self._abort.event)
                    resolved = True
                    break
                except AbortedError:
                    LOGGER.info("SpeechManager: speech aborted [%s]", job.job_id)
                    resolved = True # It succeeded, just aborted
                    break
                except Exception as exc:
                    LOGGER.warning("SpeechManager: backend '%s' failed: %s", backend_name, exc)
                    
            if not resolved:
                LOGGER.error("SpeechManager: ALL backends in profile '%s' failed, dropped: %s", 
                             profile.name, job.text[:80])

        finally:
            with self._state_lock:
                self._speaking = False
                self._last_spoken_at = time.time()
                self._current_job = None
            
            if not self.is_aborted:
                self.state_machine.transition(VoiceState.IDLE)
                
            self._event_bus.emit(VoiceEvent.SPEECH_FINISHED, {
                "job_id": job.job_id
            })

    def _clear_pending(self) -> None:
        """Drain the queue silently."""
        self._queue.drain()

    @staticmethod
    def _clean_text(text: str) -> str:
        cleaned = re.sub(r"<[^>]+>", " ", text)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned
