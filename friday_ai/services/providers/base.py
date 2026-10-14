"""Base provider interface."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Generator, Any

import requests

@dataclass
class ModelInfo:
    id: str
    name: str
    provider: str
    context_length: int = 8192
    is_free: bool = True
    parameter_count: str = ""
    size_gb: float = 0.0


class BaseProvider:
    """Abstract interface for an AI backend."""
    
    def __init__(self) -> None:
        self.is_available: bool = False
        self._session: requests.Session = requests.Session()
    
    def get_models(self) -> list[ModelInfo]:
        """Fetch available models from this provider."""
        raise NotImplementedError
        
    def stream(self, messages: list[dict[str, str]], model: str) -> Generator[str, None, None]:
        """Stream a response from the provider."""
        raise NotImplementedError
        
    def health_check(self) -> bool:
        """Check if the provider is reachable."""
        raise NotImplementedError
