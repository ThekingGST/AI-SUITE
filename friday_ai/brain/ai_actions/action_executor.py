"""Action Executor: Orchestrates the execution of AI actions."""

from __future__ import annotations

from PyQt5.QtCore import QObject

from friday_ai.brain.ai_actions.action_context import AIActionRequest
from friday_ai.brain.ai_actions.prompt_templates import build_action_prompt
from friday_ai.brain.ai_orchestrator import AIOrchestrator
from shared.logger import get_logger

LOG = get_logger("friday.action_executor")


class ActionExecutor(QObject):
    """Executes an AI Action by delegating to the Orchestrator."""
    
    def __init__(self, orchestrator: AIOrchestrator, parent: QObject | None = None):
        super().__init__(parent)
        self.orchestrator = orchestrator
        self._active_actions: dict[str, AIActionRequest] = {}
        
        from friday_ai.brain.request_scheduler import RequestState
        self.orchestrator.scheduler.request_state_changed.connect(self._on_request_state_changed)

    def execute(self, request: AIActionRequest) -> None:
        """Process and execute the action request."""
        
        # 1. Validation
        if request.action.requires_selection and not request.context.selected_text:
            LOG.warning("Action %s requires selection, but none was provided.", request.action.id)
            return

        # 2. Build Prompt
        formatted_prompt = build_action_prompt(request.action.id, request.context)
        
        # 3. Submit to Orchestrator
        req_id = self.orchestrator.submit_prompt(formatted_prompt, action=request.action.id)
        if req_id:
            self._active_actions[req_id] = request

    def _on_request_state_changed(self, request_id: str, state) -> None:
        from friday_ai.brain.request_scheduler import RequestState
        if request_id not in self._active_actions:
            return
            
        if state in (RequestState.COMPLETED, RequestState.CANCELLED, RequestState.FAILED):
            request = self._active_actions.pop(request_id)
            metrics = None
            
            # Find metrics in session history
            for m in request.session.metrics_history:
                if m.request_id == request_id:
                    metrics = m
                    break
                    
            if metrics:
                provider = metrics.provider
                model = metrics.model
                elapsed = metrics.total_time_ms
                cancelled = metrics.cancelled
                success = not metrics.error_type and not metrics.cancelled
            else:
                provider = "Unknown"
                model = "Unknown"
                elapsed = 0.0
                cancelled = (state == RequestState.CANCELLED)
                success = (state == RequestState.COMPLETED)

            LOG.info(
                "AI Action Finished\n"
                "Action: %s\n"
                "Language: %s\n"
                "Selection Length: %d\n"
                "Provider: %s\n"
                "Model: %s\n"
                "Elapsed Time: %.2f ms\n"
                "Cancelled: %s\n"
                "Success: %s\n",
                request.action.id,
                request.context.language,
                len(request.context.selected_text),
                provider,
                model,
                elapsed,
                cancelled,
                success
            )
            
            if success:
                from friday_ai.core.signals import signals
                # Grab the final text from the session memory
                messages = request.session.memory.get_messages()
                if messages and messages[-1]["role"] == "assistant":
                    final_text = messages[-1]["content"]
                    signals.ai_action_finished.emit(request, final_text)
