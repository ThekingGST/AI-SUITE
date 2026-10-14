import time
import platform
import psutil
import datetime
from ..base import BaseInspector
from ..types import InspectionReport, HealthStatus

class WindowsInspector(BaseInspector):
    @property
    def name(self) -> str:
        return "windows"

    def inspect(self) -> InspectionReport:
        uname = platform.uname()
        uptime_seconds = time.time() - psutil.boot_time()
        uptime_str = str(datetime.timedelta(seconds=int(uptime_seconds)))
        
        return InspectionReport(
            inspector=self.name,
            status=HealthStatus.HEALTHY,
            timestamp=time.time(),
            summary=f"{uname.system} {uname.release} (Uptime: {uptime_str})",
            details={
                "system": uname.system,
                "release": uname.release,
                "version": uname.version,
                "machine": uname.machine,
                "hostname": uname.node,
                "uptime_seconds": uptime_seconds
            },
            metrics={"uptime_hours": uptime_seconds / 3600}
        )
