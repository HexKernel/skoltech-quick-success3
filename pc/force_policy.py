"""Map YOLO class → FSR ADC stop threshold.

The operator only says OPEN / CLOSE. Max force is chosen from what the
camera sees. Unknown or low-confidence detections use the conservative
`unknown` limit so an egg is never treated as a stone.
"""
from __future__ import annotations

from typing import Optional


ALIASES = {
    "egg": "egg",
    "quail egg": "egg",
    "eggs": "egg",
    "sponge": "sponge",
    "foam": "sponge",
    "kitchen sponge": "sponge",
    "stone": "stone",
    "rock": "stone",
    "geological sample": "stone",
}


def canonical_class(name: Optional[str]) -> str:
    if not name:
        return "unknown"
    key = name.strip().lower()
    return ALIASES.get(key, key if key in ("egg", "sponge", "stone") else "unknown")


def fsr_limit(object_class: Optional[str], force_cfg: dict, conf: float = 1.0, min_conf: float = 0.20) -> tuple[str, int]:
    cls = canonical_class(object_class)
    if conf < min_conf:
        cls = "unknown"
    limits = force_cfg or {}
    value = int(limits.get(cls, limits.get("unknown", 650)))
    return cls, value
