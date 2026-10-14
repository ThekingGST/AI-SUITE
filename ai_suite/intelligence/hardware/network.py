import time
import socket
import psutil
from ..base import BaseInspector
from ..types import InspectionReport, HealthStatus

class NetworkInspector(BaseInspector):
    @property
    def name(self) -> str:
        return "network"

    def inspect(self) -> InspectionReport:
        # Check internet connectivity
        connected = False
        try:
            socket.create_connection(("1.1.1.1", 53), timeout=2)
            connected = True
        except OSError:
            pass

        # Gather interface stats
        interfaces = {}
        for name, stats in psutil.net_if_stats().items():
            if stats.isup:
                interfaces[name] = {"speed_mbps": stats.speed}
                
        status = HealthStatus.HEALTHY if connected else HealthStatus.CRITICAL

        return InspectionReport(
            inspector=self.name,
            status=status,
            timestamp=time.time(),
            summary="Internet connected" if connected else "Internet disconnected",
            details={
                "is_connected": connected,
                "active_interfaces": list(interfaces.keys())
            },
            metrics={}
        )
