"""Central hardware detection and AI acceleration manager for AI Suite V2.

Provides a single source of truth for GPU capabilities, CUDA availability,
ONNX execution provider selection, VRAM tracking, and Ollama GPU status.
All AI components should query this manager instead of performing inline
hardware detection.

Thread-safe after initialization. Results are cached since hardware
does not change at runtime.
"""

from __future__ import annotations

import json
import logging
import platform
import threading
import urllib.request
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("ai_suite.hardware")


@dataclass(frozen=True)
class GPUInfo:
    """Immutable snapshot of detected GPU hardware."""
    available: bool = False
    name: str = "N/A"
    vendor: str = "unknown"
    vram_total_mb: float = 0.0
    vram_used_mb: float = 0.0
    vram_free_mb: float = 0.0
    driver_version: str = "N/A"
    temperature_c: float = 0.0
    utilization_percent: float = 0.0


@dataclass(frozen=True)
class CUDAInfo:
    """Immutable snapshot of CUDA/PyTorch capabilities."""
    pytorch_available: bool = False
    pytorch_version: str = "N/A"
    cuda_version: str = "N/A"
    device_count: int = 0
    device_name: str = "N/A"


@dataclass(frozen=True)
class ONNXInfo:
    """Immutable snapshot of ONNX Runtime capabilities."""
    version: str = "N/A"
    available_providers: tuple[str, ...] = ()
    cuda_functional: bool = False


@dataclass(frozen=True)
class OllamaGPUInfo:
    """Immutable snapshot of Ollama GPU usage."""
    running: bool = False
    models: tuple[str, ...] = ()
    gpu_active: bool = False
    details: str = "unknown"


@dataclass(frozen=True)
class SystemInfo:
    """Immutable snapshot of CPU and RAM."""
    cpu_model: str = "unknown"
    cpu_cores_physical: int = 0
    cpu_cores_logical: int = 0
    ram_total_gb: float = 0.0
    ram_available_gb: float = 0.0


@dataclass(frozen=True)
class AccelerationProfile:
    """Summary of recommended acceleration settings."""
    torch_device: str = "cpu"
    onnx_providers: tuple[str, ...] = ("CPUExecutionProvider",)
    gpu_acceleration: bool = False
    reason: str = "No GPU detected"


