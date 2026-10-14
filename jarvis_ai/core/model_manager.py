"""Thread-safe singleton model cache for AI Suite V2.

All expensive vision/AI models load only once and are shared
across the application. Uses HardwareManager for device selection
instead of inline CUDA detection.
"""

from __future__ import annotations

import threading
from typing import Any

import cv2

from jarvis_ai.config import MODELS_DIR
from jarvis_ai.utils.logger import LOGGER


class ModelManager:
    """Singleton-style model cache so expensive vision models load only once."""

    _instance: "ModelManager | None" = None
    _instance_lock = threading.Lock()

    def __new__(cls) -> "ModelManager":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init_once()
            return cls._instance

    def _init_once(self) -> None:
        self._lock = threading.RLock()
        self._cache: dict[str, Any] = {}

    def _get_hardware_manager(self):
        """Lazy import to avoid circular dependency at module level."""
        try:
            from shared.hardware.manager import HardwareManager
            return HardwareManager()
        except Exception:
            return None

    def release_all(self) -> None:
        """Release all heavy AI models from memory, including GPU VRAM."""
        with self._lock:
            self._cache.clear()
            # Free GPU memory if PyTorch CUDA was used
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    LOGGER.info("GPU VRAM cache cleared.")
            except Exception:
                pass
            LOGGER.info("All heavy AI models released from memory.")

    def get_face_detector(self) -> Any | None:
        with self._lock:
            if "face_detector" in self._cache:
                return self._cache["face_detector"]
            prototxt = MODELS_DIR / "deploy.prototxt"
            caffemodel = MODELS_DIR / "res10_300x300_ssd_iter_140000.caffemodel"
            if not prototxt.exists() or not caffemodel.exists():
                LOGGER.warning("Face detector models missing in %s", MODELS_DIR)
                self._cache["face_detector"] = None
                return None
            try:
                net = cv2.dnn.readNetFromCaffe(str(prototxt), str(caffemodel))
                self._cache["face_detector"] = net
                LOGGER.info("Face detector loaded (CPU — OpenCV DNN).")
                return net
            except Exception as exc:
                LOGGER.warning("Face detector load failed: %s", exc)
                self._cache["face_detector"] = None
                return None

    def get_yunet_detector(self) -> Any | None:
        with self._lock:
            if "yunet" in self._cache:
                return self._cache["yunet"]
            model = MODELS_DIR / "face_detection_yunet_2023mar.onnx"
            if not model.exists():
                LOGGER.warning("YuNet ONNX model missing in %s", MODELS_DIR)
                self._cache["yunet"] = None
                return None
            try:
                detector = cv2.FaceDetectorYN.create(
                    model=str(model),
                    config="",
                    input_size=(320, 320),
                    score_threshold=0.6,
                    nms_threshold=0.3,
                    top_k=5000,
                )
                self._cache["yunet"] = detector
                LOGGER.info("YuNet Face detector loaded (CPU — OpenCV DNN).")
                return detector
            except Exception as exc:
                LOGGER.warning("YuNet load failed: %s", exc)
                self._cache["yunet"] = None
                return None

    def get_sface_session(self) -> tuple[Any | None, str]:
        with self._lock:
            if "sface" in self._cache:
                return self._cache["sface"]
            model = MODELS_DIR / "face_recognition_sface_2021dec.onnx"
            if not model.exists():
                LOGGER.warning("SFace ONNX model missing: %s", model)
                self._cache["sface"] = (None, "")
                return self._cache["sface"]
            try:
                import onnxruntime as ort

                # Use HardwareManager for provider selection
                hw = self._get_hardware_manager()
                if hw is not None:
                    providers = hw.get_onnx_providers()
                else:
                    # Fallback: inline detection (backward compatible)
                    available = ort.get_available_providers()
                    providers = []
                    if "CUDAExecutionProvider" in available:
                        providers.append("CUDAExecutionProvider")
                    providers.append("CPUExecutionProvider")

                session = ort.InferenceSession(str(model), providers=providers)
                input_name = session.get_inputs()[0].name
                self._cache["sface"] = (session, input_name)

                active_providers = session.get_providers()
                LOGGER.info("SFace recognizer loaded. Active providers: %s", active_providers)
                return self._cache["sface"]
            except Exception as exc:
                LOGGER.warning("SFace model failed to load: %s", exc)
                self._cache["sface"] = (None, "")
                return self._cache["sface"]

    def get_yolo(self) -> Any | None:
        with self._lock:
            if "yolo" in self._cache:
                return self._cache["yolo"]
            model_path = MODELS_DIR / "yolov8n.pt"
            if not model_path.exists():
                LOGGER.warning("YOLO model missing: %s", model_path)
                self._cache["yolo"] = None
                return None
            try:
                from ultralytics import YOLO

                # Use HardwareManager for device selection
                hw = self._get_hardware_manager()
                if hw is not None:
                    device = hw.get_torch_device()
                    LOGGER.info(
                        "GPU Check -> CUDA Available: %s, GPU: %s, CUDA Version: %s, Verified: %s",
                        hw.cuda.pytorch_available,
                        hw.cuda.device_name,
                        hw.cuda.cuda_version,
                        hw.gpu_verified,
                    )
                else:
                    # Fallback: inline detection (backward compatible)
                    import torch
                    cuda_avail = torch.cuda.is_available()
                    device = "cuda:0" if cuda_avail else "cpu"
                    gpu_name = torch.cuda.get_device_name(0) if cuda_avail else "None"
                    LOGGER.info("GPU Check (fallback) -> CUDA: %s, GPU: %s", cuda_avail, gpu_name)

                model = YOLO(str(model_path))
                model.to(device)
                self._cache["yolo"] = model
                LOGGER.info("YOLOv8 object detector loaded. Device: %s", model.device)
                return model
            except Exception as exc:
                LOGGER.error("YOLO load failed: %s", exc)
                self._cache["yolo"] = None
                raise RuntimeError(f"YOLO load failed: {exc}") from exc
