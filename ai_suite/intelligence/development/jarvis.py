import time
import threading
from ..base import BaseInspector
from ..types import InspectionReport, HealthStatus

class JarvisInspector(BaseInspector):
    @property
    def name(self) -> str:
        return "jarvis"

    def inspect(self) -> InspectionReport:
        threads = threading.enumerate()
        alive_names = [t.name for t in threads if t.is_alive()]
        
        mic_alive = any("AudioCapture" in name for name in alive_names)
        pipe_alive = any("PipelineWorker" in name for name in alive_names)
        router_alive = any("CommandRouter" in name for name in alive_names)
        
        # A simple heuristic check for threads
        # In a real environment, this might access ServiceContainer or specific managers
        
        status = HealthStatus.HEALTHY
        if not mic_alive or not pipe_alive:
            status = HealthStatus.WARNING
            
        summary = "JARVIS appears healthy."
        if status == HealthStatus.WARNING:
            summary = "JARVIS has warnings: some essential threads are missing."
            
        return InspectionReport(
            inspector=self.name,
            status=status,
            timestamp=time.time(),
            summary=summary,
            details={
                "microphone_alive": mic_alive,
                "pipeline_alive": pipe_alive,
                "router_alive": router_alive,
                "active_threads": len(threads),
                "thread_names": alive_names
            },
            metrics={"thread_count": float(len(threads))}
        )
