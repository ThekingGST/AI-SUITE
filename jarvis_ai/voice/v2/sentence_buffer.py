from __future__ import annotations

import re
from collections.abc import Callable

from jarvis_ai.utils.logger import LOGGER


# Sentence-ending punctuation followed by space or end-of-string
_SENTENCE_RE = re.compile(r'(?<=[.!?])\s+|(?<=[.!?])$')

# Clause boundary: comma/semicolon/colon followed by space (only used for long buffers)
_CLAUSE_RE = re.compile(r'(?<=[,;:])\s+')

# Minimum character threshold before we consider clause-level splitting
_MIN_CHUNK_CHARS = 40

# Maximum buffer size before we force a split at any boundary
_MAX_BUFFER_CHARS = 200


class SentenceBuffer:
    """Accumulates streaming tokens and emits semantically complete chunks.

    Designed to sit between the LLM token stream and the SpeechManager.
    Prefers splitting at sentence boundaries (`.` `!` `?`) but will fall
    back to clause boundaries (`,` `;` `:`) for very long buffers.

    Usage::

        buffer = SentenceBuffer(on_sentence=speech_manager.enqueue)
        for token in llm_stream:
            buffer.feed(token)
        buffer.flush()
    """

    def __init__(
        self,
        on_sentence: Callable[[str], None],
        min_chars: int = _MIN_CHUNK_CHARS,
        max_chars: int = _MAX_BUFFER_CHARS,
    ) -> None:
        self._on_sentence = on_sentence
        self._buffer: list[str] = []
        self._min_chars = min_chars
        self._max_chars = max_chars

    def feed(self, token: str) -> None:
        """Feed a single token from the LLM stream."""
        self._buffer.append(token)
        text = "".join(self._buffer)

        if len(text) < self._min_chars:
            return

        # Try sentence-level split first, finding the LAST boundary
        matches = list(_SENTENCE_RE.finditer(text))
        if matches:
            last_match = matches[-1]
            split_idx = last_match.end()
            chunk = text[:split_idx].strip()
            if chunk:
                self._emit(chunk)
                self._buffer = [text[split_idx:]] if split_idx < len(text) else []
                return

        # If buffer is getting long, try clause-level split
        if len(text) >= self._max_chars:
            matches = list(_CLAUSE_RE.finditer(text))
            if matches:
                last_match = matches[-1]
                split_idx = last_match.end()
                chunk = text[:split_idx].strip()
                if chunk:
                    self._emit(chunk)
                    self._buffer = [text[split_idx:]] if split_idx < len(text) else []
                    return

            # Absolute last resort: emit everything
            self._emit(text.strip())
            self._buffer = []

    def flush(self) -> None:
        """Emit whatever remains in the buffer."""
        text = "".join(self._buffer).strip()
        if text:
            self._emit(text)
        self._buffer = []

    def clear(self) -> None:
        """Discard the buffer without emitting."""
        self._buffer = []

    def _emit(self, text: str) -> None:
        """Send a complete chunk to the consumer."""
        import time
        import threading

        try:
            LOGGER.info("[TTS] SentenceBuffer emitting chunk: %s", text)
            self._on_sentence(text)
        except Exception as exc:
            LOGGER.warning("SentenceBuffer: consumer error: %s", exc)
