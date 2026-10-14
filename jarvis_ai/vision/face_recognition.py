from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

from core.model_manager import ModelManager
from config import CONFIG, MODELS_DIR, OWNER_EMBEDDINGS
from utils.helpers import timestamp_slug
from utils.logger import LOGGER
from vision.face_detection import FaceBox


class FaceRecognizer:
    """SFace ONNX owner recognition through ONNX Runtime and cosine similarity."""

    def __init__(self) -> None:
        self.session = None
        self.input_name = ""
        self.owner_embeddings: list[list[float]] = []
        self.session, self.input_name = ModelManager().get_sface_session()
        self._load_owner()

    def _load_owner(self) -> None:
        if OWNER_EMBEDDINGS.exists():
            try:
                self.owner_embeddings = json.loads(OWNER_EMBEDDINGS.read_text(encoding="utf-8"))
            except Exception as exc:
                LOGGER.warning("Owner embeddings failed to load: %s", exc)

    def register_owner(self, frame: np.ndarray, face: FaceBox) -> str:
        embedding = self.embedding(frame, face)
        if embedding is None:
            return "Owner registration failed. Face recognition model is unavailable."
        self.owner_embeddings.append(embedding.tolist())
        OWNER_EMBEDDINGS.write_text(json.dumps(self.owner_embeddings), encoding="utf-8")
        return "Owner face registered."

    def recognize(self, frame: np.ndarray, face: FaceBox) -> tuple[str, float]:
        embedding = self.embedding(frame, face)
        if embedding is None or not self.owner_embeddings:
            return ("unknown", 0.0)
        owner = np.array(self.owner_embeddings, dtype=np.float32)
        scores = [self._cosine(embedding, item) for item in owner]
        best = float(max(scores, default=0.0))
        return ("owner", best) if best >= CONFIG.vision.face_match_threshold else ("unknown", best)

    def embedding(self, frame: np.ndarray, face: FaceBox) -> np.ndarray | None:
        if self.session is None:
            return None
        crop = frame[face.y : face.y + face.h, face.x : face.x + face.w]
        if crop.size == 0:
            return None
        image = cv2.resize(crop, (112, 112))
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB).astype(np.float32)
        image = (image - 127.5) / 128.0
        tensor = np.transpose(image, (2, 0, 1))[None, :, :, :]
        output = self.session.run(None, {self.input_name: tensor})[0]
        embedding = output.reshape(-1).astype(np.float32)
        norm = np.linalg.norm(embedding)
        return embedding / norm if norm else embedding

    @staticmethod
    def _cosine(a: np.ndarray, b: np.ndarray) -> float:
        denom = float(np.linalg.norm(a) * np.linalg.norm(b))
        return float(np.dot(a, b) / denom) if denom else 0.0

    @staticmethod
    def save_intruder(frame: np.ndarray) -> Path:
        from config import INTRUDER_DIR

        path = INTRUDER_DIR / f"intruder_{timestamp_slug()}.jpg"
        cv2.imwrite(str(path), frame)
        return path
