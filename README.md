# QS Force-sensitive Robotic Gripper

Оператор говорит **когда** (жест), робот решает **насколько сильно**
(YOLOE → класс → потолок FSR). Стоп по силе — на ESP32.

Слайды: [QS Force-sensitive Robotic Gripper 2026](https://docs.google.com/presentation/d/1O3s7_5qUtafM29rLNgRNInMuGTlBbQwWCBPVWguKR5I/edit?usp=sharing)

```
камера ─┬─ YOLOE (egg / sponge / stone) ──┐
        └─ MediaPipe (palm / fist) ───────┼─ CLOSE <fsr_max> ─ USB ─ ESP32
                                          └─ OPEN / STOP           ├ Dynamixel AX-12A
                                                                   └ FSR (safety stop)
```

| Жест | Действие |
|---|---|
| Open_Palm | OPEN |
| Closed_Fist | CLOSE с порогом по классу объекта |
| клавиши `o` / `c` / пробел | запасной канал OPEN / CLOSE / STOP |

```
pc/                 ноутбук: камера, YOLOE, жесты, serial, HUD
src/main.cpp        ESP32 firmware (PlatformIO, DevKit V1)
platformio.ini      плата esp32doit-devkit-v1
models/             веса (не в git)
pc/config.yaml      камера, порт, пороги ADC
```

## Ноутбук

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python pc/download_models.py
python pc/selftest.py
python pc/00_camera_test.py
python pc/01_gesture_test.py
python pc/02_yolo_test.py
python pc/03_yolo_gesture_sequence.py
python pc/main.py
```

Клавиша **пробел = STOP** и держится, пока кулак не отпущен. Порог силы
защёлкивается на весь захват: яйцо не станет камнем посередине.

Пока платы нет: `serial.mock: true` в `pc/config.yaml`.

## Плата

Плата: **DOIT ESP32 DEVKIT V1**. USB от ПК питает ESP32. **12 V только на мотор.**
Bluetooth не обязателен: USB serial работает сразу. Если зрение уже крутится,
можно спарить Classic SPP **GRIPPER_TEST** (как в `test/sketches/bluetooth_test.ino`)
и слать те же строки `OPEN` / `CLOSE 700` / `STOP`. Прошивка слушает USB и BT сразу.

| Сигнал | GPIO | Куда |
|---|---|---|
| FSR ADC | **34** | 3.3V → FSR → GPIO34 → **47k** → GND (`fsr_test.ino`) |
| Dynamixel DIR | **21** | buffer DP, как в `dynamixel_move.ino` |
| Serial2 TX | **17** | buffer TX |
| Serial2 RX | **16** | buffer RX (дефолт Serial2) |
| Open / Close | **0 / 131** | как в стартовом скетче Яры |
| Speed | **400** | `moveSpeed` |

Библиотека мотора лежит в `lib/AX12A` (официальный `AX-12A-servo-library-master.zip`). Это **не** DynamixelSerial.

Прошивка интеграции: `src/main.cpp` (протокол `OPEN` / `CLOSE <adc>` / `STOP`).  
Проверка мотора без зрения: `test/sketches/dynamixel_move.ino`.  
Проверка FSR: `test/sketches/fsr_test.ino` (GPIO **34**). Порог в `fsr_motor_stop_test.ino` (`2000`) — заглушка, подставь число с монитора.

**12 V — после проверки схемы у Яры / организаторов.**

Ноутбук: `serial.mock: false`. Калибровка ADC: `python pc/calibrate_fsr.py`.

### Arduino IDE 2 (Linux)

1. Download **Arduino IDE 2 AppImage (Linux 64-bit)** from  
   https://www.arduino.cc/en/software  
   → “Linux AppImage 64 bits (X86-64)” → “Just Download”.

2. Install `libfuse2` if needed:

```bash
sudo apt update
sudo apt install libfuse2
```

3. Run:

```bash
cd ~/Downloads
chmod +x arduino-ide_*.AppImage
./arduino-ide_*.AppImage
```

(or double-click the AppImage after `chmod +x`).

Board manager (Windows / Mac / Linux) — follow  
[Installing the ESP32 Board in Arduino IDE](https://randomnerdtutorials.com/installing-the-esp32-board-in-arduino-ide-windows-instructions/):

1. **File → Preferences → Additional Board Manager URLs**, paste:

```
https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
```

2. **Tools → Board → Boards Manager…** → search **ESP32** → install **ESP32 by Espressif Systems**.
   Workshop slides ask for core **1.0.6** if that version is listed; otherwise install what Boards Manager offers and tell us the version.
3. **Tools → Board** → **DOIT ESP32 DEVKIT V1**. Upload speed 115200. USB: pick the CP2102/`COM`/`ttyUSB` port.

Then: **Sketch → Include Library → Add .ZIP Library** → `AX-12A-servo-library-master.zip` (or copy `lib/AX12A` into Arduino `libraries`).

Bring-up sketches: `test/sketches/dynamixel_move.ino`, `fsr_test.ino`, `fsr_motor_stop_test.ino`.

### PlatformIO (optional)

```bash
pio run -t upload
pio device monitor
```

## Протокол USB 115200

Ноутбук → ESP32: `OPEN` · `CLOSE 700` · `STOP` · `PING`

ESP32 → ноутбук: `FSR 512 CLOSING` · `ACK CLOSE 700` · `PONG`

`CLOSE <adc>` — закрывать, пока FSR < порога. Дальше `LIMIT` на МК.
