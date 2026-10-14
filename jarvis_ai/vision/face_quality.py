from __future__ import annotations

import math
from dataclasses import dataclass
import cv2
import numpy as np

from jarvis_ai.vision.face_detection import FaceBox
from jarvis_ai.config import CONFIG
from jarvis_ai.utils.logger import LOGGER


@dataclass
class QualityResult:
    score: float
    accepted: bool
    reasons: list[str]


class FaceQualityEvaluator:
    """Heuristic-based face quality filter for registration and recognition."""

    def __init__(self) -> None:
        self.min_size = getattr(CONFIG.vision, "face_min_size", 80)
        self.blur_threshold = getattr(CONFIG.vision, "blur_threshold", 100.0)

    def evaluate(self, frame: np.ndarray, face: FaceBox) -> QualityResult:
        """Evaluate face quality without using deep learning (heuristics only)."""
        reasons = []
        score = 1.0

        # 1. Size Check
        if face.w < self.min_size or face.h < self.min_size:
            reasons.append(f"Too small ({face.w}x{face.h} < {self.min_size})")
            score -= 0.5
        else:
            reasons.append(f"✓ Size OK ({face.w}x{face.h})")

        # Extract crop for further checks
        crop = frame[max(0, face.y):face.y + face.h, max(0, face.x):face.x + face.w]
        
        if crop.size > 0:
            # 2. Blur Check (Laplacian Variance)
            # High variance = sharp edges. Low variance = blurry.
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            if laplacian_var < self.blur_threshold:
                reasons.append(f"Blurry (score={laplacian_var:.1f} < {self.blur_threshold})")
                score -= 0.4
            else:
                reasons.append(f"✓ Sharpness OK ({laplacian_var:.1f})")

        # 3. Pose / Geometry Check (if landmarks available)
        if face.landmarks and len(face.landmarks) == 5:
            # right_eye, left_eye, nose, right_mouth, left_mouth
            re, le, nose, rm, lm = face.landmarks
            
            # Distance between eyes
            eye_dist = math.dist(re, le)
            if eye_dist < face.w * 0.2:
                reasons.append("Extreme pose (eyes too close/side profile)")
                score -= 0.3
            else:
                reasons.append("✓ Pose OK")
                
            # Basic bounding box sanity for landmarks
            for (lx, ly) in face.landmarks:
                # Add a small padding tolerance (10%)
                pad_x = face.w * 0.1
                pad_y = face.h * 0.1
                if not (face.x - pad_x <= lx <= face.x + face.w + pad_x and 
                        face.y - pad_y <= ly <= face.y + face.h + pad_y):
                    reasons.append("Landmarks out of bounds (heavy occlusion/bad detection)")
                    score -= 0.4
                    break
        else:
            reasons.append("No landmarks available for pose check")

        # Calculate final acceptance
        # If the score dropped below a certain threshold (e.g. 0.8), reject.
        # But specifically, if ANY negative reason exists, we might want to reject for registration.
        # For this filter, we consider a score < 0.6 as a hard fail.
        # Also, any specific failures (size, blur, pose) drop the score below 0.6 if combined,
        # or we just rely on the specific checks.
        
        # We'll use a strict policy: no negative reasons allowed.
        has_negatives = any(not r.startswith("✓") for r in reasons)
        accepted = not has_negatives

        if not accepted:
            LOGGER.debug("Face quality rejected. Score: %.2f. Reasons: %s", score, reasons)

        return QualityResult(max(0.0, score), accepted, reasons)
