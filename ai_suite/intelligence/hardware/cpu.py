import time
import psutil
import platform
from ..base import BaseInspector
from ..types import InspectionReport, HealthStatus

class CPUInspector(BaseInspector):
    @property
    def name(self) -> str:
        return "cpu"

    def inspect(self) -> InspectionReport:
        percent = psutil.cpu_percent(interval=None) # type: ignore
        cores_phys = psutil.cpu_count(logical=False)
        cores_log = psutil.cpu_count(logical=True)
        try:
            freq = psutil.cpu_freq().current # type: ignore
        except Exception:
            freq = 0.0

        status = HealthStatus.HEALTHY
        if percent > 95:
            status = HealthStatus.CRITICAL
        elif percent > 80:
            status = HealthStatus.WARNING

        return InspectionReport(
            inspector=self.name,
            status=status,
            timestamp=time.time(),
            summary=f"CPU usage at {percent}% on {platform.processor()}",
            details={
                "processor": platform.processor(),
                "physical_cores": cores_phys,
                "logical_cores": cores_log,
            },
            metrics={
                "usage_percent": percent,
                "frequency_mhz": freq
            }
        )
