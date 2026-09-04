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
    try:
        from serial.tools import list_ports

        scored: list[tuple[int, str]] = []
        for p in list_ports.comports():
            blob = f"{p.device} {p.description} {p.manufacturer or ''}".lower()
            score = 0
            if "cp210" in blob or "silicon" in blob or "slab" in blob:
                score = 3
            elif "ch340" in blob or "wch" in blob or "usb-serial" in blob:
                score = 2
            elif "gripper" in blob:
                score = 2
            elif "usb" in blob or "uart" in blob or "esp" in blob:
                score = 1
            if score:
                scored.append((score, p.device))
        if scored:
            scored.sort(reverse=True)
            return scored[0][1]
    except Exception:
        pass
    if sys.platform == "darwin":
        cands = (
            glob.glob("/dev/cu.GRIPPER*")
            + glob.glob("/dev/cu.SLAB_USBtoUART*")
            + glob.glob("/dev/cu.usbserial*")
            + glob.glob("/dev/cu.wchusbserial*")
            + glob.glob("/dev/cu.usbmodem*")
        )
        return cands[0] if cands else None
    if sys.platform.startswith("win"):
        return None
    cands = glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*")
    return cands[0] if cands else None


class SerialGripper:
    def __init__(self, port: str, baud: int = 115200, timeout: float = 0.05):
        import serial

        self.status = GripperStatus(connected=False)
        self._ser = serial.Serial(port, baud, timeout=timeout)
        time.sleep(2.0)  # ESP32 reset on open
        self._ser.reset_input_buffer()
        self.ping()
        for _ in range(25):
            self.pump()
            if self.status.connected:
                break
            time.sleep(0.04)
        self.status.connected = True  # port is open even if PONG was missed

    def close_port(self) -> None:
        try:
            self._ser.close()
        except Exception:
            pass
        self.status.connected = False

    def _send(self, line: str) -> None:
        try:
            self._ser.write((line.strip() + "\n").encode("ascii", errors="ignore"))
        except Exception as exc:
            print(f"serial write failed: {exc}")
            self.status.connected = False

    def pump(self) -> GripperStatus:
        try:
            while self._ser.in_waiting:
                raw = self._ser.readline().decode("ascii", errors="ignore").strip()
                if not raw:
                    continue
                self._parse(raw)
        except Exception as exc:
            print(f"serial read failed: {exc}")
            self.status.connected = False
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
        elif cmd == "ERR":
            print(f"esp32 {line}")

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
        self._open_t = 0

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
            self._open_t += 1
            if self.status.fsr <= 0 or self._open_t > 12:
                self.status.state = "IDLE"
                self._opening = False
            else:
                self.status.state = "OPENING"
        return self.status

    def open_gripper(self) -> None:
        self._opening = True
        self._closing = False
        self._open_t = 0
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


def connect(cfg: dict, fallback_mock: bool = True):
    serial_cfg = cfg.get("serial", {})
    if serial_cfg.get("mock", True):
        if not fallback_mock:
            raise SystemExit("serial.mock=true — set mock: false and plug in the ESP32")
        print("serial: MOCK (set serial.mock=false and serial.port when ESP32 is plugged in)")
        return MockGripper()
    port = serial_cfg.get("port", "auto")
    if not port or port == "auto":
        port = guess_port()
    if not port:
        if not fallback_mock:
            raise SystemExit("no serial port found")
        print("serial: no port found, falling back to MOCK")
        return MockGripper()
    print(f"serial: opening {port}")
    try:
        return SerialGripper(port, int(serial_cfg.get("baud", 115200)))
    except Exception as exc:
        if not fallback_mock:
            raise SystemExit(f"serial open failed: {exc}") from exc
        print(f"serial: open failed ({exc}), falling back to MOCK")
        return MockGripper()
