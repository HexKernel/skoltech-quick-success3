#!/usr/bin/env python3
"""03 — YOLOE + gestures together, no motors."""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2
from force_policy import fsr_limit
from gestures import Hands
from overlay import draw
from serial_link import GripperStatus
from util import load_config, model_path, open_camera
from vision import Sight


def main() -> None:
    cfg = load_config()
    m = cfg["models"]
    gpath = model_path(cfg, "gesture")
    if not gpath.exists():
        sys.exit(f"missing {gpath} — run python pc/download_models.py")
    ypath = model_path(cfg, "yoloe")
    yolo_src = ypath if ypath.exists() else m["yoloe"]
    sight = Sight(
        Path(yolo_src),
        classes=list(m["classes"]),
        imgsz=int(m.get("yolo_imgsz", 320)),
        conf=float(m.get("yolo_conf", 0.20)),
        device=str(m.get("device", "cpu")),
    )
    hands = Hands(gpath, score_threshold=float(m.get("gesture_score", 0.55)))
    cap = open_camera(cfg)
    if not cap.isOpened():
        sys.exit("camera did not open")
    dummy = GripperStatus()
    t0 = time.time()
    print("combined sight+intent — press Q")
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        det = sight.best(frame)
        g = hands.infer(frame, timestamp_ms=int((time.time() - t0) * 1000))
        cls, limit = fsr_limit(det.name if det else None, cfg["force"], det.conf if det else 0.0)
        vis = draw(frame, det, g.name, g.intent, cls, limit, dummy)
        cv2.imshow("YOLOE + gestures", vis)
        if (cv2.waitKey(1) & 0xFF) in (ord("q"), ord("Q")):
            break
    hands.close()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
