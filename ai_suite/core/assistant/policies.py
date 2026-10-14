from typing import Any, Dict
from ai_suite.core.assistant.types import ReasoningPolicy
from ai_suite.managers.model_manager import ModelManager

class PolicyAdapter:
    """Adapts ReasoningPolicy to ModelManager."""
    def __init__(self, model_manager: ModelManager):
        self.model_manager = model_manager
        
    def generate(self, policy: ReasoningPolicy, context: list, **kwargs) -> Any:
        """Invokes the ModelManager using the rules of the reasoning policy."""
        # For v1, we map reasoning types to model priorities.
        # e.g., "structured_code" -> precise code models
        # "conversational" -> fast conversational models
        
        # In a real implementation, ModelManager would accept the policy directly.
        # Here we just pass through to the shared ModelManager.
        
        return self.model_manager.generate(context, **kwargs)
