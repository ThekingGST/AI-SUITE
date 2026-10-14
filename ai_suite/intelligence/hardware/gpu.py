import time
import subprocess
from typing import Any
from ..base import BaseInspector
from ..types import InspectionReport, HealthStatus

class GPUInspector(BaseInspector):
    @property
    def name(self) -> str:
        return "gpu"

    def inspect(self) -> InspectionReport:
        try:
            import pynvml
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            name = pynvml.nvmlDeviceGetName(handle)
            if isinstance(name, bytes):
                name = name.decode('utf-8')
            meminfo = pynvml.nvmlDeviceGetMemoryInfo(handle)
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            
            total_mb = meminfo.total / 1024**2
            used_mb = meminfo.used / 1024**2
            vram_percent = (used_mb / total_mb) * 100 if total_mb > 0 else 0
            gpu_percent = util.gpu
            
            status = HealthStatus.HEALTHY
            if temp > 85 or vram_percent > 95:
                status = HealthStatus.CRITICAL
            elif temp > 80 or vram_percent > 90:
                status = HealthStatus.WARNING

            return InspectionReport(
                inspector=self.name,
                status=status,
                timestamp=time.time(),
                summary=f"GPU usage at {gpu_percent}%, VRAM {vram_percent:.1f}%, Temp {temp}C",
                details={
                    "name": name,
                    "driver_version": pynvml.nvmlSystemGetDriverVersion(),
                },
                metrics={
                    "usage_percent": float(gpu_percent),
                    "vram_percent": float(vram_percent),
                    "temperature_c": float(temp)
                }
            )
        except Exception:
            # Fallback
            return InspectionReport(
                inspector=self.name,
                status=HealthStatus.UNKNOWN,
                timestamp=time.time(),
                summary="GPU inspection unavailable or no NVIDIA GPU found.",
            )
