from __future__ import annotations

import threading
from typing import Any

import cv2

from config import MODELS_DIR
from utils.logger import LOGGER


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
                LOGGER.info("Face detector loaded.")
                return net
            except Exception as exc:
                LOGGER.warning("Face detector load failed: %s", exc)
                self._cache["face_detector"] = None
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

                session = ort.InferenceSession(str(model), providers=["CPUExecutionProvider"])
                input_name = session.get_inputs()[0].name
                self._cache["sface"] = (session, input_name)
                LOGGER.info("SFace recognizer loaded.")
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

                model = YOLO(str(model_path))
                self._cache["yolo"] = model
                LOGGER.info("YOLOv8 object detector loaded.")
                return model
            except Exception as exc:
                LOGGER.warning("YOLO load failed: %s", exc)
                self._cache["yolo"] = None
                return None
