from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import List, Dict, Tuple

@dataclass
class TrackedObject:
    id: str
    label: str
    box: Tuple[int, int, int, int]
    confidence: float
    first_seen: float
    last_seen: float

class ObjectTracker:
    """IoU-based object tracker with persistent IDs."""
    def __init__(self, iou_threshold: float = 0.3, max_missing_time: float = 1.0) -> None:
        self.iou_threshold = iou_threshold
        self.max_missing_time = max_missing_time
        self._tracked_objects: Dict[str, TrackedObject] = {}

    @staticmethod
    def _calculate_iou(box1: Tuple[int, int, int, int], box2: Tuple[int, int, int, int]) -> float:
        x1_1, y1_1, x2_1, y2_1 = box1
        x1_2, y1_2, x2_2, y2_2 = box2
        
        x_left = max(x1_1, x1_2)
        y_top = max(y1_1, y1_2)
        x_right = min(x2_1, x2_2)
        y_bottom = min(y2_1, y2_2)
        
        if x_right < x_left or y_bottom < y_top:
            return 0.0
            
        intersection = (x_right - x_left) * (y_bottom - y_top)
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0

    def update(self, detections: List[dict]) -> List[TrackedObject]:
        current_time = time.time()
        matched_ids = set()
        
        for det in detections:
            box = det["box"]
            label = det["label"]
            conf = det["confidence"]
            
            best_match_id = None
            best_iou = self.iou_threshold
            
            for tid, tracked in self._tracked_objects.items():
                if tid in matched_ids or tracked.label != label:
                    continue
                iou = self._calculate_iou(box, tracked.box)
                if iou > best_iou:
                    best_iou = iou
                    best_match_id = tid
                    
            if best_match_id:
                matched_ids.add(best_match_id)
                self._tracked_objects[best_match_id].box = box
                self._tracked_objects[best_match_id].last_seen = current_time
                self._tracked_objects[best_match_id].confidence = conf
            else:
                new_id = str(uuid.uuid4())[:8]
                new_obj = TrackedObject(
                    id=new_id,
                    label=label,
                    box=box,
                    confidence=conf,
                    first_seen=current_time,
                    last_seen=current_time
                )
                self._tracked_objects[new_id] = new_obj
                matched_ids.add(new_id)
                
        to_remove = []
        for tid, tracked in self._tracked_objects.items():
            if current_time - tracked.last_seen > self.max_missing_time:
                to_remove.append(tid)
                
        for tid in to_remove:
            del self._tracked_objects[tid]
            
        return list(self._tracked_objects.values())
