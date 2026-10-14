import time
import psutil
from ..base import BaseInspector
from ..types import InspectionReport, HealthStatus

class ProcessInspector(BaseInspector):
    @property
    def name(self) -> str:
        return "process"

    def inspect(self) -> InspectionReport:
        procs = []
        for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                # Need to read cpu_percent once with interval to get real usage, 
                # but for speed we just take what's cached or ignore
                mem = p.info['memory_percent'] or 0.0
                procs.append({
                    "pid": p.info['pid'],
                    "name": p.info['name'],
                    "mem": mem
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
                
        # Sort by memory usage
        procs.sort(key=lambda x: x['mem'], reverse=True)
        top_procs = procs[:5]
        
        return InspectionReport(
            inspector=self.name,
            status=HealthStatus.HEALTHY,
            timestamp=time.time(),
            summary=f"{len(procs)} processes running",
            details={
                "total_processes": len(procs),
                "top_memory_processes": top_procs
            },
            metrics={"process_count": float(len(procs))}
        )
