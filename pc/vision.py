"""YOLOE open-vocabulary detector (egg / sponge / stone)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np


@dataclass
class Detection:
    name: str
    conf: float
    xyxy: tuple[float, float, float, float]


def _box_name(names, cls_id: int) -> str:
    if names is None:
        return str(cls_id)
    if isinstance(names, dict):
        return str(names.get(cls_id, cls_id))
    try:
        return str(names[cls_id])
    except Exception:
        return str(cls_id)


class Sight:
    def __init__(self, model_path: Path, classes: list[str], imgsz: int = 320, conf: float = 0.20, device: str = "cpu"):
        from ultralytics import YOLOE

        self.classes = list(classes)
        self.imgsz = int(imgsz)
        self.conf = float(conf)
        self.device = device
        src = Path(model_path)
        work = src.parent if src.suffix else Path.cwd()
        work.mkdir(parents=True, exist_ok=True)
        prev = os.getcwd()
        try:
            os.chdir(work)
            load = src.name if src.suffix else str(src)
            self.model = YOLOE(load)
            if hasattr(self.model, "eval"):
                try:
                    self.model.eval()
                except Exception:
                    pass
            try:
                self.model.set_classes(self.classes)
            except TypeError:
                self.model.set_classes(self.classes, self.model.get_text_pe(self.classes))
        finally:
            os.chdir(prev)

    def infer(self, frame_bgr: np.ndarray) -> list[Detection]:
        results = self.model.predict(
            frame_bgr,
            imgsz=self.imgsz,
            conf=self.conf,
            device=self.device,
            verbose=False,
        )
        out: list[Detection] = []
        if not results:
            return out
        r = results[0]
        if r.boxes is None or len(r.boxes) == 0:
            return out
        names = r.names
        for box in r.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            x1, y1, x2, y2 = (float(v) for v in box.xyxy[0].tolist())
            out.append(Detection(name=_box_name(names, cls_id), conf=conf, xyxy=(x1, y1, x2, y2)))
        out.sort(key=lambda d: d.conf, reverse=True)
        return out

    def best(self, frame_bgr: np.ndarray) -> Optional[Detection]:
        dets = self.infer(frame_bgr)
        return dets[0] if dets else None
