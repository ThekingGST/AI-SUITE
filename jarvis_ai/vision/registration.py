from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from jarvis_ai.vision.face_detection import FaceBox
from jarvis_ai.vision.face_quality import FaceQualityEvaluator, QualityResult
from jarvis_ai.vision.embedding_manager import EmbeddingManager
from jarvis_ai.config import CONFIG, FACE_DATASET_DIR
from jarvis_ai.utils.logger import LOGGER


@dataclass
class RegistrationState:
    person_name: str
    is_owner: bool = False
    required_views: list[str] = field(default_factory=list)
    completed_views: dict[str, tuple[np.ndarray, FaceBox]] = field(default_factory=dict)
    current_view_idx: int = 0
    start_time: float = field(default_factory=time.time)
    
    @property
    def current_view(self) -> str | None:
        if self.current_view_idx < len(self.required_views):
            return self.required_views[self.current_view_idx]
        return None
        
    @property
    def is_complete(self) -> bool:
        return self.current_view_idx >= len(self.required_views)


class GuidedRegistrar:
    """State machine for guided face registration."""

    def __init__(self, recognizer: "FaceRecognizer") -> None:
        self.recognizer = recognizer
        self.quality_evaluator = FaceQualityEvaluator()
        self.state: RegistrationState | None = None
        self._last_capture_time = 0.0

    def start_registration(self, name: str, is_owner: bool = False) -> None:
        """Initialize a new registration session."""
        views = list(getattr(CONFIG.vision, "registration_required_views", 
                           ("FRONT", "LEFT", "RIGHT", "UP", "DOWN", "SMILE", "NEUTRAL")))
        self.state = RegistrationState(
            person_name=name,
            is_owner=is_owner,
            required_views=views
        )
        LOGGER.info("STARTED GUIDED REGISTRATION for '%s'. Required views: %s", name, views)

    def process_frame(self, frame: np.ndarray, face: FaceBox) -> tuple[bool, str, QualityResult | None]:
        """Process a frame during active registration.
        
        Returns:
            (is_complete, instruction_message, quality_result)
        """
        if not self.state or self.state.is_complete:
            return True, "Registration complete", None

        now = time.time()
        # Cooldown between captures to ensure diversity and give user time to move
        if now - self._last_capture_time < 1.0:
            return False, f"Hold {self.state.current_view}...", None

        current_view = self.state.current_view
        if not current_view:
            return True, "Registration complete", None

        # Evaluate quality
        quality = self.quality_evaluator.evaluate(frame, face)
        if not quality.accepted:
            return False, f"Quality poor: {', '.join(quality.reasons)}", quality

        # Note: In a fully advanced version, we would verify the pose actually 
        # matches the requested `current_view` using landmark geometry.
        # For now, we trust the user followed the instruction if quality is good.

        # Store the successful capture
        self.state.completed_views[current_view] = (frame.copy(), face)
        self.state.current_view_idx += 1
        self._last_capture_time = now

        LOGGER.info("REGISTRATION CAPTURE: '%s' view successful.", current_view)

        if self.state.is_complete:
            self._finalize()
            return True, "Registration complete!", quality

        next_view = self.state.current_view
        return False, f"Please look: {next_view}", quality

    def _finalize(self) -> None:
        """Generate embeddings and save to database."""
        if not self.state:
            return

        name = self.state.person_name
        is_owner = self.state.is_owner
        
        # We delegate the actual embedding generation and saving back to the recognizer
        # or handle it directly here using the recognizer's methods.
        
        # 1. Collect samples
        samples_for_recognizer = []
        for view, (frame, face) in self.state.completed_views.items():
            samples_for_recognizer.append((frame, face))
            
        # 2. Call recognizer to generate and add embeddings
        if is_owner:
            # For owner, we just need one frame for the legacy register_owner
            frame, face = samples_for_recognizer[0]
            self.recognizer.register_owner(frame, face)
        else:
            self.recognizer.register_person(name, samples_for_recognizer)

        LOGGER.info("GUIDED REGISTRATION COMPLETE for '%s'. Saved %d views.", 
                    name, len(samples_for_recognizer))
        self.state = None

    def cancel(self) -> None:
        """Cancel an ongoing registration."""
        if self.state:
            LOGGER.info("Cancelled registration for '%s'.", self.state.person_name)
            self.state = None
