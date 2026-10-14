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

    def summary_for_planner(self, max_pairs: int = 3) -> str:
        """Return recent conversation as compact text for classification prompts."""
        msgs = list(self._messages)
        if not msgs:
            return ""
        recent = msgs[-(max_pairs * 2) :]
        lines = []
        for msg in recent:
            role = "User" if msg["role"] == "user" else "Assistant"
            content = msg["content"][:150].replace("\n", " ")
            lines.append(f"{role}: {content}")
        return "\n".join(lines)
