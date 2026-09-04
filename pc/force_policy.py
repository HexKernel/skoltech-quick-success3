"""Map YOLO class → FSR ADC stop threshold.

The operator only says OPEN / CLOSE. Max force is chosen from what the
camera sees. Unknown or low-confidence detections use the conservative
`unknown` limit so an egg is never treated as a stone.

RANK is used to refuse raising the cap mid-grasp.
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
    "piece of rock": "stone",
    "rock fragment": "stone",
    "geological sample": "stone",
}

RANK = {"unknown": 0, "egg": 1, "sponge": 2, "stone": 3}


def canonical_class(name: Optional[str]) -> str:
    if not name:
        return "unknown"
    key = name.strip().lower()
    return ALIASES.get(key, key if key in ("egg", "sponge", "stone") else "unknown")


def fsr_limit(
    object_class: Optional[str],
    force_cfg: dict,
    conf: float = 1.0,
    min_conf: float = 0.20,
    force_min_conf: float = 0.35,
) -> tuple[str, int]:
    cls = canonical_class(object_class)
    need = max(float(min_conf), float(force_min_conf))
    if conf < need:
        cls = "unknown"
    limits = force_cfg or {}
    value = int(limits.get(cls, limits.get("unknown", 650)))
    return cls, value
