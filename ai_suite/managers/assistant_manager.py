from typing import Any
from jarvis_ai.utils.logger import LOGGER

class AssistantManager:
    """Thin compatibility adapter forwarding to the new Assistant subsystem."""
    def __init__(self, event_bus: Any, registry: Any = None):
        self.event_bus = event_bus
        self.registry = registry

    def register_assistant(self, md: Any) -> None:
        """Legacy registration. Will be replaced by direct registry calls in main.py."""
        LOGGER.warning("Legacy AssistantManager.register_assistant called.")

    def switch_assistant(self, id: str) -> None:
        """Legacy switch."""
        LOGGER.info(f"Legacy AssistantManager switching to {id}")

