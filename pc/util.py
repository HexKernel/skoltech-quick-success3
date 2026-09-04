"""Shared paths and config."""
from __future__ import annotations

from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def load_config(path: Path | None = None) -> dict:
    cfg_path = path or (HERE / "config.yaml")
    with cfg_path.open() as f:
        return yaml.safe_load(f)


def model_path(cfg: dict, key: str) -> Path:
    models = cfg.get("models", {})
    folder = ROOT / models.get("dir", "models")
    return folder / models[key]


def open_camera(cfg: dict):
    import cv2

    cam = cfg.get("camera", {})
    idx = int(cam.get("index", 0))
    backend = str(cam.get("backend", "auto")).lower()
    if backend == "auto":
        import sys

        if sys.platform == "darwin":
            backend = "avfoundation"
        elif sys.platform.startswith("win"):
            backend = "dshow"
    if backend == "dshow":
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
    elif backend == "avfoundation":
        cap = cv2.VideoCapture(idx, cv2.CAP_AVFOUNDATION)
    else:
        cap = cv2.VideoCapture(idx)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(cam.get("width", 640)))
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(cam.get("height", 480)))
    return cap
