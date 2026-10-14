import time
import psutil
from ..base import BaseInspector
from ..types import InspectionReport, HealthStatus

class BatteryInspector(BaseInspector):
    @property
    def name(self) -> str:
        return "battery"

    def inspect(self) -> InspectionReport:
        battery = psutil.sensors_battery()
        if not battery:
            return InspectionReport(
                inspector=self.name,
                status=HealthStatus.UNKNOWN,
                timestamp=time.time(),
                summary="No battery detected (likely a desktop PC)."
            )

        percent = battery.percent
        plugged = battery.power_plugged
        
        status = HealthStatus.HEALTHY
        if not plugged:
            if percent < 10:
                status = HealthStatus.CRITICAL
            elif percent < 20:
                status = HealthStatus.WARNING

        plug_str = "plugged in" if plugged else "on battery"
        
        return InspectionReport(
            inspector=self.name,
            status=status,
            timestamp=time.time(),
            summary=f"Battery at {percent}%, {plug_str}",
            details={
                "is_plugged": plugged,
                "time_left_secs": battery.secsleft if not plugged else -1,
            },
            metrics={
                "percent": float(percent)
            }
        )
