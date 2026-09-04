#!/usr/bin/env python3
"""Download workshop models into models/ if they are not already there."""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MODELS = ROOT / "models"
MODELS.mkdir(exist_ok=True)

GESTURE_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "gesture_recognizer/gesture_recognizer/float16/latest/gesture_recognizer.task"
)


def fetch(url: str, dest: Path) -> None:
    if dest.exists() and dest.stat().st_size > 1000:
        print(f"ok {dest.name}")
        return
    print(f"downloading {dest.name} ...")
    urllib.request.urlretrieve(url, dest)
    print(f"saved {dest}")


def main() -> None:
    fetch(GESTURE_URL, MODELS / "gesture_recognizer.task")
    print(
        "YOLOE weights: first `python pc/02_yolo_test.py` downloads "
        "yoloe-26n-seg.pt + mobileclip2_b.ts into the working directory / models/.\n"
        "If the starter USB stick has those files, copy them into models/."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
