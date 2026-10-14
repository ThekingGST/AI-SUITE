"""Provider manager — The single gateway to all AI backends."""

from __future__ import annotations

from PyQt5.QtCore import QObject

from friday_ai.core.signals import signals
from friday_ai.services.providers.base import BaseProvider, ModelInfo
from friday_ai.services.persistence import WorkspacePersistence
from shared.logger import get_logger

LOG = get_logger("friday.provider_manager")


from dataclasses import dataclass
import time

@dataclass
class ProviderHealth:
    name: str
    is_available: bool = True
    success_count: int = 0
    failure_count: int = 0
    consecutive_failures: int = 0
    last_failure_time: float = 0.0
    avg_latency_ms: float = 0.0
    avg_ttft_ms: float = 0.0
    avg_tps: float = 0.0
    
    def record_success(self, latency_ms: float, ttft_ms: float, tps: float):
        self.success_count += 1
        self.consecutive_failures = 0
        # Rolling average approximation
        alpha = 0.3
        self.avg_latency_ms = (alpha * latency_ms) + ((1 - alpha) * self.avg_latency_ms) if self.avg_latency_ms else latency_ms
        self.avg_ttft_ms = (alpha * ttft_ms) + ((1 - alpha) * self.avg_ttft_ms) if self.avg_ttft_ms else ttft_ms
        self.avg_tps = (alpha * tps) + ((1 - alpha) * self.avg_tps) if self.avg_tps else tps
        
    def record_failure(self):
        self.failure_count += 1
        self.consecutive_failures += 1
        self.last_failure_time = time.time()
        
    @property
    def is_healthy(self) -> bool:
        """Heuristic for health. Unhealthy if >3 consecutive failures in the last 5 minutes."""
        if self.consecutive_failures >= 3:
            if (time.time() - self.last_failure_time) < 300:
                return False
        return self.is_available


class ProviderManager(QObject):
    """Manages AI providers and routes requests to the active one."""

    def __init__(self, persistence: WorkspacePersistence, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.persistence = persistence
        self._providers: dict[str, BaseProvider] = {}
        self._health: dict[str, ProviderHealth] = {}
        
        # Register standard providers
        from friday_ai.services.providers.ollama import OllamaProvider
        from friday_ai.services.providers.openrouter import OpenRouterProvider
        
        self.register_provider("ollama", OllamaProvider())
        self.register_provider("openrouter", OpenRouterProvider(persistence))
        
        self._active_provider = self.persistence.get("ai_provider", "ollama")
        self._active_model = self.persistence.get("ai_model", "qwen3")

        # Connect signals
        signals.ai_model_changed.connect(self._on_model_changed)

    def register_provider(self, name: str, provider: BaseProvider) -> None:
        """Register a new provider."""
        self._providers[name] = provider
        self._health[name] = ProviderHealth(name=name)
        
    def get_provider(self, name: str) -> BaseProvider | None:
        return self._providers.get(name)

    def get_health(self, name: str) -> ProviderHealth | None:
        return self._health.get(name)
        
    def get_all_health(self) -> dict[str, ProviderHealth]:
        return self._health

    @property
    def current_provider(self) -> str:
        return self._active_provider
        
    @property
    def current_model(self) -> str:
        return self._active_model

    def _on_model_changed(self, provider: str, model: str) -> None:
        self._active_provider = provider
        self._active_model = model
        self.persistence.set("ai_provider", provider)
        self.persistence.set("ai_model", model)
        self.persistence.save()
        LOG.info("Model changed to %s / %s", provider, model)

    def get_all_models(self) -> dict[str, list[ModelInfo]]:
        """Get models grouped by provider."""
        results = {}
        for name, provider in self._providers.items():
            try:
                results[name] = provider.get_models()
            except Exception as exc:
                LOG.warning("Failed to fetch models for %s: %s", name, exc)
                results[name] = []
        return results

    def provider_status(self) -> dict[str, bool]:
        """Check health of all registered providers. (Synchronous deep check)"""
        status = {}
        for name, provider in self._providers.items():
            try:
                is_avail = provider.health_check()
                status[name] = is_avail
                self._health[name].is_available = is_avail
            except Exception:
                status[name] = False
                self._health[name].is_available = False
        return status

