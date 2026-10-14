import time
import urllib.request
import json
from ..base import BaseInspector
from ..types import InspectionReport, HealthStatus

class OllamaInspector(BaseInspector):
    @property
    def name(self) -> str:
        return "ollama"

    def inspect(self) -> InspectionReport:
        try:
            req = urllib.request.Request("http://localhost:11434/api/tags")
            with urllib.request.urlopen(req, timeout=2) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    models = [m["name"] for m in data.get("models", [])]
                    
                    status = HealthStatus.HEALTHY if models else HealthStatus.WARNING
                    summary = f"Ollama is running with {len(models)} models loaded." if models else "Ollama is running, but no models found."
                    
                    return InspectionReport(
                        inspector=self.name,
                        status=status,
                        timestamp=time.time(),
                        summary=summary,
                        details={"models": models},
                        metrics={"model_count": float(len(models))}
                    )
        except Exception as e:
            return InspectionReport(
                inspector=self.name,
                status=HealthStatus.UNKNOWN,
                timestamp=time.time(),
                summary=f"Ollama is offline or unreachable: {e}"
            )
        
        return InspectionReport(
            inspector=self.name,
            status=HealthStatus.UNKNOWN,
            timestamp=time.time(),
            summary="Unexpected state."
        )
