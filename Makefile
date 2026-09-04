.PHONY: help models camera gestures yolo sequence run calibrate motor check

PYTHON ?= python3

help:
	@echo "make models      download MediaPipe gesture weights"
	@echo "make camera      00 webcam"
	@echo "make gestures    01 Open_Palm / Closed_Fist"
	@echo "make yolo        02 YOLOE (first run downloads weights)"
	@echo "make sequence    03 vision + gestures, no motors"
	@echo "make run         full HUD (serial.mock in pc/config.yaml)"
	@echo "make calibrate   FSR ADC while ESP32 is plugged in"
	@echo "make motor       keyboard open/close over serial"
	@echo "make check       no-camera self-test"

models:
	$(PYTHON) pc/download_models.py

camera:
	$(PYTHON) pc/00_camera_test.py

gestures:
	$(PYTHON) pc/01_gesture_test.py

yolo:
	$(PYTHON) pc/02_yolo_test.py

sequence:
	$(PYTHON) pc/03_yolo_gesture_sequence.py

run:
	$(PYTHON) pc/main.py

calibrate:
	$(PYTHON) pc/calibrate_fsr.py

motor:
	$(PYTHON) pc/motor_test.py

check:
	$(PYTHON) pc/selftest.py
