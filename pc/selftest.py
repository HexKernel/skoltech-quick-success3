#!/usr/bin/env python3
"""No camera, no ESP32 — sanity-check force mapping and config."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from force_policy import canonical_class, fsr_limit
from util import load_config


def main() -> int:
    cfg = load_config()
    force = cfg["force"]
    assert canonical_class("quail egg") == "egg"
    assert canonical_class("kitchen sponge") == "sponge"
    assert canonical_class("rock") == "stone"
    assert canonical_class("banana") == "unknown"
    assert fsr_limit("egg", force) == ("egg", int(force["egg"]))
    assert fsr_limit(None, force) == ("unknown", int(force["unknown"]))
    assert fsr_limit("stone", force, conf=0.05, min_conf=0.20) == (
        "unknown",
        int(force["unknown"]),
    )
    assert cfg["serial"]["baud"] == 115200
    print("selftest ok")
    print(f"  mock={cfg['serial']['mock']}  port={cfg['serial']['port']}")
    print(f"  force egg={force['egg']} sponge={force['sponge']} stone={force['stone']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
