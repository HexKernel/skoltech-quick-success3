#!/usr/bin/env python3
"""Full loop: camera → YOLOE + gesture → force policy → ESP32.

Operator: Open_Palm = OPEN, Closed_Fist = CLOSE (or keys o / c).
Robot: max FSR from the detected class. Safety stop is on the ESP32.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2
from force_policy import fsr_limit
from gestures import Hands
from overlay import draw
from serial_link import connect
from util import load_config, model_path, open_camera
from vision import Sight


def main() -> None:
    cfg = load_config()
    m = cfg["models"]
    gpath = model_path(cfg, "gesture")
    if not gpath.exists():
        sys.exit(f"missing {gpath} — python pc/download_models.py")
    ypath = model_path(cfg, "yoloe")
    yolo_src = ypath if ypath.exists() else m["yoloe"]

    print("loading YOLOE…")
    sight = Sight(
        Path(yolo_src),
        classes=list(m["classes"]),
        imgsz=int(m.get("yolo_imgsz", 320)),
        conf=float(m.get("yolo_conf", 0.20)),
        device=str(m.get("device", "cpu")),
    )
    print("loading gestures…")
    hands = Hands(
        gpath,
        score_threshold=float(m.get("gesture_score", 0.55)),
        min_streak=int(cfg.get("gestures", {}).get("min_streak", 3)),
    )
    gripper = connect(cfg)
    cap = open_camera(cfg)
    if not cap.isOpened():
        sys.exit("camera did not open")

    last_intent = None
    t0 = time.time()
    print("running — palm OPEN, fist CLOSE, o/c keys, q quit")
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("camera frame dropped")
                continue
            ts = int((time.time() - t0) * 1000)
            det = sight.best(frame)
            g = hands.infer(frame, timestamp_ms=ts)
            cls, limit = fsr_limit(
                det.name if det else None,
                cfg["force"],
                det.conf if det else 0.0,
                min_conf=float(m.get("yolo_conf", 0.20)),
            )
            status = gripper.pump()

            intent = g.intent
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("o"), ord("O")):
                intent = "open"
            elif key in (ord("c"), ord("C")):
                intent = "close"
            elif key == ord(" "):
                gripper.stop()
                last_intent = "stop"
            elif key in (ord("q"), ord("Q"), 27):
                break

            if intent and intent != last_intent:
                if intent == "open":
                    gripper.open_gripper()
                    print("→ OPEN")
                elif intent == "close":
                    gripper.close_gripper(limit)
                    print(f"→ CLOSE {cls} fsr_max={limit}")
                last_intent = intent
            if intent is None:
                last_intent = None

            vis = draw(frame, det, g.name, intent or g.intent, cls, limit, status)
            cv2.imshow("QS gripper", vis)
    finally:
        hands.close()
        gripper.close_port()
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
