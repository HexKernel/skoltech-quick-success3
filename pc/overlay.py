"""OpenCV HUD: YOLO box, gesture, FSR vs limit, gripper state."""
from __future__ import annotations

from typing import Optional

import cv2
import numpy as np

from force_policy import canonical_class
from serial_link import GripperStatus
from vision import Detection

COLORS = {
    "egg": (0, 220, 255),
    "sponge": (0, 165, 255),
    "stone": (180, 180, 180),
    "person": (80, 220, 80),
    "unknown": (200, 200, 200),
}


def _color(name: str) -> tuple[int, int, int]:
    key = (name or "").strip().lower()
    if key in COLORS:
        return COLORS[key]
    return COLORS.get(canonical_class(name), COLORS["unknown"])


def draw_box(vis: np.ndarray, det: Detection) -> None:
    x1, y1, x2, y2 = (int(v) for v in det.xyxy)
    color = _color(det.name)
    cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)
    label = f"{det.name} {det.conf:.2f}"
    cv2.putText(vis, label, (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)


def draw(
    frame: np.ndarray,
    det: Optional[Detection],
    gesture_name: str,
    intent: Optional[str],
    cls: str,
    fsr_max: int,
    status: GripperStatus,
    dets: Optional[list[Detection]] = None,
    hint: Optional[str] = None,
) -> np.ndarray:
    vis = frame.copy()
    h, w = vis.shape[:2]
    boxes = dets if dets is not None else ([det] if det is not None else [])
    for box in boxes:
        if box is not None:
            draw_box(vis, box)

    panel_w = 280
    overlay = vis.copy()
    cv2.rectangle(overlay, (w - panel_w, 0), (w, h), (20, 20, 20), -1)
    vis = cv2.addWeighted(overlay, 0.55, vis, 0.45, 0)

    x0 = w - panel_w + 14
    y = 36
    lines = [
        f"SEE   {cls.upper()}",
        f"INTENT {intent or '—'}",
        f"HAND  {gesture_name or '—'}",
        f"FSR   {status.fsr} / {fsr_max}",
        f"STATE {status.state}",
        f"LINK  {'ESP32' if status.connected else 'MOCK'}",
    ]
    for line in lines:
        cv2.putText(vis, line, (x0, y), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (240, 240, 240), 2)
        y += 32

    bar_x, bar_y, bar_w, bar_h = x0, y + 8, panel_w - 40, 18
    cv2.rectangle(vis, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (220, 220, 220), 1)
    frac = 0.0 if fsr_max <= 0 else min(1.0, status.fsr / float(fsr_max))
    fill = int(frac * (bar_w - 2))
    col = (80, 80, 255) if status.state == "LIMIT" else (80, 200, 120)
    if fill > 0:
        cv2.rectangle(vis, (bar_x + 1, bar_y + 1), (bar_x + 1 + fill, bar_y + bar_h - 1), col, -1)
    y = bar_y + 48
    hint = hint or "palm=OPEN  fist=CLOSE  o/c  space=STOP  q"
    cv2.putText(vis, hint, (x0, y), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (180, 180, 180), 1)
    return vis
