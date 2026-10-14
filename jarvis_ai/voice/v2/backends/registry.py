from __future__ import annotations

import threading

from jarvis_ai.utils.logger import LOGGER
from jarvis_ai.voice.v2.backends.base import TTSBackend


class TTSBackendRegistry:
    """Manages available TTS backends with hot-swapping.

    Thread-safe.  The active backend can be changed at runtime via
    ``set_active()``.  A fallback backend is used automatically if
    the primary ``speak()`` fails.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._backends: dict[str, TTSBackend] = {}
        self._active: str = ""
        self._fallback: str = ""

    def register(self, name: str, backend: TTSBackend) -> None:
        """Register a backend under *name*."""
        with self._lock:
            self._backends[name] = backend
            LOGGER.info("TTSBackendRegistry: registered '%s'", name)

    def set_active(self, name: str) -> bool:
        """Set the primary backend.  Returns True on success."""
        with self._lock:
            if name not in self._backends:
                LOGGER.warning("TTSBackendRegistry: unknown backend '%s'", name)
                return False
            self._active = name
            LOGGER.info("TTSBackendRegistry: active backend = '%s'", name)
            return True

    def set_fallback(self, name: str) -> bool:
        """Set the fallback backend.  Returns True on success."""
        with self._lock:
            if name not in self._backends:
                LOGGER.warning("TTSBackendRegistry: unknown fallback '%s'", name)
                return False
            self._fallback = name
            LOGGER.info("TTSBackendRegistry: fallback backend = '%s'", name)
            return True

    def get_backend(self, name: str) -> TTSBackend | None:
        """Retrieve a registered backend by name."""
        with self._lock:
            return self._backends.get(name)
            
    def get_all_backends(self) -> dict[str, TTSBackend]:
        """Return a copy of all registered backends."""
        with self._lock:
            return dict(self._backends)

    def get_active(self) -> TTSBackend | None:
        """DEPRECATED: Use dynamic capability-based resolution instead."""
        with self._lock:
            return self._backends.get(self._active)

    def get_fallback(self) -> TTSBackend | None:
        """DEPRECATED: Use dynamic capability-based resolution instead."""
        with self._lock:
            if self._fallback and self._fallback != self._active:
                return self._backends.get(self._fallback)
            return None

    @property
    def active_name(self) -> str:
        with self._lock:
            return self._active

    def list_available(self) -> list[str]:
        with self._lock:
            return [
                name for name, backend in self._backends.items()
                if backend.is_available()
            ]

    def close_all(self) -> None:
        """Close all registered backends."""
        with self._lock:
            for name, backend in self._backends.items():
                try:
                    backend.close()
                except Exception as exc:
                    LOGGER.warning("TTSBackendRegistry: close '%s' failed: %s", name, exc)
            self._backends.clear()
