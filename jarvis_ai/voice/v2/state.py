from __future__ import annotations

import threading
from enum import Enum
from typing import Callable

from jarvis_ai.utils.logger import LOGGER


class VoiceState(Enum):
    """Unified voice system state.

    Replaces scattered boolean flags across MainWindow, Speaker, and
    VoiceListener with a single authoritative state enum.
    """

    OFF = "off"                  # Voice system disabled
    IDLE = "idle"                # Listening for wake word
    LISTENING = "listening"      # Wake word detected, capturing command
    RECOGNIZING = "recognizing"  # STT processing captured audio
    THINKING = "thinking"        # LLM generating response
    STREAMING = "streaming"      # LLM streaming + TTS pipelining
    SPEAKING = "speaking"        # Audio playback active (no more LLM tokens)
    INTERRUPTED = "interrupted"  # User interrupted, cancelling speech
    MUTED = "muted"              # Audio output disabled, mic still active
    ERROR = "error"              # Recoverable error state


# ---------------------------------------------------------------------------
# Transition rules
# ---------------------------------------------------------------------------

_VALID_TRANSITIONS: dict[VoiceState, set[VoiceState]] = {
    VoiceState.OFF: {VoiceState.IDLE},
    VoiceState.IDLE: {
        VoiceState.LISTENING,
        VoiceState.OFF,
        VoiceState.MUTED,
        VoiceState.THINKING,   # text command bypass (no wake word needed)
        VoiceState.STREAMING,  # standalone TTS streaming (notifications)
        VoiceState.SPEAKING,   # standalone TTS speaking (notifications)
        VoiceState.ERROR,
    },
    VoiceState.LISTENING: {
        VoiceState.IDLE,        # silence timeout
        VoiceState.THINKING,    # text recognized
        VoiceState.ERROR,
    },
    VoiceState.RECOGNIZING: {
        VoiceState.THINKING,
        VoiceState.IDLE,
        VoiceState.ERROR,
    },
    VoiceState.THINKING: {
        VoiceState.STREAMING,   # first token arrives
        VoiceState.SPEAKING,    # non-streaming (automation) response
        VoiceState.INTERRUPTED, # user interrupts
        VoiceState.IDLE,        # empty response
        VoiceState.ERROR,
    },
    VoiceState.STREAMING: {
        VoiceState.SPEAKING,    # generation done, last sentence queued
        VoiceState.INTERRUPTED, # user interrupts
        VoiceState.ERROR,
    },
    VoiceState.SPEAKING: {
        VoiceState.IDLE,        # playback done
        VoiceState.INTERRUPTED, # user interrupts
        VoiceState.ERROR,
    },
    VoiceState.INTERRUPTED: {
        VoiceState.IDLE,        # cleanup done
        VoiceState.ERROR,
    },
    VoiceState.MUTED: {
        VoiceState.IDLE,        # unmute
        VoiceState.OFF,
        VoiceState.ERROR,
    },
    VoiceState.ERROR: {
        VoiceState.IDLE,        # recovered
        VoiceState.OFF,         # fatal
    },
}


class VoiceStateMachine:
    """Thread-safe state machine governing the entire voice pipeline.

    All state reads and writes are protected by a single RLock.
    Observers are notified *after* the lock is released to prevent
    deadlocks from callback re-entry.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._state = VoiceState.OFF
        self._observers: list[Callable[[VoiceState, VoiceState], None]] = []
        self._error_count = 0
        self._max_consecutive_errors = 3

    @property
    def state(self) -> VoiceState:
        with self._lock:
            return self._state

    def transition(self, target: VoiceState) -> bool:
        """Attempt a state transition.

        Returns True if the transition was valid and executed.
        Returns False (and logs a warning) if the transition is illegal.
        Observers are called outside the lock.
        """
        with self._lock:
            current = self._state
            if target == current:
                return True  # no-op, not an error

            valid_targets = _VALID_TRANSITIONS.get(current, set())
            if target not in valid_targets:
                LOGGER.warning(
                    "VoiceState: illegal transition %s -> %s (allowed: %s)",
                    current.value,
                    target.value,
                    ", ".join(s.value for s in valid_targets),
                )
                return False

            old = self._state
            self._state = target

            # Track consecutive errors for auto-disable
            if target == VoiceState.ERROR:
                self._error_count += 1
            else:
                self._error_count = 0

        # Notify observers outside the lock
        LOGGER.info("VoiceState: %s -> %s", old.value, target.value)
        for observer in self._observers:
            try:
                observer(old, target)
            except Exception as exc:
                LOGGER.warning("VoiceState observer error: %s", exc)

        return True

    def should_auto_disable(self) -> bool:
        """True if consecutive error count exceeds threshold."""
        with self._lock:
            return self._error_count >= self._max_consecutive_errors

    def on_state_change(self, callback: Callable[[VoiceState, VoiceState], None]) -> None:
        """Register an observer for state transitions.

        Callback signature: (old_state, new_state) -> None
        """
        self._observers.append(callback)

    def reset(self) -> None:
        """Force-reset to OFF. Used during shutdown or fatal recovery."""
        with self._lock:
            old = self._state
            self._state = VoiceState.OFF
            self._error_count = 0
        LOGGER.info("VoiceState: RESET (%s -> OFF)", old.value)
