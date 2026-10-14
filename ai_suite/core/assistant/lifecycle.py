from typing import Dict, Optional, Any
from ai_suite.core.assistant.types import AssistantState
from jarvis_ai.utils.logger import LOGGER

class AssistantLifecycleManager:
    """Manages the state transitions of an assistant."""
    def __init__(self, event_bus: Any, assistant_id: str):
        self.event_bus = event_bus
        self.assistant_id = assistant_id
        self._state = AssistantState.UNLOADED
        
    @property
    def state(self) -> AssistantState:
        return self._state
        
    def transition_to(self, new_state: AssistantState) -> None:
        """Transitions to a new state and emits events."""
        if self._state == new_state:
            return
            
        old_state = self._state
        self._state = new_state
        LOGGER.info(f"[Assistant {self.assistant_id}] Lifecycle transition: {old_state.value} -> {new_state.value}")
        
        # Emit generic state changed event
        self.event_bus.assistantStateChanged.emit(self.assistant_id, old_state.value, new_state.value)
        
        # Emit specific lifecycle events
        if new_state == AssistantState.READY:
            self.event_bus.assistantReady.emit(self.assistant_id)
        elif new_state == AssistantState.BUSY:
            self.event_bus.assistantBusy.emit(self.assistant_id)
        elif new_state == AssistantState.DELEGATING:
            self.event_bus.assistantDelegated.emit(self.assistant_id)
