"""Line protocol with the ESP32 gripper.

PC → ESP32
  OPEN
  CLOSE <fsr_max>
  STOP
  PING

ESP32 → PC
  FSR <adc> <STATE>
  ACK OPEN
  ACK CLOSE <fsr_max>
  PONG
  ERR <msg>

STATE: IDLE | OPENING | CLOSING | HOLDING | LIMIT | FAULT
"""
from __future__ import annotations

import glob
import sys
import time
from dataclasses import dataclass
from typing import Optional


STATES = ("IDLE", "OPENING", "CLOSING", "HOLDING", "LIMIT", "FAULT")


@dataclass
class GripperStatus:
    fsr: int = 0
    state: str = "IDLE"
    last_line: str = ""
    connected: bool = False


def guess_port() -> Optional[str]:
    # ESP32 DevKit V1 typically uses a CP2102 USB-UART.
    if sys.platform == "darwin":
        cands = (
            glob.glob("/dev/cu.SLAB_USBtoUART*")
            + glob.glob("/dev/cu.usbserial*")
            + glob.glob("/dev/cu.wchusbserial*")
            + glob.glob("/dev/cu.usbmodem*")
        )
    elif sys.platform.startswith("win"):
        return "COM3"
    else:
        cands = glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*")
    return cands[0] if cands else None


class SerialGripper:
    def __init__(self, port: str, baud: int = 115200, timeout: float = 0.05):
        import serial

        self.status = GripperStatus(connected=True)
        self._ser = serial.Serial(port, baud, timeout=timeout)
        time.sleep(2.0)  # ESP32 reset on open
        self._ser.reset_input_buffer()
        self.ping()

    def close_port(self) -> None:
        try:
            self._ser.close()
        except Exception:
            pass
        self.status.connected = False

    def _send(self, line: str) -> None:
        self._ser.write((line.strip() + "\n").encode("ascii", errors="ignore"))

    def pump(self) -> GripperStatus:
        while self._ser.in_waiting:
            raw = self._ser.readline().decode("ascii", errors="ignore").strip()
            if not raw:
                continue
            self._parse(raw)
        return self.status

    def _parse(self, line: str) -> None:
        self.status.last_line = line
        parts = line.split()
        if not parts:
            return
        cmd = parts[0].upper()
        if cmd == "FSR" and len(parts) >= 3:
            try:
                self.status.fsr = int(parts[1])
            except ValueError:
                return
            st = parts[2].upper()
            if st in STATES:
                self.status.state = st
        elif cmd == "PONG":
            self.status.connected = True

    def open_gripper(self) -> None:
        self._send("OPEN")

    def close_gripper(self, fsr_max: int) -> None:
        self._send(f"CLOSE {int(fsr_max)}")

    def stop(self) -> None:
        self._send("STOP")

    def ping(self) -> None:
        self._send("PING")


class MockGripper:
    """No hardware: FSR ramps while closing so the HUD can be demoed."""

    def __init__(self):
        self.status = GripperStatus(connected=False, state="IDLE")
        self._max = 1000
        self._closing = False
        self._opening = False

    def close_port(self) -> None:
        return

    def pump(self) -> GripperStatus:
        if self._closing:
            self.status.fsr = min(self._max, self.status.fsr + 35)
            if self.status.fsr >= self._max:
                self.status.state = "LIMIT"
                self._closing = False
            else:
                self.status.state = "CLOSING"
        elif self._opening:
            self.status.fsr = max(0, self.status.fsr - 50)
            if self.status.fsr <= 0:
                self.status.state = "IDLE"
                self._opening = False
            else:
                self.status.state = "OPENING"
        return self.status

    def open_gripper(self) -> None:
        self._opening = True
        self._closing = False
        self.status.state = "OPENING"

    def close_gripper(self, fsr_max: int) -> None:
        self._max = int(fsr_max)
        self._closing = True
        self._opening = False
        self.status.state = "CLOSING"

    def stop(self) -> None:
        self._closing = False
        self._opening = False
        self.status.state = "IDLE"

    def ping(self) -> None:
        return


def connect(cfg: dict):
    serial_cfg = cfg.get("serial", {})
    if serial_cfg.get("mock", True):
        print("serial: MOCK (set serial.mock=false and serial.port when ESP32 is plugged in)")
        return MockGripper()
    port = serial_cfg.get("port", "auto")
    if not port or port == "auto":
        port = guess_port()
    if not port:
        print("serial: no port found, falling back to MOCK")
        return MockGripper()
    print(f"serial: opening {port}")
    return SerialGripper(port, int(serial_cfg.get("baud", 115200)))
