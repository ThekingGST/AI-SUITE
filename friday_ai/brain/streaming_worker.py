"""Streaming Worker for executing AI generations asynchronously."""

from __future__ import annotations
import time

from PyQt5.QtCore import QThread, pyqtSignal as Signal

from friday_ai.brain.metrics import AIMetrics
from shared.logger import get_logger

LOG = get_logger("friday.streaming_worker")


class StreamingWorker(QThread):
    """Background thread specifically for AI streaming."""
    chunk = Signal(str)
    result = Signal(str)
    error = Signal(Exception, object)  # Passes exception and the metrics object
    completed = Signal(object)         # Passes the completed metrics object

    def __init__(self, provider, messages, model, metrics: AIMetrics, parent=None):
        super().__init__(parent)
        self.provider = provider
        self.messages = messages
        self.model = model
        self.metrics = metrics
        self.is_cancelled = False

    def cancel(self):
        self.is_cancelled = True

    def run(self):
        LOG.info("StreamingWorker: Starting background generation.")
        self.metrics.request_start_ms = time.time() * 1000.0
        try:
            full_response = []
            chunk_count = 0
            for c in self.provider.stream(self.messages, self.model):
                if self.is_cancelled:
                    LOG.warning("StreamingWorker: Generation cancelled.")
                    self.metrics.cancelled = True
                    break
                
                if chunk_count == 0:
                    self.metrics.first_token_ms = time.time() * 1000.0
                    
                self.chunk.emit(c)
                full_response.append(c)
                chunk_count += 1
            
            self.metrics.total_time_ms = time.time() * 1000.0 - self.metrics.request_start_ms
            self.metrics.chunks_received = chunk_count
            self.metrics.estimated_tokens = chunk_count  # Approximation
            
            # TTFT and Token Speed
            ttft = self.metrics.first_token_ms - self.metrics.request_start_ms if self.metrics.first_token_ms else 0.0
            gen_time = self.metrics.total_time_ms - ttft
            if gen_time > 0 and chunk_count > 0:
                self.metrics.tokens_per_second = (chunk_count / gen_time) * 1000.0
            
            final_text = "".join(full_response)
            LOG.info("StreamingWorker: Generation complete. Total chunks: %d", chunk_count)
            self.result.emit(final_text)
            self.completed.emit(self.metrics)
            
        except Exception as e:
            self.metrics.error_type = type(e).__name__
            self.metrics.total_time_ms = time.time() * 1000.0 - self.metrics.request_start_ms
            LOG.error("StreamingWorker: Error during generation: %s", e)
            self.error.emit(e, self.metrics)
