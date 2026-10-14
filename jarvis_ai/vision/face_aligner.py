from __future__ import annotations

import cv2
import numpy as np

from jarvis_ai.vision.face_detection import FaceBox
from jarvis_ai.utils.logger import LOGGER


class FaceAligner:
    """Aligns faces using 5-point landmarks for SFace recognition.

    SFace expects a 112x112 face crop aligned such that the eyes, nose,
    and mouth are in standard positions. This alignment is critical for
    robustness against head rotation and pose variations.
    """

    def __init__(self, target_size: tuple[int, int] = (112, 112)) -> None:
        self.target_size = target_size
        
        # Standard landmark coordinates for 112x112 SFace alignment
        # SFace standard reference points:
        # [left_eye, right_eye, nose, left_mouth, right_mouth]
        # Wait, YuNet outputs: [right_eye, left_eye, nose_tip, right_mouth_corner, left_mouth_corner]
        # We must map YuNet landmarks to the standard reference points.
        
        # Reference points for 112x112 from SFace documentation / deepinsight ArcFace
        # Coordinates are (x, y)
        self.reference_pts = np.array([
            [38.2946, 51.6963],   # Right eye (viewer's left)
            [73.5318, 51.5014],   # Left eye (viewer's right)
            [56.0252, 71.7366],   # Nose
            [41.5493, 92.3655],   # Right mouth corner
            [70.7299, 92.2041]    # Left mouth corner
        ], dtype=np.float32)

    def align(self, frame: np.ndarray, face: FaceBox) -> np.ndarray | None:
        """Align the face using an affine transformation if landmarks are available.
        
        If landmarks are not available (e.g., legacy SSD detector), falls back
        to a simple crop and resize.
        """
        if not face.landmarks or len(face.landmarks) != 5:
            # Fallback to simple crop
            LOGGER.debug("No landmarks for alignment. Falling back to simple crop.")
            crop = frame[face.y : face.y + face.h, face.x : face.x + face.w]
            if crop.size == 0:
                return None
            return cv2.resize(crop, self.target_size)

        # YuNet outputs: [right_eye, left_eye, nose, right_mouth, left_mouth]
        # This order perfectly matches our reference_pts order.
        src_pts = np.array(face.landmarks, dtype=np.float32)

        # Estimate affine transform
        # We use estimateAffinePartial2D which finds an optimal similarity transform
        # (rotation, uniform scaling, translation) with 4 degrees of freedom.
        # This is more robust than a full affine transform for face alignment.
        matrix, inliers = cv2.estimateAffinePartial2D(src_pts, self.reference_pts, method=cv2.LMEDS)

        if matrix is None:
            LOGGER.warning("Affine transform estimation failed. Falling back to crop.")
            crop = frame[face.y : face.y + face.h, face.x : face.x + face.w]
            if crop.size == 0:
                return None
            return cv2.resize(crop, self.target_size)

        # Warp the entire frame to the 112x112 target size
        aligned_face = cv2.warpAffine(
            frame, 
            matrix, 
            self.target_size,
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REPLICATE
        )
        return aligned_face
