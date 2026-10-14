from __future__ import annotations

from config import CONFIG
from utils.helpers import normalize_text


class WakeWordDetector:
    def __init__(self, wake_word: str = CONFIG.voice.wake_word) -> None:
        self.wake_word = wake_word.lower()

    def contains_wake_word(self, text: str) -> bool:
        words = normalize_text(text).split()
        return self.wake_word in words or normalize_text(text).startswith(self.wake_word)

    def strip_wake_word(self, text: str) -> str:
        cleaned = normalize_text(text)
        if cleaned.startswith(self.wake_word):
            return cleaned[len(self.wake_word) :].strip(" ,")
        return cleaned
