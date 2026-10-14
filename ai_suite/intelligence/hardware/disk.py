import time
import psutil
from ..base import BaseInspector
from ..types import InspectionReport, HealthStatus

class DiskInspector(BaseInspector):
    @property
    def name(self) -> str:
        return "disk"

    def inspect(self) -> InspectionReport:
        partitions = psutil.disk_partitions(all=False)
        details = {}
        max_percent = 0.0
        
        for p in partitions:
            try:
                usage = psutil.disk_usage(p.mountpoint)
                details[p.device] = {
                    "mountpoint": p.mountpoint,
                    "fstype": p.fstype,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "free_gb": round(usage.free / (1024**3), 2),
                    "percent": usage.percent
                }
                if usage.percent > max_percent:
                    max_percent = usage.percent
            except PermissionError:
                continue

        status = HealthStatus.HEALTHY
        if max_percent > 95:
            status = HealthStatus.CRITICAL
        elif max_percent > 85:
            status = HealthStatus.WARNING

        return InspectionReport(
            inspector=self.name,
            status=status,
            timestamp=time.time(),
            summary=f"Disk usage peaking at {max_percent}% across partitions",
            details=details,
            metrics={"max_usage_percent": max_percent}
        )
