"""Request Scheduler: Manages queuing, cancellation, and execution of AI requests."""

from __future__ import annotations
import uuid
from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional, Callable

from PyQt5.QtCore import QObject, pyqtSignal as Signal, pyqtSlot as Slot
from friday_ai.brain.metrics import AIMetrics


class RequestState(Enum):
    QUEUED = auto()
    RUNNING = auto()
    STREAMING = auto()
    CANCELLED = auto()
    COMPLETED = auto()
    FAILED = auto()


@dataclass
class AIRequest:
    """Represents a single AI generation request."""
    id: str
    metrics: AIMetrics
    worker: Optional[QObject] = None
    state: RequestState = RequestState.QUEUED


class RequestScheduler(QObject):
    """Manages execution of AI requests, ensuring obsolete requests are cancelled."""
    
    # Emits when the active request changes state
    request_state_changed = Signal(str, object)  # id, state
    
    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.active_request: Optional[AIRequest] = None
        self._pending_request: Optional[AIRequest] = None
        
    def schedule(self, request: AIRequest, worker: QObject) -> None:
        """Schedule a new request for execution. Cancels current if active."""
        request.worker = worker
        
        if self.active_request and self.active_request.state in (RequestState.RUNNING, RequestState.STREAMING):
            # We have an active request. Cancel it.
            self._cancel_active()
            self._pending_request = request
            # We must wait for the active worker to finish (via signals) before starting the new one.
        else:
            self._start_request(request)
            
    def _cancel_active(self) -> None:
        """Cancel the currently active request."""
        if self.active_request and self.active_request.worker:
            self.active_request.state = RequestState.CANCELLED
            self.request_state_changed.emit(self.active_request.id, RequestState.CANCELLED)
            self.active_request.worker.cancel()
            
    def _start_request(self, request: AIRequest) -> None:
        self.active_request = request
        self.active_request.state = RequestState.RUNNING
        self.request_state_changed.emit(self.active_request.id, RequestState.RUNNING)
        self.active_request.worker.start()

    def on_worker_finished(self, request_id: str) -> None:
        """Called when a worker completes, either via success, error, or cancellation."""
        if self.active_request and self.active_request.id == request_id:
            # We don't overwrite COMPLETED/FAILED/CANCELLED if already set
            if self.active_request.state in (RequestState.RUNNING, RequestState.STREAMING):
                self.active_request.state = RequestState.COMPLETED
                self.request_state_changed.emit(request_id, RequestState.COMPLETED)
                
            self.active_request = None
            
            # Start pending request if any
            if self._pending_request:
                next_req = self._pending_request
                self._pending_request = None
                self._start_request(next_req)
                
    def on_worker_chunk(self, request_id: str) -> None:
        if self.active_request and self.active_request.id == request_id:
            if self.active_request.state == RequestState.RUNNING:
                self.active_request.state = RequestState.STREAMING
                self.request_state_changed.emit(request_id, RequestState.STREAMING)

    def cancel_all(self) -> None:
        """Cancel everything and clear pending."""
        self._pending_request = None
        self._cancel_active()
