import uuid
from typing import List, Optional, Tuple
from ai_suite.core.assistant.registry import AssistantRegistry
from ai_suite.core.assistant.delegation import TaskDelegationEngine
from ai_suite.core.assistant.context import SharedContextTransfer
from ai_suite.core.assistant.types import DelegationRequest, DelegationTransparency
from jarvis_ai.utils.logger import LOGGER

class TaskPlanner:
    """Analyzes requests, identifies required capabilities, and coordinates execution."""
    
    def __init__(self, registry: AssistantRegistry, delegation_engine: TaskDelegationEngine, context_transfer: SharedContextTransfer):
        self.registry = registry
        self.delegation_engine = delegation_engine
        self.context_transfer = context_transfer
        
    def analyze_and_execute(self, source_assistant_id: str, request_text: str, current_workspace_id: str) -> str:
        """
        1. Analyzes request to find required capabilities.
        2. If source assistant lacks capability, finds best assistant.
        3. Delegates task.
        """
        required_capability, intent = self._extract_capability_and_intent(request_text)
        LOGGER.info(f"[TaskPlanner] Analyzed request. Required capability: {required_capability}")
        
        source = self.registry.get_assistant(source_assistant_id)
        if not source:
            return "Error: Source assistant not found."
            
        if required_capability and required_capability not in source.supported_capabilities:
            # Delegate!
            candidates = self.registry.get_by_capability(required_capability)
            if not candidates:
                return f"Error: No assistant supports {required_capability}."
                
            target = candidates[0]
            LOGGER.info(f"[TaskPlanner] Decided to delegate from {source.id} to {target.id}")
            
            context = self.context_transfer.build_delegation_context(
                task=request_text,
                goal=intent,
                constraints=[],
                workspace_id=current_workspace_id,
                source_id=source.id,
                target_id=target.id,
                user_intent=intent
            )
            
            req = DelegationRequest(
                id=str(uuid.uuid4()),
                context=context,
                transparency=DelegationTransparency.INFORMATIONAL
            )
            
            # Since this is synchronous for the prototype verification, we'll capture the result
            final_result = None
            def on_complete(response):
                nonlocal final_result
                final_result = response.result
                
            self.delegation_engine.delegate_task(req, on_complete)
            return f"[{target.display_name} assisted]: {final_result}"
            
        # If no delegation needed, just return a generic success
        return f"[{source.display_name} executed directly]"
        
    def _extract_capability_and_intent(self, text: str) -> Tuple[Optional[str], str]:
        """Simple keyword-based capability extraction for prototype."""
        text_lower = text.lower()
        if "sort a list" in text_lower or "script" in text_lower or "code" in text_lower:
            return "code_generation", "Generate code"
        if "ocr" in text_lower or "extract text" in text_lower:
            return "ocr", "Extract text from image"
        if "camera" in text_lower or "visible" in text_lower:
            return "vision", "Analyze camera feed"
            
        return None, "General inquiry"
