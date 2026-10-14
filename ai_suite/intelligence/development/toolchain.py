import time
import shutil
from ..base import BaseInspector
from ..types import InspectionReport, HealthStatus

class ToolchainInspector(BaseInspector):
    @property
    def name(self) -> str:
        return "toolchain"

    def inspect(self) -> InspectionReport:
        tools = ["git", "node", "npm", "java", "gcc", "clang", "cmake", "docker"]
        found = {}
        for t in tools:
            found[t] = bool(shutil.which(t))
            
        summary = "Installed tools: " + ", ".join([k for k, v in found.items() if v])
        
        return InspectionReport(
            inspector=self.name,
            status=HealthStatus.HEALTHY,
            timestamp=time.time(),
            summary=summary,
            details={"installed": found},
            metrics={}
        )
