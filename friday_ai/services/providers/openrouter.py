"""OpenRouter AI provider for cloud models."""

from __future__ import annotations
import json
import time
from typing import Generator

import requests

from friday_ai.services.providers.base import BaseProvider, ModelInfo
from friday_ai.core.config import CONFIG
from friday_ai.services.persistence import WorkspacePersistence
from shared.logger import get_logger

LOG = get_logger("friday.openrouter")


class OpenRouterProvider(BaseProvider):
    """Integrates with OpenRouter API.
    
    Only fetches FREE models (where pricing for prompt and completion is '0').
    Caches model list for 24 hours.
    """

    def __init__(self, persistence: WorkspacePersistence) -> None:
        super().__init__()
        self.persistence = persistence
        self.base_url = CONFIG.openrouter_url
        
    @property
    def api_key(self) -> str:
        key = self.persistence.get("openrouter_api_key", "")
        if not key:
            key = getattr(CONFIG, "openrouter_api_key", "")
        
        if key:
            key = key.strip().strip("'\"")
            # Safe diagnostic logging
            prefix = key[:10] if len(key) > 10 else "***"
            LOG.debug("OpenRouter API Key loaded. Length: %d, Prefix: %s", len(key), prefix)
        else:
            LOG.warning("OpenRouter API Key is missing.")
            
        return key

    def health_check(self) -> bool:
        """Check if we have an API key and can reach the service."""
        if not self.api_key:
            self.is_available = False
            return False
        # Lightweight check: models endpoint works
        try:
            resp = self._session.get(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=5
            )
            self.is_available = resp.status_code == 200
            return self.is_available
        except requests.RequestException:
            self.is_available = False
            return False

    def get_models(self, force_refresh: bool = False) -> list[ModelInfo]:
        """Fetch available FREE cloud models, with 24-hour cache."""
        cached_time = self.persistence.get("or_models_time", 0)
        cached_data = self.persistence.get("or_models_data", [])
        
        now = time.time()
        # 24 hours = 86400 seconds
        if not force_refresh and cached_data and (now - cached_time) < 86400:
            return [ModelInfo(**m) for m in cached_data]
            
        if not self.api_key:
            LOG.info("No OpenRouter API key, cannot fetch models.")
            return []

        try:
            resp = self._session.get(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json().get("data", [])
            
            free_models = [
                ModelInfo(
                    id="openrouter/free",
                    name="Auto (Free Router)",
                    provider="openrouter",
                    context_length=8192,
                    is_free=True
                )
            ]
            
            for m in data:
                pricing = m.get("pricing", {})
                # Check if it's explicitly free
                if pricing.get("prompt") == "0" and pricing.get("completion") == "0":
                    mi = ModelInfo(
                        id=m["id"],
                        name=m.get("name", m["id"]),
                        provider="openrouter",
                        context_length=m.get("context_length", 8192),
                        is_free=True
                    )
                    free_models.append(mi)
                    
            # Update cache (store dicts)
            self.persistence.set("or_models_time", now)
            self.persistence.set("or_models_data", [m.__dict__ for m in free_models])
            self.persistence.save()
            
            return free_models
        except requests.RequestException as e:
            LOG.warning("Failed to fetch OpenRouter models: %s", e)
            if cached_data:
                return [ModelInfo(**m) for m in cached_data]
            return []

    def stream(self, messages: list[dict[str, str]], model: str) -> Generator[str, None, None]:
        """Stream a response from OpenRouter."""
        if not self.api_key:
            yield "OpenRouter API key is not configured. Please add OPENROUTER_API_KEY to your .env file."
            return

        # Enforce free-only rule at the inference layer
        allowed_models = {m.id for m in self.get_models(force_refresh=False)}
        if model not in allowed_models and model != "openrouter/free":
            LOG.error("Attempted to use unauthorized or paid model: %s", model)
            raise ValueError(f"FRIDAY is strictly restricted to free models. '{model}' is not allowed.")

        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "temperature": CONFIG.temperature,
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://friday.ai",
            "X-Title": "FRIDAY IDE",
            "Content-Type": "application/json"
        }
        
        # We use a tuple for timeout: (connect_timeout, read_timeout)
        # This prevents the initial TCP/TLS handshake from hanging indefinitely
        try:
            with self._session.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                stream=True,
                timeout=(5, CONFIG.response_timeout),
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if line:
                        line = line.decode("utf-8")
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                choices = data.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    if "content" in delta:
                                        yield delta["content"]
                            except json.JSONDecodeError:
                                pass
        except requests.HTTPError as e:
            if e.response is not None:
                LOG.error("OpenRouter HTTP Error: %s %s", e.response.status_code, e.response.reason)
                LOG.error("OpenRouter Response Body: %s", e.response.text)
                if e.response.status_code == 401:
                    LOG.error("Authentication failure. Check if the API key is active and has sufficient credits.")
                    yield "\n\n[System] OpenRouter Authentication Failed. Please check if your API key in .env is valid."
                    return
                yield f"\n\n[System] OpenRouter API Error: {e.response.status_code} {e.response.reason}"
            else:
                LOG.error("OpenRouter HTTP Error (no response object): %s", e)
                yield f"\n\n[System] OpenRouter Connection Error: {e}"
            return
        except requests.RequestException as e:
            LOG.error("OpenRouter streaming failed with exception: %s", e)
            yield f"\n\n[System] OpenRouter Request Failed: {e}"
            return
