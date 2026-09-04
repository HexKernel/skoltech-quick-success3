#!/usr/bin/env python3
"""Keyboard open/close without vision. o OPEN, c CLOSE, space STOP, q quit."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from serial_link import connect
from util import load_config


def main() -> None:
    cfg = load_config()
    grip = connect(cfg)
    unknown = int(cfg["force"]["unknown"])
    print("o=OPEN  c=CLOSE(unknown limit)  space=STOP  q=quit")
    print("type a letter and Enter if stdin, or use pc/main.py for a window")
    try:
        while True:
            grip.pump()
            line = sys.stdin.readline()
            if not line:
                break
            k = line.strip().lower()
            if k == "q":
                break
            if k == "o":
                grip.open_gripper()
                print("OPEN")
            elif k == "c":
                grip.close_gripper(unknown)
                print(f"CLOSE {unknown}")
            elif k == "s" or k == "":
                grip.stop()
                print("STOP")
            st = grip.pump()
            print(f"  FSR={st.fsr} {st.state}")
    finally:
        grip.close_port()


if __name__ == "__main__":
    main()
