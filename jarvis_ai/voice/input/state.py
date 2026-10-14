from __future__ import annotations

import threading
from enum import Enum
from typing import Callable, Dict, List, Set

from jarvis_ai.utils.logger import LOGGER
from jarvis_ai.voice.input.events import AudioEvent, AudioEventBus


class InputState(Enum):
    OFF = "off"                      # Capture stopped
    IDLE = "idle"                    # Capturing, silence
    LISTENING = "listening"          # Capture active (pre-speech)
    SPEECH_DETECTED = "speech"       # VAD triggered
    RECOGNIZING = "recognizing"      # Wakeword met, STT engaged
    RECOGNIZED = "recognized"        # Final transcript emitted
    INTERRUPTED = "interrupted"      # Output interrupted us
    ERROR = "error"                  # Device error


_VALID_TRANSITIONS: Dict[InputState, Set[InputState]] = {
    InputState.OFF: {InputState.IDLE, InputState.ERROR},
    InputState.IDLE: {
        InputState.LISTENING,
        InputState.OFF,
        InputState.ERROR
    },
    InputState.LISTENING: {
        InputState.SPEECH_DETECTED,
        InputState.IDLE,
        InputState.OFF,
        InputState.ERROR
    },
    InputState.SPEECH_DETECTED: {
        InputState.RECOGNIZING,
        InputState.LISTENING,
        InputState.IDLE,
        InputState.ERROR
    },
    InputState.RECOGNIZING: {
        InputState.RECOGNIZED,
        InputState.LISTENING,
        InputState.INTERRUPTED,
        InputState.ERROR
    },
    InputState.RECOGNIZED: {
        InputState.LISTENING,
        InputState.IDLE,
        InputState.ERROR
    },
    InputState.INTERRUPTED: {
        InputState.IDLE,
        InputState.LISTENING,
        InputState.ERROR
    },
    InputState.ERROR: {
        InputState.OFF,
        InputState.IDLE
    }
}


class AudioStateMachine:
    """Thread-safe state machine for the input pipeline."""

    def __init__(self, event_bus: AudioEventBus) -> None:
        self._lock = threading.RLock()
        self._state = InputState.OFF
        self.event_bus = event_bus

        # Bind to pipeline events to auto-transition
        self.event_bus.subscribe(AudioEvent.AUDIO_STARTED, lambda _: self.transition(InputState.IDLE))
        self.event_bus.subscribe(AudioEvent.AUDIO_STOPPED, lambda _: self.transition(InputState.OFF))
        self.event_bus.subscribe(AudioEvent.DEVICE_ERROR, lambda _: self.transition(InputState.ERROR))
        self.event_bus.subscribe(AudioEvent.SPEECH_STARTED, lambda _: self.transition(InputState.SPEECH_DETECTED))
        self.event_bus.subscribe(AudioEvent.RECOGNITION_STARTED, lambda _: self.transition(InputState.RECOGNIZING))
        self.event_bus.subscribe(AudioEvent.RECOGNITION_FINISHED, lambda _: self._handle_recognized())
        self.event_bus.subscribe(AudioEvent.SPEECH_ENDED, lambda _: self._handle_speech_ended())

    @property
    def state(self) -> InputState:
        with self._lock:
            return self._state

    def transition(self, target: InputState) -> bool:
        with self._lock:
            current = self._state
            if target == current:
                return True
                
            # If off and trying to transition to something other than IDLE/ERROR, ignore
            if current == InputState.OFF and target not in (InputState.IDLE, InputState.ERROR):
                return False

            valid_targets = _VALID_TRANSITIONS.get(current, set())
            
            # Forcing fallback safety
            if target not in valid_targets:
                LOGGER.warning("AudioStateMachine: illegal transition %s -> %s", current.value, target.value)
                return False

            self._state = target
            LOGGER.info("AudioStateMachine: %s -> %s", current.value, target.value)
            
        return True

    def _handle_recognized(self) -> None:
        self.transition(InputState.RECOGNIZED)
        # Auto-return to listening
        self.transition(InputState.LISTENING)

    def _handle_speech_ended(self) -> None:
        # If we were in SPEECH_DETECTED but not RECOGNIZING, we go back to listening
        if self.state == InputState.SPEECH_DETECTED:
            self.transition(InputState.LISTENING)
