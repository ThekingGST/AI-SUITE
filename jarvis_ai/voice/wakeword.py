import re
from jarvis_ai.config import CONFIG
from jarvis_ai.utils.helpers import normalize_text

class WakeWordDetector:
    def __init__(self, wake_word: str = CONFIG.voice.wake_word) -> None:
        self.wake_word = wake_word.lower()
        self.aliases = {
            self.wake_word,
            "jarvis", "जार्विस", "జార్విస్"
        }

    def contains_wake_word(self, text: str) -> bool:
        # Strip basic ASCII and common unicode punctuation
        cleaned = re.sub(r'[,.?/!;।:\u200b]', '', normalize_text(text))
        words = cleaned.split()
        return any(alias in words or cleaned.startswith(alias) for alias in self.aliases)

    def strip_wake_word(self, text: str) -> str:
        cleaned = normalize_text(text)
        cleaned_no_punct = re.sub(r'[,.?/!;।:\u200b]', '', cleaned)
        
        for alias in self.aliases:
            if cleaned_no_punct.startswith(alias):
                words = cleaned.split(maxsplit=1)
                if len(words) > 1:
                    return words[1].strip(' ,.?/!।')
                return ''
                
        return cleaned
