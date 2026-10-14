from __future__ import annotations
from typing import List, Dict

class SceneAnalyzer:
    """Analyzes tracked objects and faces to generate natural language scene descriptions."""
    
    @staticmethod
    def generate_description(tracked_objects: List['TrackedObject'], tracked_faces: List['TrackedFace'] = None) -> str:
        if not tracked_objects and not (tracked_faces and len(tracked_faces) > 0):
            return "I don't see anything notable in the scene."
            
        counts: Dict[str, int] = {}
        for obj in tracked_objects:
            counts[obj.label] = counts.get(obj.label, 0) + 1
            
        face_count = len(tracked_faces) if tracked_faces else 0
        
        parts = []
        if face_count > 0:
            if face_count == 1:
                parts.append("one person")
            else:
                parts.append(f"{face_count} people")
                
        for label, count in counts.items():
            if label == "person":
                continue # Handled by face/person logic
            if count == 1:
                parts.append(f"one {label}")
            else:
                parts.append(f"{count} {label}s")
                
        if not parts:
            return "I can see some movement, but nothing clearly identifiable."
            
        if len(parts) == 1:
            desc = f"I see {parts[0]}."
        elif len(parts) == 2:
            desc = f"I see {parts[0]} and {parts[1]}."
        else:
            desc = f"I see {', '.join(parts[:-1])}, and {parts[-1]}."
            
        return desc
