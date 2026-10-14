from __future__ import annotations

import io
import threading

from jarvis_ai.utils.logger import LOGGER
from jarvis_ai.voice.v2.backends.base import AbortedError


class PygamePlayer:
    """AudioPlaybackInterface implementation using pygame.mixer.
    
    Supports cooperative abort during playback.
    """
    
    def __init__(self) -> None:
        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return
            
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
            self._initialized = True
            LOGGER.info("PygamePlayer initialized.")
        except Exception as exc:
            LOGGER.warning("PygamePlayer init failed: %s", exc)
            raise RuntimeError(f"Failed to initialize pygame mixer: {exc}") from exc

    def play_bytes(self, audio_data: bytes, abort: threading.Event | None = None) -> None:
        if not self._initialized:
            self.initialize()
            
        if not audio_data:
            return
            
        import pygame
        
        try:
            sound = pygame.mixer.Sound(io.BytesIO(audio_data))
            channel = sound.play()
            if channel:
                while channel.get_busy():
                    if abort and abort.is_set():
                        channel.stop()
                        raise AbortedError("Aborted during playback")
                    pygame.time.wait(25)  # 25ms poll for responsiveness
        except AbortedError:
            raise
        except Exception as exc:
            LOGGER.warning("Pygame playback failed: %s", exc)
            raise RuntimeError(f"Playback failed: {exc}") from exc

    def close(self) -> None:
        if self._initialized:
            try:
                import pygame
                pygame.mixer.quit()
                LOGGER.info("PygamePlayer closed.")
            except Exception as exc:
                LOGGER.warning("PygamePlayer close failed: %s", exc)
            self._initialized = False
