import uuid
from typing import Dict, Any, Callable
from ai_suite.core.assistant.types import DelegationRequest, DelegationResponse
from ai_suite.core.assistant.registry import AssistantRegistry
from jarvis_ai.utils.logger import LOGGER

class TaskDelegationEngine:
    """Handles asynchronous task delegation between assistants."""
    
    def __init__(self, event_bus, registry: AssistantRegistry):
        self.event_bus = event_bus
        self.registry = registry
        self._pending_tasks: Dict[str, Callable] = {}
        
    def delegate_task(self, request: DelegationRequest, callback: Callable[[DelegationResponse], None]) -> str:
        """Dispatches a task to the target assistant asynchronously."""
        target = self.registry.get_assistant(request.context.target_assistant_id)
        if not target:
            LOGGER.error(f"Cannot delegate task to unknown assistant: {request.context.target_assistant_id}")
            callback(DelegationResponse(request.id, "FAILED", None, "Unknown assistant"))
            return request.id
            
        LOGGER.info(f"Delegating task [{request.id}] from {request.context.source_assistant_id} to {target.id}")
        
        self._pending_tasks[request.id] = callback
        
        # Fire EventBus event so the target assistant can pick it up
        # In a full implementation, the target assistant's lifecycle manager would transition to DELEGATING/BUSY
        self.event_bus.assistantDelegated.emit(target.id)
        
        # For prototype purposes, we'll simulate the target assistant finishing the task immediately
        self._simulate_execution(request)
        
        return request.id
        
    def _simulate_execution(self, request: DelegationRequest):
        # Simulate processing delay and success
        result = f"Simulated result for task '{request.context.task}' executed by {request.context.target_assistant_id}"
        response = DelegationResponse(request.id, "SUCCESS", result)
        self.complete_delegation(response)
        
    def complete_delegation(self, response: DelegationResponse) -> None:
        """Called by the target assistant when the task is finished."""
        if response.request_id in self._pending_tasks:
            callback = self._pending_tasks.pop(response.request_id)
            LOGGER.info(f"Task [{response.request_id}] completed with status: {response.status}")
            callback(response)
