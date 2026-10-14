import time
import sys
import os
from ..base import BaseInspector
from ..types import InspectionReport, HealthStatus

class PythonInspector(BaseInspector):
    @property
    def name(self) -> str:
        return "python"

    def inspect(self) -> InspectionReport:
        active_venv = os.environ.get("VIRTUAL_ENV", "None")
        version = sys.version.split()[0]
        
        return InspectionReport(
            inspector=self.name,
            status=HealthStatus.HEALTHY,
            timestamp=time.time(),
            summary=f"Python {version} (venv: {active_venv})",
            details={
                "version": version,
                "executable": sys.executable,
                "virtual_env": active_venv,
                "platform": sys.platform
            },
            metrics={}
        )
