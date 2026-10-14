from __future__ import annotations

from collections import deque

from config import CONFIG


class ContextManager:
    def __init__(self, max_messages: int = CONFIG.ai.max_history_messages) -> None:
        self._messages: deque[dict[str, str]] = deque(maxlen=max_messages)

    def add(self, role: str, content: str) -> None:
        self._messages.append({"role": role, "content": content})

    def load(self, messages: list[dict[str, str]]) -> None:
        self._messages.clear()
        for message in messages[-self._messages.maxlen :]:
            self.add(message["role"], message["content"])

    def messages(self) -> list[dict[str, str]]:
        return list(self._messages)
