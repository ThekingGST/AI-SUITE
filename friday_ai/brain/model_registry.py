"""Model Registry: Single source of truth for model capabilities and metadata."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto


class ModelProfile(Enum):
    """User-selectable profiles influencing routing."""
    FAST = auto()
    BALANCED = auto()
    DEEP_REASONING = auto()
    OFFLINE_ONLY = auto()
    CLOUD_PREFERRED = auto()
    CODING = auto()


@dataclass
class ModelCapabilities:
    """Metadata describing what a model can do and how well it does it."""
    provider: str
    model_id: str
    is_local: bool
    
    # Capabilities (0.0 to 10.0)
    reasoning_capability: float = 5.0
    coding_capability: float = 5.0
    chat_capability: float = 5.0
    speed_rating: float = 5.0
    
    # Features
    context_window: int = 8192
    vision_support: bool = False
    tool_calling_support: bool = False
    streaming_support: bool = True
    json_output: bool = False


# A hardcoded set of baseline capabilities for known models
# Any model not in this list gets a default capability set.
KNOWN_MODELS_DB = {
    "qwen3:latest": ModelCapabilities(
        provider="ollama", model_id="qwen3:latest", is_local=True,
        reasoning_capability=6.0, coding_capability=7.5, chat_capability=7.0, speed_rating=8.0,
        context_window=8192, streaming_support=True, json_output=True
    ),
    "openrouter/free": ModelCapabilities(
        provider="openrouter", model_id="openrouter/free", is_local=False,
        reasoning_capability=5.0, coding_capability=5.0, chat_capability=6.0, speed_rating=7.0,
        context_window=8192, streaming_support=True, json_output=False
    )
}


class ModelRegistry:
    """Maintains the unified catalog of available models and their capabilities."""
    
    def __init__(self):
        # provider -> model_id -> ModelCapabilities
        self._registry: dict[str, dict[str, ModelCapabilities]] = {}
        
    def register_model(self, provider: str, model_id: str, baseline_overrides: dict = None) -> None:
        """Register a model discovered dynamically."""
        if provider not in self._registry:
            self._registry[provider] = {}
            
        # If it's a known model, use its predefined baseline, else use defaults
        base_cap = KNOWN_MODELS_DB.get(model_id)
        if base_cap:
            # We copy it because multiple providers might theoretically serve the same model id
            cap = ModelCapabilities(**base_cap.__dict__)
        else:
            # Default for unknown models
            is_local = (provider == "ollama")
            cap = ModelCapabilities(
                provider=provider, model_id=model_id, is_local=is_local
            )
            
        if baseline_overrides:
            for k, v in baseline_overrides.items():
                setattr(cap, k, v)
                
        self._registry[provider][model_id] = cap

    def get_capabilities(self, provider: str, model_id: str) -> ModelCapabilities | None:
        """Retrieve capabilities for a specific model."""
        return self._registry.get(provider, {}).get(model_id)

    def get_all_models(self) -> list[ModelCapabilities]:
        """Return all registered models."""
        models = []
        for prov_models in self._registry.values():
            models.extend(prov_models.values())
        return models
