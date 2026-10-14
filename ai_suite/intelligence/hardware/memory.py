import time
import psutil
from ..base import BaseInspector
from ..types import InspectionReport, HealthStatus

class MemoryInspector(BaseInspector):
    @property
    def name(self) -> str:
        return "memory"

    def inspect(self) -> InspectionReport:
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        percent = mem.percent
        status = HealthStatus.HEALTHY
        if percent > 90:
            status = HealthStatus.CRITICAL
        elif percent > 80:
            status = HealthStatus.WARNING

        def to_gb(bytes_val: float) -> float:
            return round(bytes_val / (1024**3), 2)

        return InspectionReport(
            inspector=self.name,
            status=status,
            timestamp=time.time(),
            summary=f"RAM usage at {percent}% ({to_gb(mem.used)}GB / {to_gb(mem.total)}GB)",
            details={
                "total_gb": to_gb(mem.total),
                "used_gb": to_gb(mem.used),
                "available_gb": to_gb(mem.available),
                "swap_total_gb": to_gb(swap.total),
                "swap_used_gb": to_gb(swap.used),
            },
            metrics={
                "usage_percent": percent,
                "swap_percent": swap.percent
            }
        )
