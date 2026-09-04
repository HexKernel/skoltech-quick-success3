#!/usr/bin/env python3
"""01 — MediaPipe Open_Palm / Closed_Fist. Q to quit."""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2
from gestures import Hands
from util import load_config, model_path, open_camera


def main() -> None:
    cfg = load_config()
    path = model_path(cfg, "gesture")
    if not path.exists():
        sys.exit(f"missing {path} — run python pc/download_models.py")
    cap = open_camera(cfg)
    if not cap.isOpened():
        sys.exit("camera did not open")
    mcfg = cfg.get("models", {})
    gcfg = cfg.get("gestures", {})
    hands = Hands(
        path,
        score_threshold=float(mcfg.get("gesture_score", 0.55)),
        open_name=str(gcfg.get("open", "Open_Palm")),
        close_name=str(gcfg.get("close", "Closed_Fist")),
        min_streak=int(gcfg.get("min_streak", 3)),
        sticky_ms=int(gcfg.get("sticky_ms", 250)),
    )
    print("Open palm = OPEN, closed fist = CLOSE — Q quits")
    t0 = time.time()
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frame = cv2.flip(frame, 1)
        g = hands.infer(frame, timestamp_ms=int((time.time() - t0) * 1000))
        intent = (g.intent or "SHOW PALM OR FIST").upper()
        color = (80, 220, 80) if g.intent == "open" else (60, 160, 255) if g.intent == "close" else (220, 220, 220)
        cv2.putText(frame, intent, (16, 48), cv2.FONT_HERSHEY_SIMPLEX, 1.15, color, 3)
        cv2.putText(
            frame,
            f"{g.name or 'no gesture'}  {g.score:.2f}",
            (16, 82),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            color,
            2,
        )
        cv2.putText(
            frame,
            "OPEN = open palm    CLOSE = closed fist    Q = quit",
            (16, frame.shape[0] - 18),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (230, 230, 230),
            1,
        )
        cv2.imshow("Gestures", frame)
        if (cv2.waitKey(1) & 0xFF) in (ord("q"), ord("Q"), 27):
            break
    hands.close()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
