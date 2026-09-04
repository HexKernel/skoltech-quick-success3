#!/usr/bin/env python3
"""Print FSR ADC from the ESP32 so you can set force.egg / sponge / stone."""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from serial_link import connect
from util import load_config


def main() -> None:
    cfg = load_config()
    cfg.setdefault("serial", {})["mock"] = False
    grip = connect(cfg)
    print("squeeze the FSR — Ctrl+C to stop")
    try:
        while True:
            st = grip.pump()
            print(f"\rFSR {st.fsr:4d}  {st.state:8s}  {st.last_line:20s}", end="", flush=True)
            time.sleep(0.05)
    except KeyboardInterrupt:
        print()
    finally:
        grip.close_port()


if __name__ == "__main__":
    main()
