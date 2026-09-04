#!/usr/bin/env python3
"""00 — webcam only. Q to quit."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2
from util import load_config, open_camera


def main() -> None:
    cap = open_camera(load_config())
    if not cap.isOpened():
        sys.exit("camera did not open — close Zoom/Teams, try camera.index 1, on Windows set backend: dshow")
    print("camera ok — press Q")
    misses = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            misses += 1
            if misses > 30:
                sys.exit("camera read failed — try camera.index 1 or backend: dshow")
            continue
        misses = 0
        cv2.imshow("Camera", frame)
        if (cv2.waitKey(1) & 0xFF) in (ord("q"), ord("Q")):
            break
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
