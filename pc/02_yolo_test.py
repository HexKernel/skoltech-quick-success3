#!/usr/bin/env python3
"""02 — YOLOE open-vocabulary: egg / sponge / stone. Q in the video window to quit.

This script is vision-only. Keys o/c/space do nothing here — that is pc/main.py.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2
from force_policy import canonical_class
from overlay import draw_box
from util import load_config, model_path, open_camera
from vision import Sight

GRASP = {"egg", "sponge", "stone"}


def main() -> None:
    cfg = load_config()
    m = cfg["models"]
    weights = model_path(cfg, "yoloe")
    path = weights if weights.exists() else m["yoloe"]
    prompts = list(m["classes"])
    print(f"loading YOLOE {path}")
    sight = Sight(
        Path(path),
        classes=prompts,
        imgsz=int(m.get("yolo_imgsz", 640)),
        conf=float(m.get("yolo_conf", 0.01)),
        device=str(m.get("device", "cpu")),
        visual_prompts=bool(m.get("visual_prompts", False)),
    )
    cap = open_camera(cfg)
    if not cap.isOpened():
        sys.exit("camera did not open — close Zoom/Teams, try camera.index 1 in pc/config.yaml")
    print("YOLOE ok — keys o/c/space are ignored here.")
    print("Hold an egg / sponge / stone. Q in the video window to quit.")
    cv2.namedWindow("YOLOE", cv2.WINDOW_NORMAL)
    misses = 0
    last_print = ""
    t_prev = time.monotonic()
    while True:
        ok, frame = cap.read()
        if not ok:
            misses += 1
            if misses > 60:
                sys.exit("no camera frames — close Zoom/Teams, set camera.index: 1 in pc/config.yaml")
            if (cv2.waitKey(30) & 0xFF) in (ord("q"), ord("Q")):
                break
            continue
        misses = 0
        dets = sight.infer(frame)
        grasp = [d for d in dets if canonical_class(d.name) in GRASP]
        now = time.monotonic()
        fps = 1.0 / max(1e-3, now - t_prev)
        t_prev = now
        vis = frame.copy()
        for det in dets:
            draw_box(vis, det)
        label = canonical_class(grasp[0].name).upper() if grasp else "NO OBJECT"
        cv2.putText(
            vis,
            f"YOLO  {label}   {fps:.0f} fps   Q=quit",
            (16, 32),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (240, 240, 240),
            2,
        )
        shown = " ".join(f"{d.name}:{d.conf:.2f}" for d in dets) or "(no boxes)"
        if shown != last_print:
            print(f"dets {shown}", flush=True)
            last_print = shown
        cv2.imshow("YOLOE", vis)
        if (cv2.waitKey(1) & 0xFF) in (ord("q"), ord("Q")):
            break
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
