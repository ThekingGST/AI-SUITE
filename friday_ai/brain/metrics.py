"""AI performance metrics tracking."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class AIMetrics:
    """Structured metrics for an AI generation request."""
    request_id: str = ""
    provider: str = ""
    model: str = ""
    
    # Request lifecycle
    context_build_ms: float = 0.0
    request_start_ms: float = 0.0
    first_token_ms: float = 0.0
    first_render_ms: float = 0.0  # Time when UI actually receives it
    total_time_ms: float = 0.0
    
    # Token approximation
    chunks_received: int = 0
    estimated_tokens: int = 0
    tokens_per_second: float = 0.0
    
    # Status
    cancelled: bool = False
    error_type: Optional[str] = None
    retry_count: int = 0
    
    # Granular details
    context_breakdown: dict = None
    
    def __post_init__(self):
        if self.context_breakdown is None:
            self.context_breakdown = {}
    
    def log_report(self, logger) -> None:
        """Dump a structured representation to the logger."""
        ttft = (self.first_token_ms - self.request_start_ms) if self.first_token_ms else 0.0
        ttfr = (self.first_render_ms - self.request_start_ms) if self.first_render_ms else 0.0
        
        report = (
            f"[AIMetrics] RequestID={self.request_id} | Provider={self.provider} | Model={self.model} | "
            f"ContextBuild={self.context_build_ms:.1f}ms | TTFT={ttft:.1f}ms | UI_Latency={ttfr:.1f}ms | "
            f"Speed={self.tokens_per_second:.1f} T/s | Total={self.total_time_ms:.1f}ms | "
            f"Chunks={self.chunks_received} | Tokens(Est)={self.estimated_tokens}"
        )
        if self.error_type:
            report += f" | Error={self.error_type}"
        if self.cancelled:
            report += " | [CANCELLED]"
            
        logger.info(report)
        if self.context_breakdown:
            breakdown_str = " | ".join(f"{k}={v:.1f}ms" for k, v in self.context_breakdown.items())
            logger.info(f"[AIMetrics Context Breakdown] {breakdown_str}")
