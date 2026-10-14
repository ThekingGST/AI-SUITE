from __future__ import annotations

import time
from collections.abc import Callable

import cv2
import numpy as np
import pyautogui

from jarvis_ai.config import CONFIG
from jarvis_ai.utils.logger import LOGGER


class GestureController:
    """MediaPipe hand gestures mapped to low-frequency desktop actions."""

    def __init__(self, on_action: Callable[[str], None] | None = None) -> None:
        self.on_action = on_action
        self._last_action = 0.0
        self.hands = None
        try:
            import mediapipe as mp

            self.mp_hands = mp.solutions.hands
            self.mp_draw = mp.solutions.drawing_utils
            self.hands = self.mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.65, min_tracking_confidence=0.65)
        except Exception as exc:
            LOGGER.warning("Gesture controller unavailable: %s", exc)

    def process(self, frame: np.ndarray) -> str | None:
        if frame is None or frame.size == 0:
            return None

        if self.hands is None:
            return None
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self.hands.process(rgb)
        if not result.multi_hand_landmarks:
            return None
        hand = result.multi_hand_landmarks[0]
        self.mp_draw.draw_landmarks(frame, hand, self.mp_hands.HAND_CONNECTIONS)
        fingers = self._finger_states(hand)
        action = self._classify(fingers)
        if action and time.time() - self._last_action >= CONFIG.vision.gesture_cooldown_seconds:
            self._last_action = time.time()
            self._execute(action)
            if self.on_action:
                self.on_action(action)
            return action
        return None

    def _finger_states(self, hand) -> list[bool]:
        tips = [4, 8, 12, 16, 20]
        pips = [3, 6, 10, 14, 18]
        lm = hand.landmark
        states = [lm[tips[0]].x < lm[pips[0]].x]
        states.extend(lm[tips[i]].y < lm[pips[i]].y for i in range(1, 5))
        return states

    @staticmethod
    def _classify(fingers: list[bool]) -> str | None:
        count = sum(fingers)
        if count == 5:
            return "play_pause"
        if count == 0:
            return "screenshot"
        if fingers[1] and fingers[2] and not any((fingers[0], fingers[3], fingers[4])):
            return "volume_up"
        if fingers[1] and not any((fingers[0], fingers[2], fingers[3], fingers[4])):
            return "volume_down"
        return None

    @staticmethod
    def _execute(action: str) -> None:
        if action == "play_pause":
            pyautogui.press("playpause")
        elif action == "screenshot":
            pyautogui.hotkey("win", "printscreen")
        elif action == "volume_up":
            pyautogui.press("volumeup")
        elif action == "volume_down":
            pyautogui.press("volumedown")
