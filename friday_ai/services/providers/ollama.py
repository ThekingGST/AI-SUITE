"""Ollama local AI provider."""

from __future__ import annotations
import json
from typing import Generator

import requests

from friday_ai.services.providers.base import BaseProvider, ModelInfo
from friday_ai.core.config import CONFIG
from shared.logger import get_logger

LOG = get_logger("friday.ollama")


class OllamaProvider(BaseProvider):
    """Integrates with local Ollama instance."""

    def __init__(self, base_url: str = "http://localhost:11434") -> None:
        super().__init__()
        self.base_url = base_url.rstrip("/")

    def health_check(self) -> bool:
        """Check if Ollama is running."""
        try:
            resp = self._session.get(f"{self.base_url}/api/tags", timeout=2)
            self.is_available = resp.status_code == 200
            return self.is_available
        except requests.RequestException:
            self.is_available = False
            return False

    def get_models(self) -> list[ModelInfo]:
        """Fetch available local models."""
        try:
            resp = self._session.get(f"{self.base_url}/api/tags", timeout=2)
            resp.raise_for_status()
            data = resp.json()
            models = []
            for m in data.get("models", []):
                name = m.get("name", "")
                details = m.get("details", {})
                
                # Approximate size in GB
                size = m.get("size", 0) / (1024 ** 3)
                
                # Ollama context lengths vary by model, usually default to 8192 for qwen
                context_length = 8192 
                
                models.append(ModelInfo(
                    id=name,
                    name=name,
                    provider="ollama",
                    context_length=context_length,
                    is_free=True,
                    parameter_count=details.get("parameter_size", "unknown"),
                    size_gb=round(size, 2)
                ))
            return models
        except requests.RequestException as e:
            LOG.warning("Failed to fetch Ollama models: %s", e)
            return []

    def stream(self, messages: list[dict[str, str]], model: str) -> Generator[str, None, None]:
        """Stream a response from Ollama."""
        LOG.info("OllamaProvider.stream() called for model: %s", model)
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
        }
        
        chunk_count = 0
        try:
            with self._session.post(
                f"{self.base_url}/api/chat",
                json=payload,
                stream=True,
                timeout=(10, 120),  # Generous connection timeout to allow model wake-up
            ) as resp:
                resp.raise_for_status()
                LOG.info("OllamaProvider.stream() received HTTP response: %s", resp.status_code)
                for line in resp.iter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if "message" in data and "content" in data["message"]:
                                chunk = data["message"]["content"]
                                chunk_count += 1
                                LOG.debug("OllamaProvider.stream() yielding chunk %d", chunk_count)
                                yield chunk
                            if data.get("done"):
                                LOG.info("OllamaProvider.stream() stream complete. Total chunks: %d", chunk_count)
                                break
                        except json.JSONDecodeError as e:
                            LOG.error("OllamaProvider.stream() JSON parse error: %s", e)
        except requests.RequestException as e:
            LOG.error("OllamaProvider.stream() failed: %s", e)
            raise
        except Exception as e:
            LOG.error("OllamaProvider.stream() unexpected error: %s", e)
            raise
