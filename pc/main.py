#!/usr/bin/env python3
"""Full loop: camera → YOLOE + gesture → force policy → ESP32.

Operator: Open_Palm = OPEN, Closed_Fist = CLOSE (or keys o / c / space).
A CLOSE latches the force cap for the whole grasp — YOLO cannot raise it.
Space STOP sticks until the fist is released. Safety stop is on the ESP32.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2
from force_policy import RANK, fsr_limit
from gestures import Hands
from overlay import draw
from serial_link import connect
from util import load_config, model_path, open_camera
from vision import Sight


def main() -> None:
    cfg = load_config()
    m = cfg["models"]
    gcfg = cfg.get("gestures", {})
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
        open_name=str(gcfg.get("open", "Open_Palm")),
        close_name=str(gcfg.get("close", "Closed_Fist")),
        min_streak=int(gcfg.get("min_streak", 3)),
        sticky_ms=int(gcfg.get("sticky_ms", 250)),
    )
    gripper = connect(cfg)
    cap = open_camera(cfg)
    if not cap.isOpened():
        sys.exit("camera did not open — close Zoom/Teams, try camera.index 1")

    command: str | None = None
    fist_since_stop = True
    grasp_cls: str | None = None
    grasp_limit: int | None = None
    force_conf = float(m.get("force_min_conf", 0.35))
    yolo_conf = float(m.get("yolo_conf", 0.20))
    t0 = time.monotonic()
    print("running — palm OPEN, fist CLOSE, o/c keys, space STOP, q quit")
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("camera frame dropped")
                if (cv2.waitKey(30) & 0xFF) in (ord("q"), ord("Q"), 27):
                    break
                continue
            ts = int((time.monotonic() - t0) * 1000)
            det = sight.best(frame)
            g = hands.infer(frame, timestamp_ms=ts)
            live_cls, live_limit = fsr_limit(
                det.name if det else None,
                cfg["force"],
                det.conf if det else 0.0,
                min_conf=yolo_conf,
                force_min_conf=force_conf,
            )
            status = gripper.pump()

            intent = g.intent
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("o"), ord("O")):
                intent = "open"
            elif key in (ord("c"), ord("C")):
                intent = "close"
            elif key == ord(" "):
                intent = "stop"
            elif key in (ord("q"), ord("Q"), 27):
                break

            if command == "stop" and intent == "close" and fist_since_stop:
                intent = None
            if intent != "close":
                fist_since_stop = False

            if intent == "stop" and command != "stop":
                gripper.stop()
                command = "stop"
                fist_since_stop = True
                grasp_cls = None
                grasp_limit = None
                print("→ STOP")
            elif intent == "open" and command != "open":
                gripper.open_gripper()
                command = "open"
                fist_since_stop = False
                grasp_cls = None
                grasp_limit = None
                print("→ OPEN")
            elif intent == "close" and command != "close":
                grasp_cls, grasp_limit = live_cls, live_limit
                gripper.close_gripper(grasp_limit)
                command = "close"
                print(f"→ CLOSE {grasp_cls} fsr_max={grasp_limit}")
            elif command == "close" and grasp_limit is not None:
                # Never raise the cap mid-grasp. Lower it if YOLO becomes more conservative.
                if RANK.get(live_cls, 0) < RANK.get(grasp_cls or "unknown", 0):
                    grasp_cls, grasp_limit = live_cls, live_limit
                    gripper.close_gripper(grasp_limit)
                    print(f"→ CLOSE safer {grasp_cls} fsr_max={grasp_limit}")

            hud_cls = grasp_cls or live_cls
            hud_limit = grasp_limit if grasp_limit is not None else live_limit
            vis = draw(frame, det, g.name, intent or command, hud_cls, hud_limit, status)
            cv2.imshow("QS gripper", vis)
    finally:
        hands.close()
        gripper.close_port()
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
