from typing import Optional
from ai_suite.core.assistant.registry import AssistantRegistry
from jarvis_ai.utils.logger import LOGGER

class AssistantRouter:
    """Routes incoming requests to the best available assistant."""
    
    def __init__(self, registry: AssistantRegistry):
        self.registry = registry
        
    def route_request(self, text: str) -> str:
        """Determines the ID of the best assistant to handle the request."""
        
        # 1. Deterministic capability/keyword matching
        text_lower = text.lower()
        candidates = self.registry.get_all_assistants()
        
        for assistant in candidates:
            for keyword in assistant.routing_keywords:
                if keyword in text_lower:
                    LOGGER.info(f"[AssistantRouter] Routed to {assistant.id} via deterministic keyword '{keyword}'")
                    return assistant.id
                    
        # 2. Lightweight Intent Classification (mocked for prototype)
        LOGGER.info("[AssistantRouter] Deterministic routing failed. Falling back to lightweight intent classification.")
        if "code" in text_lower or "script" in text_lower:
            return "friday"
        elif "see" in text_lower or "camera" in text_lower:
            return "jarvis"
            
        # Default to JARVIS
        LOGGER.info("[AssistantRouter] Routing defaulted to jarvis")
        return "jarvis"
