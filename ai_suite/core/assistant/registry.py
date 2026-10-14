from typing import Dict, List, Optional
from ai_suite.core.assistant.types import AssistantProfile
from jarvis_ai.utils.logger import LOGGER

class AssistantRegistry:
    """Central registry for discovering and querying independent assistants."""
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self._assistants: Dict[str, AssistantProfile] = {}

    def register(self, profile: AssistantProfile) -> None:
        if profile.id in self._assistants:
            LOGGER.warning(f"Assistant {profile.id} is already registered.")
            return
            
        self._assistants[profile.id] = profile
        LOGGER.info(f"Registered assistant: {profile.id} ({profile.display_name})")
        
        # Fire event
        self.event_bus.assistantRegistered.emit(profile.id)

    def get_assistant(self, assistant_id: str) -> Optional[AssistantProfile]:
        return self._assistants.get(assistant_id)

    def get_all_assistants(self) -> List[AssistantProfile]:
        return list(self._assistants.values())

    def get_by_capability(self, capability: str) -> List[AssistantProfile]:
        """Returns assistants that support the given capability, ordered by routing priority."""
        matches = []
        for profile in self._assistants.values():
            if capability in profile.supported_capabilities or capability in profile.default_capabilities:
                matches.append(profile)
                
        # Sort by routing priority (highest first)
        matches.sort(key=lambda p: p.routing_priority, reverse=True)
        return matches
