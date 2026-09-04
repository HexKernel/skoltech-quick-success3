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

Пока платы нет: `serial.mock: true` в `pc/config.yaml`.

## Плата (PlatformIO)

```bash
pio run -t upload
pio device monitor
```

Плата: **DOIT ESP32 DEVKIT V1**. Пины в `src/main.cpp`: FSR GPIO 34, Dynamixel DIR GPIO 4
(не GPIO 1 — это USB TX). `USE_DYNAMIXEL 0` пока нет `DynamixelSerial.zip`.

**12 V к Dynamixel — только после проверки организаторами.**

На ноутбуке: `serial.mock: false`, порт `auto` или `/dev/cu.SLAB_USBtoUART` / `COM3`.
Калибровка: `python pc/calibrate_fsr.py`.

## Протокол USB 115200

Ноутбук → ESP32: `OPEN` · `CLOSE 700` · `STOP` · `PING`

ESP32 → ноутбук: `FSR 512 CLOSING` · `ACK CLOSE 700` · `PONG`

`CLOSE <adc>` — закрывать, пока FSR < порога. Дальше `LIMIT` на МК.
