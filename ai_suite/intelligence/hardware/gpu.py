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
            from shared.hardware.manager import HardwareManager
            import time
            hw = HardwareManager()
            if not getattr(hw, "_initialized", False):
                hw.detect_all()
            
            if not hw.gpu.available:
                return InspectionReport(
                    inspector=self.name,
                    status=HealthStatus.UNKNOWN,
                    timestamp=time.time(),
                    summary="GPU inspection unavailable or no NVIDIA GPU found.",
                )

            # Query fresh VRAM usage
            vram = hw.get_vram_usage()
            vram_percent = vram.get("percent", 0.0)
            
            status = HealthStatus.HEALTHY
            if hw.gpu.temperature_c > 85 or vram_percent > 95:
                status = HealthStatus.CRITICAL
            elif hw.gpu.temperature_c > 80 or vram_percent > 90:
                status = HealthStatus.WARNING

            return InspectionReport(
                inspector=self.name,
                status=status,
                timestamp=time.time(),
                summary=f"GPU usage at {hw.gpu.utilization_percent:.1f}%, VRAM {vram_percent:.1f}%, Temp {hw.gpu.temperature_c}C",
                details={
                    "name": hw.gpu.name,
                    "driver_version": hw.gpu.driver_version,
                },
                metrics={
                    "usage_percent": float(hw.gpu.utilization_percent),
                    "vram_percent": float(vram_percent),
                    "temperature_c": float(hw.gpu.temperature_c)
                }
            )
        except Exception:
            import time
            # Fallback
            return InspectionReport(
                inspector=self.name,
                status=HealthStatus.UNKNOWN,
                timestamp=time.time(),
                summary="GPU inspection unavailable or no NVIDIA GPU found.",
            )
