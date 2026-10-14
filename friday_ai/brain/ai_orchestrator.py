"""AI Orchestrator: Central coordinator for all AI operations."""

from __future__ import annotations
import time
import uuid

from PyQt5.QtCore import QObject

from friday_ai.brain.ai_session import AISession
from friday_ai.brain.task_analyzer import TaskAnalyzer, RuleBasedTaskAnalyzer
from friday_ai.brain.context_optimizer import ContextOptimizer
from friday_ai.brain.model_router import ModelRouter
from friday_ai.brain.request_scheduler import RequestScheduler, AIRequest, RequestState
from friday_ai.brain.model_registry import ModelRegistry
from friday_ai.brain.context_builder import ContextBuilder
from friday_ai.services.provider_manager import ProviderManager
from friday_ai.brain.metrics import AIMetrics
from friday_ai.core.signals import signals
from shared.logger import get_logger

LOG = get_logger("friday.ai_orchestrator")


class AIOrchestrator(QObject):
    """Coordinates Task Analysis, Context Optimization, Routing, and Execution."""
    
    def __init__(
        self,
        session: AISession,
        context_builder: ContextBuilder,
        provider_manager: ProviderManager,
        registry: ModelRegistry,
        parent: QObject | None = None
    ):
        super().__init__(parent)
        self.session = session
        self.context_builder = context_builder
        self.provider_manager = provider_manager
        self.registry = registry
        
        # Instantiate sub-components
        self.task_analyzer: TaskAnalyzer = RuleBasedTaskAnalyzer()
        self.context_optimizer = ContextOptimizer()
        self.model_router = ModelRouter(self.registry)
        self.scheduler = RequestScheduler(self)
        
        self.scheduler.request_state_changed.connect(self._on_request_state_changed)
        
    def submit_prompt(self, user_prompt: str, action: str = "") -> str | None:
        """Process an incoming prompt through the entire AI pipeline."""
        
        req_id = str(uuid.uuid4())
        metrics = AIMetrics(request_id=req_id)
        
        # 1. Task Analysis
        intent = self.task_analyzer.analyze(user_prompt, action)
        LOG.info("AIOrchestrator: Intent classified as %s", intent.name)
        
        # 2. Context Optimization
        has_selection = bool(self.context_builder.workspace.get_context().selected_code)
        context_plan = self.context_optimizer.optimize(intent, has_selection=has_selection)
        
        # Build Context String
        t0 = time.time() * 1000.0
        sys_msg = self.context_builder.build_system_prompt(user_prompt, action, metrics=metrics, plan=context_plan)
        user_msg = self.context_builder.build_user_prompt(user_prompt, action)
        metrics.context_build_ms = time.time() * 1000.0 - t0
        
        messages = [
            {"role": "system", "content": sys_msg},
            *self.session.memory.get_messages(),
            {"role": "user", "content": user_msg}
        ]
        
        # Store in conversation memory
        self.session.memory.add_message("user", user_msg)
        
        # 3. Model Routing
        # Sync dynamically available models into the registry
        all_prov_models = self.provider_manager.get_all_models()
        for prov_name, prov_models in all_prov_models.items():
            for m in prov_models:
                self.registry.register_model(prov_name, m.id)
                
        health_status = self.provider_manager.get_all_health()
        best_model = self.model_router.get_best_model(intent, self.session.profile, health_status)
        
        if not best_model:
            signals.ai_error.emit("No suitable AI models available for this task.")
            return None
            
        metrics.provider = best_model.provider
        metrics.model = best_model.model_id
        LOG.info("AIOrchestrator: Routed to %s/%s", best_model.provider, best_model.model_id)
        
        provider = self.provider_manager.get_provider(best_model.provider)
        if not provider:
            signals.ai_error.emit(f"Provider '{best_model.provider}' is not properly loaded.")
            return None
            
        # 4. Scheduling
        request = AIRequest(id=req_id, metrics=metrics)
        
        # Create worker (we import it here or pass it to scheduler)
        from friday_ai.brain.streaming_worker import StreamingWorker
        worker = StreamingWorker(provider, messages, best_model.model_id, metrics, parent=self)
        
        # Connect worker signals directly to the UI emit channels, but let scheduler track state
        worker.chunk.connect(lambda c: self._on_chunk(req_id, c))
        worker.result.connect(lambda text: self._on_done(req_id, text))
        worker.error.connect(lambda e, m: self._on_error(req_id, e, m))
        worker.completed.connect(lambda m: self.scheduler.on_worker_finished(req_id))
        
        self.scheduler.schedule(request, worker)
        return req_id
        
    def cancel_active(self) -> None:
        """Cancel whatever is currently running."""
        self.scheduler.cancel_all()
        
    # --- Internal Event Handlers ---
    
    def _on_request_state_changed(self, request_id: str, state: RequestState) -> None:
        LOG.info("AIOrchestrator: Request %s transitioned to %s", request_id, state.name)
        if state == RequestState.RUNNING:
            signals.ai_busy.emit(True)
        elif state in (RequestState.COMPLETED, RequestState.CANCELLED, RequestState.FAILED):
            signals.ai_busy.emit(False)
            
    def _on_chunk(self, request_id: str, chunk: str) -> None:
        self.scheduler.on_worker_chunk(request_id)
        if self.scheduler.active_request and self.scheduler.active_request.id == request_id:
            m = self.scheduler.active_request.metrics
            if m.first_render_ms == 0.0:
                m.first_render_ms = time.time() * 1000.0
            signals.ai_chunk_received.emit(chunk)
            
    def _on_done(self, request_id: str, final_text: str) -> None:
        if self.scheduler.active_request and self.scheduler.active_request.id == request_id:
            self.session.memory.add_message("assistant", final_text)
            self.session.add_metrics(self.scheduler.active_request.metrics)
            self.scheduler.active_request.metrics.log_report(LOG)
            
            # Inform ProviderManager health of success
            h = self.provider_manager.get_health(self.scheduler.active_request.metrics.provider)
            if h:
                m = self.scheduler.active_request.metrics
                ttft = m.first_token_ms - m.request_start_ms if m.first_token_ms else 0.0
                h.record_success(m.total_time_ms, ttft, m.tokens_per_second)
                
            signals.ai_response_complete.emit(final_text)

    def _on_error(self, request_id: str, error: Exception, metrics: AIMetrics) -> None:
        LOG.error("AIOrchestrator: Error for %s - %s", request_id, error)
        self.session.add_metrics(metrics)
        metrics.log_report(LOG)
        
        # Inform ProviderManager health of failure
        h = self.provider_manager.get_health(metrics.provider)
        if h:
            h.record_failure()
            
        # UI Error mapping
        user_msg = f"Request Failed ({metrics.error_type})"
        if "Unauthorized" in str(error) or "401" in str(error):
            user_msg = "Authentication failed. Please check your API key."
        elif "Connection" in str(error) or "Timeout" in str(error):
            user_msg = "Network connection failed. Please check your internet connection."
        
        signals.ai_error.emit(user_msg)
        self.scheduler.on_worker_finished(request_id)
