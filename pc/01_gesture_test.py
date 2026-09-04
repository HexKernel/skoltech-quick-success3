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
    gcfg = cfg.get("models", {})
    hands = Hands(
        path,
        score_threshold=float(gcfg.get("gesture_score", 0.55)),
        min_streak=1,
    )
    print("palm = OPEN, fist = CLOSE — press Q")
    t0 = time.time()
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        g = hands.infer(frame, timestamp_ms=int((time.time() - t0) * 1000))
        label = f"{g.name or '—'} {g.score:.2f}  intent={g.intent or '—'}"
        cv2.putText(frame, label, (16, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 180), 2)
        cv2.imshow("Gestures", frame)
        if (cv2.waitKey(1) & 0xFF) in (ord("q"), ord("Q")):
            break
    hands.close()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
