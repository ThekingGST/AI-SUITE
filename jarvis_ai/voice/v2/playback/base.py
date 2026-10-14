from __future__ import annotations

import threading
from typing import Protocol, runtime_checkable

from jarvis_ai.voice.v2.backends.base import AbortedError


@runtime_checkable
class AudioPlaybackInterface(Protocol):
    """Protocol for audio playback engines in the Voice Framework.
    
    Decouples TTS backends from specific audio libraries (pygame, pyaudio).
    """

    def initialize(self) -> None:
        """Initialize the audio subsystem (e.g. pygame.mixer)."""
        ...
        
    def play_bytes(self, audio_data: bytes, abort: threading.Event | None = None) -> None:
        """Play raw audio bytes completely.
        
        Must block until playback completes.
        If abort is set during playback, it must stop immediately and raise AbortedError.
        """
        ...
        
    def close(self) -> None:
        """Shut down the audio subsystem and release resources."""
        ...