class HardwareManager:
    """Singleton hardware detection and acceleration manager.

    Usage::

        hw = HardwareManager()
        hw.detect_all()  # Run once during boot

        device = hw.get_torch_device()       # "cuda:0" or "cpu"
        providers = hw.get_onnx_providers()   # ["CUDAExecutionProvider", "CPUExecutionProvider"] or ["CPUExecutionProvider"]
        summary = hw.get_acceleration_summary()
    """

    _instance: HardwareManager | None = None
    _instance_lock = threading.Lock()

    def __new__(cls) -> HardwareManager:
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def _init_once(self) -> None:
        if self._initialized:
            return
        self._lock = threading.RLock()
        self._gpu_info = GPUInfo()
        self._cuda_info = CUDAInfo()
        self._onnx_info = ONNXInfo()
        self._ollama_info = OllamaGPUInfo()
        self._system_info = SystemInfo()
        self._profile = AccelerationProfile()
        self._gpu_verified = False
        self._initialized = True

    def detect_all(self) -> None:
        """Run full hardware detection. Call once during application boot."""
        self._init_once()
        with self._lock:
            self._detect_system()
            self._detect_gpu_nvml()
            self._detect_pytorch_cuda()
            self._detect_onnx_providers()
            self._verify_gpu()
            self._build_acceleration_profile()
            self._log_summary()

    # ── Public API ──────────────────────────────────────────────────────

    @property
    def gpu(self) -> GPUInfo:
        return self._gpu_info

    @property
    def cuda(self) -> CUDAInfo:
        return self._cuda_info

    @property
    def onnx(self) -> ONNXInfo:
        return self._onnx_info

    @property
    def system(self) -> SystemInfo:
        return self._system_info

    @property
    def profile(self) -> AccelerationProfile:
        return self._profile

    @property
    def gpu_verified(self) -> bool:
        """True if GPU acceleration was actually tested and confirmed working."""
        return self._gpu_verified

    def get_torch_device(self) -> str:
        """Get the recommended PyTorch device string ('cuda:0' or 'cpu')."""
        return self._profile.torch_device

    def get_onnx_providers(self) -> list[str]:
        """Get ordered list of ONNX execution providers to use."""
        return list(self._profile.onnx_providers)

    def get_acceleration_summary(self) -> str:
        """Get a human-readable summary of the acceleration configuration."""
        if self._profile.gpu_acceleration:
            return (
                f"GPU: {self._gpu_info.name} | "
                f"VRAM: {self._gpu_info.vram_total_mb:.0f} MB | "
                f"CUDA: {self._cuda_info.cuda_version} | "
                f"Torch: {self._profile.torch_device} | "
                f"ONNX CUDA: {'Yes' if self._onnx_info.cuda_functional else 'No'}"
            )
        return f"CPU mode — {self._profile.reason}"

    def get_vram_usage(self) -> dict[str, float]:
        """Query current VRAM usage. Returns fresh data from NVML."""
        try:
            import pynvml
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            meminfo = pynvml.nvmlDeviceGetMemoryInfo(handle)
            pynvml.nvmlShutdown()
            return {
                "total_mb": round(meminfo.total / 1024**2, 2),
                "used_mb": round(meminfo.used / 1024**2, 2),
                "free_mb": round(meminfo.free / 1024**2, 2),
                "percent": round(meminfo.used / meminfo.total * 100, 1) if meminfo.total > 0 else 0.0,
            }
        except Exception:
            return {"total_mb": 0, "used_mb": 0, "free_mb": 0, "percent": 0}

    def can_fit_vram(self, estimated_mb: float) -> bool:
        """Check if estimated_mb of VRAM can fit in available GPU memory."""
        usage = self.get_vram_usage()
        return usage["free_mb"] > estimated_mb

    def detect_ollama_gpu(self) -> OllamaGPUInfo:
        """Check if Ollama is using GPU acceleration. Can be called on demand."""
        self._detect_ollama()
        return self._ollama_info

    def release_gpu_memory(self) -> None:
        """Release cached GPU memory from PyTorch."""
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
                logger.info("GPU memory cache cleared.")
        except Exception as e:
            logger.debug("GPU memory release skipped: %s", e)

    # ── Detection Methods ───────────────────────────────────────────────

    def _detect_system(self) -> None:
        """Detect CPU and RAM information."""
        try:
            import psutil
            cpu_model = platform.processor() or "unknown"
            cores_physical = psutil.cpu_count(logical=False) or 0
            cores_logical = psutil.cpu_count(logical=True) or 0
            mem = psutil.virtual_memory()
            self._system_info = SystemInfo(
                cpu_model=cpu_model,
                cpu_cores_physical=cores_physical,
                cpu_cores_logical=cores_logical,
                ram_total_gb=round(mem.total / 1024**3, 2),
                ram_available_gb=round(mem.available / 1024**3, 2),
            )
        except Exception as e:
            logger.warning("System detection failed: %s", e)

    def _detect_gpu_nvml(self) -> None:
        """Detect NVIDIA GPU hardware via NVML."""
        try:
            import pynvml
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            name = pynvml.nvmlDeviceGetName(handle)
            if isinstance(name, bytes):
                name = name.decode("utf-8")
            meminfo = pynvml.nvmlDeviceGetMemoryInfo(handle)
            try:
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                gpu_util = float(util.gpu)
            except Exception:
                gpu_util = 0.0
            try:
                temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            except Exception:
                temp = 0.0
            try:
                driver = pynvml.nvmlSystemGetDriverVersion()
            except Exception:
                driver = "unknown"

            vendor = "NVIDIA" if "nvidia" in name.lower() or "geforce" in name.lower() or "rtx" in name.lower() or "gtx" in name.lower() else "unknown"

            self._gpu_info = GPUInfo(
                available=True,
                name=name,
                vendor=vendor,
                vram_total_mb=round(meminfo.total / 1024**2, 2),
                vram_used_mb=round(meminfo.used / 1024**2, 2),
                vram_free_mb=round(meminfo.free / 1024**2, 2),
                driver_version=driver,
                temperature_c=float(temp),
                utilization_percent=gpu_util,
            )
            pynvml.nvmlShutdown()
        except Exception as e:
            logger.info("NVML GPU detection unavailable: %s", e)
            self._gpu_info = GPUInfo()

    def _detect_pytorch_cuda(self) -> None:
        """Detect PyTorch CUDA availability."""
        try:
            import torch
            cuda_avail = torch.cuda.is_available()
            self._cuda_info = CUDAInfo(
                pytorch_available=cuda_avail,
                pytorch_version=torch.__version__,
                cuda_version=torch.version.cuda or "N/A" if cuda_avail else "N/A",
                device_count=torch.cuda.device_count() if cuda_avail else 0,
                device_name=torch.cuda.get_device_name(0) if cuda_avail else "N/A",
            )
        except Exception as e:
            logger.warning("PyTorch CUDA detection failed: %s", e)
            self._cuda_info = CUDAInfo()

    def _detect_onnx_providers(self) -> None:
        """Detect ONNX Runtime execution providers."""
        try:
            import onnxruntime as ort
            available = ort.get_available_providers()
            # Test if CUDA provider actually works by attempting a tiny session
            cuda_functional = False
            if "CUDAExecutionProvider" in available:
                cuda_functional = self._test_onnx_cuda()

            self._onnx_info = ONNXInfo(
                version=ort.__version__,
                available_providers=tuple(available),
                cuda_functional=cuda_functional,
            )
        except Exception as e:
            logger.warning("ONNX Runtime detection failed: %s", e)
            self._onnx_info = ONNXInfo()

    def _test_onnx_cuda(self) -> bool:
        """Actually test if ONNX CUDA provider can initialize.

        Returns True only if the provider genuinely works,
        not just if it's listed as available.
        """
        try:
            import ctypes
            import onnxruntime as ort
            import os
            
            # Find the ONNX runtime installation path
            ort_path = os.path.dirname(ort.__file__)
            dll_path = os.path.join(ort_path, "capi", "onnxruntime_providers_cuda.dll")
            
            if not os.path.exists(dll_path):
                return False
                
            # Attempt to load the DLL. This will fail if CUDA dependencies are missing.
            ctypes.CDLL(dll_path)
            logger.info("ONNX CUDA provider verified working (DLL loaded successfully).")
            return True
        except Exception as e:
            logger.info("ONNX CUDA provider test failed (CUDA dependencies missing?): %s", e)
            return False

    def _verify_gpu(self) -> None:
        """Perform actual GPU computation to verify acceleration works."""
        if not self._cuda_info.pytorch_available:
            self._gpu_verified = False
            return

        try:
            import torch
            # Allocate a small tensor on GPU and perform computation
            device = torch.device("cuda:0")
            a = torch.randn(64, 64, device=device)
            b = torch.randn(64, 64, device=device)
            c = torch.mm(a, b)
            torch.cuda.synchronize()
            # Verify result is valid
            assert c.shape == (64, 64)
            assert not torch.isnan(c).any()
            del a, b, c
            torch.cuda.empty_cache()
            self._gpu_verified = True
            logger.info("PyTorch GPU verification PASSED — actual tensor computation confirmed on %s.", self._cuda_info.device_name)
        except Exception as e:
            logger.warning("PyTorch GPU verification FAILED: %s — falling back to CPU.", e)
            self._gpu_verified = False

    def _detect_ollama(self) -> None:
        """Check Ollama status and GPU acceleration."""
        try:
            req = urllib.request.Request("http://localhost:11434/api/tags")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read())
                models = tuple(m["name"] for m in data.get("models", []))

            # Check running model GPU usage
            gpu_active = False
            details = "no models loaded"
            try:
                req2 = urllib.request.Request("http://localhost:11434/api/ps")
                with urllib.request.urlopen(req2, timeout=3) as resp2:
                    ps_data = json.loads(resp2.read())
                    running = ps_data.get("models", [])
                    if running:
                        for m in running:
                            vram = m.get("size_vram", 0)
                            if vram > 0:
                                gpu_active = True
                                details = f"GPU active ({vram / 1024**3:.1f} GB VRAM)"
                                break
                        if not gpu_active:
                            details = "CPU only"
            except Exception:
                pass

            self._ollama_info = OllamaGPUInfo(
                running=True,
                models=models,
                gpu_active=gpu_active,
                details=details,
            )
        except Exception:
            self._ollama_info = OllamaGPUInfo()

    def _build_acceleration_profile(self) -> None:
        """Build the final acceleration profile based on all detections."""
        torch_device = "cpu"
        onnx_providers = ["CPUExecutionProvider"]
        gpu_acceleration = False
        reason = "No GPU detected"

        if self._gpu_verified and self._cuda_info.pytorch_available:
            torch_device = "cuda:0"
            gpu_acceleration = True
            reason = f"GPU verified: {self._gpu_info.name}"

        if self._onnx_info.cuda_functional:
            onnx_providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        else:
            if "CUDAExecutionProvider" in self._onnx_info.available_providers:
                reason += " | ONNX CUDA listed but non-functional (missing CUDA runtime DLLs)"

        self._profile = AccelerationProfile(
            torch_device=torch_device,
            onnx_providers=tuple(onnx_providers),
            gpu_acceleration=gpu_acceleration,
            reason=reason,
        )

    def _log_summary(self) -> None:
        """Log the complete hardware detection summary."""
        logger.info("=" * 60)
        logger.info("HARDWARE DETECTION SUMMARY")
        logger.info("=" * 60)
        logger.info("CPU: %s (%d physical / %d logical cores)",
                     self._system_info.cpu_model,
                     self._system_info.cpu_cores_physical,
                     self._system_info.cpu_cores_logical)
        logger.info("RAM: %.1f GB total, %.1f GB available",
                     self._system_info.ram_total_gb,
                     self._system_info.ram_available_gb)

        if self._gpu_info.available:
            logger.info("GPU: %s (VRAM: %.0f MB total, %.0f MB free)",
                         self._gpu_info.name,
                         self._gpu_info.vram_total_mb,
                         self._gpu_info.vram_free_mb)
            logger.info("Driver: %s", self._gpu_info.driver_version)
        else:
            logger.info("GPU: Not detected via NVML")

        logger.info("PyTorch: %s | CUDA: %s | Device: %s",
                     self._cuda_info.pytorch_version,
                     self._cuda_info.cuda_version,
                     self._cuda_info.device_name)
        logger.info("ONNX Runtime: %s | Providers: %s | CUDA functional: %s",
                     self._onnx_info.version,
                     ", ".join(self._onnx_info.available_providers),
                     self._onnx_info.cuda_functional)
        logger.info("GPU Verified: %s", self._gpu_verified)
        logger.info("Acceleration: %s", self.get_acceleration_summary())
        logger.info("=" * 60)
