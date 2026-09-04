#!/usr/bin/env python3
"""02 — YOLOE open-vocabulary: egg / sponge / stone. Q to quit."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2
from overlay import draw
from serial_link import GripperStatus
from util import load_config, model_path, open_camera
from vision import Sight


def main() -> None:
    cfg = load_config()
    m = cfg["models"]
    weights = model_path(cfg, "yoloe")
    # Ultralytics also accepts a bare filename and downloads it
    path = weights if weights.exists() else m["yoloe"]
    print(f"loading YOLOE {path} (first run downloads weights + mobileclip2_b.ts)")
    sight = Sight(
        Path(path),
        classes=list(m["classes"]),
        imgsz=int(m.get("yolo_imgsz", 320)),
        conf=float(m.get("yolo_conf", 0.20)),
        device=str(m.get("device", "cpu")),
    )
    cap = open_camera(cfg)
    if not cap.isOpened():
        sys.exit("camera did not open")
    print("YOLOE ok — press Q")
    dummy = GripperStatus()
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        det = sight.best(frame)
        name = det.name if det else "unknown"
        vis = draw(frame, det, "", None, name, 1, dummy)
        cv2.imshow("YOLOE", vis)
        if (cv2.waitKey(1) & 0xFF) in (ord("q"), ord("Q")):
            break
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
