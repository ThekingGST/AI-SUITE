import unittest
import numpy as np
import time

from jarvis_ai.vision.face_tracker import FaceTracker
from jarvis_ai.vision.object_tracker import ObjectTracker, TrackedObject
from jarvis_ai.vision.scene_analyzer import SceneAnalyzer
from jarvis_ai.vision.emotion_detection import EmotionDetector


class TestVision(unittest.TestCase):

    def test_face_tracker_iou(self):
        tracker = FaceTracker(iou_threshold=0.3, max_missing_time=1.0)
        
        # Initial detect
        boxes = [(10, 10, 50, 50)]
        confs = [0.9]
        tracked = tracker.update(boxes, confs)
        self.assertEqual(len(tracked), 1)
        fid = tracked[0].id
        
        # Slight move
        boxes_moved = [(12, 12, 50, 50)]
        confs_moved = [0.85]
        tracked_moved = tracker.update(boxes_moved, confs_moved)
        self.assertEqual(len(tracked_moved), 1)
        self.assertEqual(tracked_moved[0].id, fid)
        self.assertEqual(tracked_moved[0].box, boxes_moved[0])
        
        # Missing for a bit (but not max_missing_time)
        tracked_empty = tracker.update([], [])
        # In current implementation, if empty, it doesn't return old ones unless they are matched?
        # Wait, the tracker's return list is `list(self._tracked_faces.values())` which includes ones not seen in current frame.
        self.assertEqual(len(tracked_empty), 1)
        
        # Wait longer than max_missing_time
        time.sleep(1.1)
        tracked_expired = tracker.update([], [])
        self.assertEqual(len(tracked_expired), 0)

    def test_object_tracker(self):
        tracker = ObjectTracker(iou_threshold=0.3, max_missing_time=1.0)
        
        detections = [{"box": (10, 10, 50, 50), "label": "person", "confidence": 0.9}]
        tracked = tracker.update(detections)
        self.assertEqual(len(tracked), 1)
        oid = tracked[0].id
        
        # Wrong label should not match even if IoU is high
        detections_wrong = [{"box": (10, 10, 50, 50), "label": "dog", "confidence": 0.9}]
        tracked_wrong = tracker.update(detections_wrong)
        self.assertEqual(len(tracked_wrong), 2)  # Should have 1 old person (missing) + 1 new dog
        
    def test_scene_analyzer(self):
        objs = [
            TrackedObject(id="1", label="laptop", box=(0,0,0,0), confidence=0.9, first_seen=0, last_seen=0),
            TrackedObject(id="2", label="laptop", box=(0,0,0,0), confidence=0.9, first_seen=0, last_seen=0),
            TrackedObject(id="3", label="cup", box=(0,0,0,0), confidence=0.9, first_seen=0, last_seen=0)
        ]
        faces = [None] # just length matters for face_count
        
        desc = SceneAnalyzer.generate_description(objs, faces)
        self.assertTrue("one person" in desc or "1 people" in desc or "people" not in desc if faces[0] is None else True)
        # Using string matching flexibly
        self.assertIn("2 laptops", desc)
        self.assertIn("one cup", desc)
        
    def test_emotion_detector_fallback(self):
        detector = EmotionDetector()
        # Mock the ONNX session to fail loading
        detector.available = False
        result = detector.detect(np.zeros((100, 100, 3), dtype=np.uint8))
        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()
