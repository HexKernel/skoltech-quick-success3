"""MediaPipe Gesture Recognizer: Open_Palm → OPEN, Closed_Fist → CLOSE."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np


@dataclass
class Gesture:
    name: str
    score: float
    intent: Optional[str]  # "open" | "close" | None


class Hands:
    def __init__(
        self,
        model_path: Path,
        score_threshold: float = 0.55,
        open_name: str = "Open_Palm",
        close_name: str = "Closed_Fist",
        min_streak: int = 3,
        sticky_ms: int = 250,
    ):
        import mediapipe as mp
        from mediapipe.tasks.python.core import base_options as bo
        from mediapipe.tasks.python.vision import RunningMode
        from mediapipe.tasks.python.vision import gesture_recognizer as gr

        self.open_name = open_name
        self.close_name = close_name
        self.min_streak = int(min_streak)
        self.sticky_ms = int(sticky_ms)
        self._streak_name: Optional[str] = None
        self._streak = 0
        self._ts = 0
        self._sticky_intent: Optional[str] = None
        self._sticky_until = 0
        self._mp = mp

        try:
            from mediapipe.tasks.python.components.processors import ClassifierOptions

            canned = ClassifierOptions(
                score_threshold=float(score_threshold),
                category_allowlist=[open_name, close_name],
            )
            options = gr.GestureRecognizerOptions(
                base_options=bo.BaseOptions(
                    model_asset_path=str(model_path),
                    delegate=bo.BaseOptions.Delegate.CPU,
                ),
                running_mode=RunningMode.VIDEO,
                num_hands=1,
                canned_gesture_classifier_options=canned,
            )
        except (TypeError, ImportError, AttributeError):
            options = gr.GestureRecognizerOptions(
                base_options=bo.BaseOptions(
                    model_asset_path=str(model_path),
                    delegate=bo.BaseOptions.Delegate.CPU,
                ),
                running_mode=RunningMode.VIDEO,
                num_hands=1,
            )
        self._recognizer = gr.GestureRecognizer.create_from_options(options)

    def infer(self, frame_bgr: np.ndarray, timestamp_ms: Optional[int] = None) -> Gesture:
        rgb = frame_bgr[:, :, ::-1].copy()
        image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
        if timestamp_ms is None:
            self._ts += 33
            timestamp_ms = self._ts
        else:
            self._ts = max(self._ts + 1, int(timestamp_ms))
            timestamp_ms = self._ts
        result = self._recognizer.recognize_for_video(image, timestamp_ms)
        name, score = "", 0.0
        if result.gestures and result.gestures[0]:
            cat = result.gestures[0][0]
            name, score = cat.category_name, float(cat.score)
        if name in (self.open_name, self.close_name):
            if name == self._streak_name:
                self._streak += 1
            else:
                self._streak_name = name
                self._streak = 1
        else:
            self._streak_name = None
            self._streak = 0
        intent = None
        if self._streak >= self.min_streak and self._streak_name == self.open_name:
            intent = "open"
        elif self._streak >= self.min_streak and self._streak_name == self.close_name:
            intent = "close"
        if intent:
            self._sticky_intent = intent
            self._sticky_until = timestamp_ms + self.sticky_ms
        elif self._sticky_intent and timestamp_ms <= self._sticky_until:
            intent = self._sticky_intent
        else:
            self._sticky_intent = None
        return Gesture(name=name, score=score, intent=intent)

    def close(self) -> None:
        self._recognizer.close()
