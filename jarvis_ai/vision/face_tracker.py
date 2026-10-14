from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import List, Dict, Optional

import numpy as np


@dataclass
class TrackedFace:
    id: str
    box: tuple[int, int, int, int]
    first_seen: float
    last_seen: float
    confidence: float
    features: Optional[np.ndarray] = None


class FaceTracker:
    """Lightweight IoU-based face tracker."""
    
    def __init__(self, iou_threshold: float = 0.3, max_missing_time: float = 1.0) -> None:
        self.iou_threshold = iou_threshold
        self.max_missing_time = max_missing_time
        self._tracked_faces: Dict[str, TrackedFace] = {}

    @staticmethod
    def _calculate_iou(box1: tuple[int, int, int, int], box2: tuple[int, int, int, int]) -> float:
        x1_1, y1_1, w1, h1 = box1
        x2_1, y2_1 = x1_1 + w1, y1_1 + h1
        
        x1_2, y1_2, w2, h2 = box2
        x2_2, y2_2 = x1_2 + w2, y1_2 + h2
        
        x_left = max(x1_1, x1_2)
        y_top = max(y1_1, y1_2)
        x_right = min(x2_1, x2_2)
        y_bottom = min(y2_1, y2_2)
        
        if x_right < x_left or y_bottom < y_top:
            return 0.0
            
        intersection = (x_right - x_left) * (y_bottom - y_top)
        area1 = w1 * h1
        area2 = w2 * h2
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0

    def update(self, detected_boxes: List[tuple[int, int, int, int]], confidences: List[float], features: List[Optional[np.ndarray]] = None) -> List[TrackedFace]:
        """Update tracker with new detections and return currently tracked faces."""
        current_time = time.time()
        
        if features is None:
            features = [None] * len(detected_boxes)
            
        matched_ids = set()
        
        for i, box in enumerate(detected_boxes):
            best_match_id = None
            best_iou = self.iou_threshold
            
            for fid, tracked in self._tracked_faces.items():
                if fid in matched_ids:
                    continue
                iou = self._calculate_iou(box, tracked.box)
                if iou > best_iou:
                    best_iou = iou
                    best_match_id = fid
                    
            if best_match_id:
                matched_ids.add(best_match_id)
                self._tracked_faces[best_match_id].box = box
                self._tracked_faces[best_match_id].last_seen = current_time
                self._tracked_faces[best_match_id].confidence = confidences[i]
                if features[i] is not None:
                    self._tracked_faces[best_match_id].features = features[i]
            else:
                new_id = str(uuid.uuid4())[:8]
                new_face = TrackedFace(
                    id=new_id,
                    box=box,
                    first_seen=current_time,
                    last_seen=current_time,
                    confidence=confidences[i],
                    features=features[i]
                )
                self._tracked_faces[new_id] = new_face
                matched_ids.add(new_id)
                
        # Remove old faces
        to_remove = []
        for fid, tracked in self._tracked_faces.items():
            if current_time - tracked.last_seen > self.max_missing_time:
                to_remove.append(fid)
                
        for fid in to_remove:
            del self._tracked_faces[fid]
            
        return list(self._tracked_faces.values())
