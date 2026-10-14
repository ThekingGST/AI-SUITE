from __future__ import annotations

import time
from collections import deque
from typing import TypedDict

from jarvis_ai.config import CONFIG
from jarvis_ai.utils.logger import LOGGER


class RecognitionEvent(TypedDict):
    identity: str
    confidence: float
    timestamp: float


class TemporalRecognizer:
    """Rolling history buffer to smooth out frame-by-frame recognition anomalies."""

    def __init__(self) -> None:
        self.history_size = getattr(CONFIG.vision, "history_size", 5)
        self.majority_thresh = getattr(CONFIG.vision, "history_majority", 3)
        self.timeout = getattr(CONFIG.vision, "history_timeout_seconds", 2.0)
        
        # Buffer of recent recognitions
        self._buffer: deque[RecognitionEvent] = deque(maxlen=self.history_size)

    def update(self, identity: str, confidence: float) -> tuple[str, float]:
        """Add a new recognition event and return the temporally smoothed identity.
        
        Args:
            identity: The raw identity recognized in the current frame.
            confidence: The raw confidence score.
            
        Returns:
            (smoothed_identity, average_confidence)
        """
        now = time.time()
        
        # Add new event
        self._buffer.append({
            "identity": identity,
            "confidence": confidence,
            "timestamp": now
        })
        
        # Prune expired events
        while self._buffer and now - self._buffer[0]["timestamp"] > self.timeout:
            self._buffer.popleft()
            
        # If buffer is empty (shouldn't happen since we just added one), return raw
        if not self._buffer:
            return identity, confidence

        # Count frequencies
        counts: dict[str, int] = {}
        conf_sums: dict[str, float] = {}
        for event in self._buffer:
            name = event["identity"]
            counts[name] = counts.get(name, 0) + 1
            conf_sums[name] = conf_sums.get(name, 0.0) + event["confidence"]

        # Find the most frequent identity
        best_name = max(counts.keys(), key=lambda k: counts[k])
        best_count = counts[best_name]
        
        # Check if it meets majority threshold
        if best_count >= self.majority_thresh:
            avg_conf = conf_sums[best_name] / best_count
            if best_name != identity:
                LOGGER.debug(
                    "TEMPORAL SMOOTHING: Overrode raw '%s' with majority '%s' (%d/%d)",
                    identity, best_name, best_count, len(self._buffer)
                )
            return best_name, avg_conf
            
        # If no majority, return "unknown" to prevent flickering, 
        # OR fallback to current frame if it's the only one.
        if len(self._buffer) < self.majority_thresh:
            # Not enough history yet, trust the raw output
            return identity, confidence
            
        # Conflicting history without a clear majority
        LOGGER.debug(
            "TEMPORAL SMOOTHING: No majority found (best=%s with %d/%d). Returning unknown.",
            best_name, best_count, len(self._buffer)
        )
        return "unknown", 0.0

    def clear(self) -> None:
        """Clear the temporal buffer (e.g., when scene changes)."""
        self._buffer.clear()
