from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from difflib import SequenceMatcher


CommandHandler = Callable[[str], str]


@dataclass(frozen=True)
class PluginCommand:
    name: str
    patterns: tuple[str, ...]
    handler: CommandHandler
    priority: int = 50
    fuzzy_threshold: float = 0.82


@dataclass
class PluginRegistry:
    """Dynamic command registry for future JARVIS skills and integrations."""

    commands: list[PluginCommand] = field(default_factory=list)

    def register(self, command: PluginCommand) -> None:
        self.commands.append(command)
        self.commands.sort(key=lambda item: item.priority)

    def match(self, text: str) -> str | None:
        for command in self.commands:
            for pattern in command.patterns:
                if text == pattern or text.startswith(pattern + " "):
                    return command.handler(text)
                ratio = SequenceMatcher(None, text, pattern).ratio()
                if ratio >= command.fuzzy_threshold:
                    return command.handler(text)
        return None
