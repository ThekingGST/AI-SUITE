from dataclasses import dataclass, field
from typing import Any

@dataclass
class GenerationRequest:
    prompt: str
    system: str = ""
    history: list[dict] = field(default_factory=list)
    images: list[Any] = field(default_factory=list)
    model: str = "default"

@dataclass
class GenerationResponse:
    text: str
    usage: dict = field(default_factory=dict)
