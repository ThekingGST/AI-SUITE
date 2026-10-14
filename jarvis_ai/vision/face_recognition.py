from __future__ import annotations

import json
import pickle
from pathlib import Path

import cv2
import numpy as np

from jarvis_ai.core.model_manager import ModelManager
from jarvis_ai.config import CONFIG, FACE_EMBEDDINGS_DB, FACE_DATASET_DIR, OWNER_EMBEDDINGS
from jarvis_ai.utils.helpers import timestamp_slug
from jarvis_ai.utils.logger import LOGGER
from jarvis_ai.vision.face_detection import FaceBox


class FaceRecognizer:
    """SFace ONNX face recognition with adaptive per-identity thresholds."""

    def __init__(self) -> None:
        self.session = None
        self.input_name = ""
        self.owner_embeddings: list[list[float]] = []
        self.named_embeddings: dict[str, list[list[float]]] = {}
        # Per-identity adaptive thresholds, computed from cluster compactness.
        self._adaptive_thresholds: dict[str, float] = {}
        self.session, self.input_name = ModelManager().get_sface_session()
        self._load_owner()
        self._load_named_embeddings()

    # ── loading ──────────────────────────────────────────────────────

    def _load_owner(self) -> None:
        if OWNER_EMBEDDINGS.exists():
            try:
                self.owner_embeddings = json.loads(OWNER_EMBEDDINGS.read_text(encoding="utf-8"))
            except Exception as exc:
                LOGGER.warning("Owner embeddings failed to load: %s", exc)

    def _load_named_embeddings(self) -> None:
        if FACE_EMBEDDINGS_DB.exists():
            try:
                with FACE_EMBEDDINGS_DB.open("rb") as handle:
                    self.named_embeddings = pickle.load(handle)
                LOGGER.info(
                    "Loaded face embeddings for: %s",
                    ", ".join(self.named_embeddings) or "none",
                )
                self._compute_adaptive_thresholds()
            except Exception as exc:
                LOGGER.warning("Named face embeddings failed to load: %s", exc)
                self.named_embeddings = {}

    def _compute_adaptive_thresholds(self) -> None:
        """Compute a per-identity recognition threshold from cluster statistics.

        Mathematical reasoning
        ----------------------
        For each identity we have N registered embeddings.  We compute:

        - **compactness**: mean pairwise cosine similarity within the cluster.
        - **min_pair**: the lowest pairwise cosine in the cluster — i.e. the
          most dissimilar pair of genuine images.
        - **spread**: ``compactness - min_pair``, measuring how much natural
          variation exists within the registration set.

        A new genuine observation should score at least as well as the worst
        registered pair, minus a margin that accounts for new-observation
        variation (different lighting, slight pose change, etc.).

        Formula::

            raw = min_pair - spread * 2.0
            adaptive = clamp(raw, floor, ceiling)

        Where:
        - ``floor``   = ``face_match_threshold`` (global minimum, default 0.70)
        - ``ceiling`` = ``face_match_ceiling`` (configurable max, default 0.85)

        Why this works:
        - For **compact clusters** (single-session registration), min_pair ≈
          compactness ≈ 0.99 and spread ≈ 0.005, so raw ≈ 0.98.  The ceiling
          clamp pulls this down to 0.85, preventing over-tightening.
        - For **diverse clusters** (multi-session, varied lighting), min_pair
          is naturally lower and spread is larger, producing a lower raw value
          that falls between floor and ceiling without clamping.
        - The floor ensures we never accept wildly dissimilar faces.
        """
        floor = CONFIG.vision.face_match_threshold
        ceiling = CONFIG.vision.face_match_ceiling
        dirty = False

        for name, vectors in list(self.named_embeddings.items()):
            if len(vectors) < 3:
                self._adaptive_thresholds[name] = floor
                continue

            arr = np.array(vectors, dtype=np.float32)

            # Iterative pruning: remove embeddings whose average similarity
            # to peers is anomalously low (contamination guard).
            pruned = True
            while pruned and len(arr) >= 3:
                pruned = False
                n = len(arr)
                pairs: list[float] = []
                for i in range(n):
                    for j in range(i + 1, n):
                        pairs.append(self._cosine(arr[i], arr[j]))
                compactness = float(np.mean(pairs))
                prune_thr = compactness * 0.90
                avg_sims = []
                for i in range(n):
                    sims = [self._cosine(arr[i], arr[j])
                            for j in range(n) if j != i]
                    avg_sims.append(float(np.mean(sims)))
                keep = [i for i, s in enumerate(avg_sims) if s >= prune_thr]
                if len(keep) < n and len(keep) >= 2:
                    removed = [i for i in range(n) if i not in keep]
                    LOGGER.warning(
                        "ADAPTIVE PRUNE: removed %d weak embedding(s) for "
                        "'%s' (compactness=%.4f prune_thr=%.4f removed=%s)",
                        len(removed), name, compactness, prune_thr, removed,
                    )
                    arr = arr[keep]
                    pruned = True
                    dirty = True

            # Save pruned embeddings back
            if dirty:
                self.named_embeddings[name] = [row.tolist() for row in arr]

            # Final cluster statistics after pruning
            n = len(arr)
            pairs = []
            for i in range(n):
                for j in range(i + 1, n):
                    pairs.append(self._cosine(arr[i], arr[j]))
            compactness = float(np.mean(pairs))
            min_pair = float(min(pairs))
            spread = compactness - min_pair

            # Adaptive threshold: statistical lower bound with clamp
            raw = min_pair - spread * 2.0
            adaptive = max(floor, min(ceiling, raw))
            self._adaptive_thresholds[name] = adaptive

            LOGGER.info(
                "ADAPTIVE THRESHOLD for '%s': embeddings=%d compactness=%.4f "
                "min_pair=%.4f spread=%.4f raw=%.4f => clamped=%.4f "
                "(floor=%.4f ceiling=%.4f)",
                name, n, compactness, min_pair, spread, raw,
                adaptive, floor, ceiling,
            )

        if dirty:
            self._save_named_embeddings()

    # ── persistence ──────────────────────────────────────────────────

    def _save_named_embeddings(self) -> None:
        FACE_EMBEDDINGS_DB.parent.mkdir(parents=True, exist_ok=True)
        with FACE_EMBEDDINGS_DB.open("wb") as handle:
            pickle.dump(self.named_embeddings, handle)

    # ── registration ─────────────────────────────────────────────────

    def register_owner(self, frame: np.ndarray, face: FaceBox) -> str:
        embedding = self.embedding(frame, face)
        if embedding is None:
            return "Owner registration failed. Face recognition model is unavailable."
        self.owner_embeddings.append(embedding.tolist())
        OWNER_EMBEDDINGS.write_text(json.dumps(self.owner_embeddings), encoding="utf-8")
        return "Owner face registered."

    def register_person(self, name: str, samples: list[tuple[np.ndarray, FaceBox]]) -> int:
        clean_name = name.strip().title()
        if not clean_name:
            raise ValueError("REGISTRATION FAILED: name is empty")
        if self.session is None:
            raise RuntimeError("REGISTRATION FAILED: SFace ONNX model or onnxruntime is unavailable")
        if not samples:
            raise ValueError("REGISTRATION FAILED: no face samples captured")
        person_dir = FACE_DATASET_DIR / clean_name
        person_dir.mkdir(parents=True, exist_ok=True)
        LOGGER.info("FACE DATASET FOLDER: %s", person_dir)
        embeddings = self.named_embeddings.setdefault(clean_name, [])
        saved = 0
        LOGGER.info("GENERATING EMBEDDINGS")
        for frame, face in samples:
            emb = self.embedding(frame, face)
            if emb is None:
                LOGGER.warning("REGISTRATION FAILED: embedding generation returned None for a captured sample")
                continue
            saved += 1
            embeddings.append(emb.tolist())
            cv2.imwrite(str(person_dir / f"img{len(embeddings):03d}.jpg"), frame)
            LOGGER.info("EMBEDDING GENERATED %s/%s", saved, len(samples))
        if saved:
            self._save_named_embeddings()
            self._compute_adaptive_thresholds()
            LOGGER.info("EMBEDDINGS SAVED: %s", FACE_EMBEDDINGS_DB)
            LOGGER.info("Registered %s face samples for %s.", saved, clean_name)
            LOGGER.info("REGISTRATION COMPLETE")
        else:
            raise RuntimeError("REGISTRATION FAILED: no embeddings were generated")
        return saved

    # ── recognition ──────────────────────────────────────────────────

    def recognize(self, frame: np.ndarray, face: FaceBox) -> tuple[str, float]:
        emb = self.embedding(frame, face)
        if emb is None:
            return ("unknown", 0.0)
        named_match = self._match_named(emb)
        if named_match:
            return named_match
        if not self.owner_embeddings:
            return ("unknown", 0.0)
        owner = np.array(self.owner_embeddings, dtype=np.float32)
        scores = [self._cosine(emb, item) for item in owner]
        best = float(max(scores, default=0.0))
        return ("owner", best) if best >= CONFIG.vision.face_match_threshold else ("unknown", best)

    def _match_named(self, embedding: np.ndarray) -> tuple[str, float] | None:
        global_thr = CONFIG.vision.face_match_threshold
        ranked: list[tuple[str, float, float, int, int]] = []

        for name, vectors in self.named_embeddings.items():
            if not vectors:
                continue
            matrix = np.array(vectors, dtype=np.float32)
            sample_scores = [self._cosine(embedding, row) for row in matrix]
            sample_scores.sort(reverse=True)

            # Top-K mean (K=3): robust aggregate score.
            k = min(3, len(sample_scores))
            top_k_score = float(np.mean(sample_scores[:k]))

            # Use the adaptive threshold for this identity.
            identity_thr = self._adaptive_thresholds.get(name, global_thr)
            agree = sum(1 for s in sample_scores if s >= identity_thr)
            total = len(sample_scores)

            ranked.append((name, top_k_score, identity_thr, agree, total))

        ranked.sort(key=lambda item: item[1], reverse=True)
        if not ranked:
            return None

        best_name, best_score, best_thr, best_agree, best_total = ranked[0]
        runner_up_score = ranked[1][1] if len(ranked) > 1 else 0.0
        runner_up_name = ranked[1][0] if len(ranked) > 1 else ""
        margin = best_score - runner_up_score if len(ranked) > 1 else 1.0
        agree_pct = (best_agree / best_total * 100) if best_total else 0.0

        # ── Structured diagnostic log (DEBUG level — disable in production) ──
        LOGGER.debug(
            "RECOGNITION DIAGNOSTICS\n"
            "  Identity:          %s\n"
            "  Top-K Score:       %.4f\n"
            "  Adaptive Threshold:%.4f\n"
            "  Global Threshold:  %.4f\n"
            "  Agreement:         %d/%d (%.0f%%)\n"
            "  Runner-up:         %s (%.4f)\n"
            "  Margin:            %.4f",
            best_name, best_score,
            best_thr, global_thr,
            best_agree, best_total, agree_pct,
            runner_up_name or "N/A", runner_up_score,
            margin,
        )

        # Gate 1: score must exceed the per-identity adaptive threshold.
        if best_score < best_thr:
            LOGGER.debug(
                "  DECISION: REJECTED (Gate 1 — score %.4f < threshold %.4f)",
                best_score, best_thr,
            )
            return None

        # Gate 2: at least 60% of stored embeddings must individually agree.
        min_agree = max(1, int(best_total * 0.6))
        if best_agree < min_agree:
            LOGGER.debug(
                "  DECISION: REJECTED (Gate 2 — agree %d/%d < required %d)",
                best_agree, best_total, min_agree,
            )
            return None

        # Gate 3: margin guard for multi-identity disambiguation.
        if len(ranked) > 1 and runner_up_score >= global_thr:
            if margin < 0.15:
                LOGGER.debug(
                    "  DECISION: REJECTED (Gate 3 — ambiguous margin %.4f < 0.15)",
                    margin,
                )
                return None

        LOGGER.debug(
            "  DECISION: ACCEPTED as '%s' (score=%.4f)",
            best_name, best_score,
        )
        return (best_name, best_score)

    # ── embedding extraction ─────────────────────────────────────────

    def embedding(self, frame: np.ndarray, face: FaceBox) -> np.ndarray | None:
        if self.session is None:
            return None
        # Minimum face size guard: too-small crops produce unreliable embeddings
        min_size = CONFIG.vision.face_min_size
        if face.w < min_size or face.h < min_size:
            LOGGER.debug(
                "Face too small (%dx%d < %d), skipping embedding.",
                face.w, face.h, min_size,
            )
            return None
            
        from jarvis_ai.vision.face_aligner import FaceAligner
        
        aligner = FaceAligner()
        if getattr(CONFIG.vision, "alignment_enabled", True):
            image = aligner.align(frame, face)
        else:
            # Fallback for when alignment is disabled via config
            crop = frame[face.y : face.y + face.h, face.x : face.x + face.w]
            if crop.size == 0:
                return None
            image = cv2.resize(crop, (112, 112))

        if image is None:
            return None

        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB).astype(np.float32)
        image = (image - 127.5) / 128.0
        tensor = np.transpose(image, (2, 0, 1))[None, :, :, :]
        output = self.session.run(None, {self.input_name: tensor})[0]
        emb = output.reshape(-1).astype(np.float32)
        norm = np.linalg.norm(emb)
        return emb / norm if norm else emb

    @staticmethod
    def _cosine(a: np.ndarray, b: np.ndarray) -> float:
        denom = float(np.linalg.norm(a) * np.linalg.norm(b))
        return float(np.dot(a, b) / denom) if denom else 0.0

    @staticmethod
    def save_intruder(frame: np.ndarray) -> Path:
        from jarvis_ai.config import INTRUDER_DIR

        path = INTRUDER_DIR / f"intruder_{timestamp_slug()}.jpg"
        cv2.imwrite(str(path), frame)
        return path
