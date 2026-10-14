"""AI Session: Encapsulates state for a single conversation or agent task."""

from __future__ import annotations
from dataclasses import dataclass, field

from friday_ai.brain.memory import ConversationMemory
from friday_ai.brain.model_registry import ModelProfile
from friday_ai.brain.metrics import AIMetrics


@dataclass
class AISession:
    """Represents an ongoing interaction context."""
    id: str
    memory: ConversationMemory
    profile: ModelProfile = ModelProfile.BALANCED
    
    # Store metrics from all requests in this session
    metrics_history: list[AIMetrics] = field(default_factory=list)
    
    def add_metrics(self, metrics: AIMetrics) -> None:
        self.metrics_history.append(metrics)
