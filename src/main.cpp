/*
  QS Force-sensitive gripper — ESP32 DevKit V1 (PlatformIO)
  Safety stop lives HERE, not on the laptop.

  Do NOT use GPIO 1 / 3 (USB Serial) or 6–11 (flash).
  FSR must be ADC1 input-only: 32, 33, 34, 35, 36, 39.
  DIR must be an output pin: 4, 5, 18, 19, 21, 22, 23.

  Line protocol (115200 8N1, newline):
    PC → OPEN | CLOSE <fsr_max> | STOP | PING
    ESP → FSR <adc> <STATE> | ACK ... | PONG | ERR ...

  STATE: IDLE OPENING CLOSING HOLDING LIMIT FAULT
*/

#include <Arduino.h>

#define FSR_PIN         34
#define DXL_DIR_PIN     4
#define DXL_BAUD        1000000
#define DXL_ID          1
#define POS_OPEN        200
#define POS_CLOSE       820
#define MOVE_SPEED      80
#define FSR_DEFAULT_MAX 800
#define REPORT_MS       40
#define USE_DYNAMIXEL   0

#if USE_DYNAMIXEL
#include <DynamixelSerial.h>
#endif

enum State { ST_IDLE, ST_OPENING, ST_CLOSING, ST_HOLDING, ST_LIMIT, ST_FAULT };

State state = ST_IDLE;
int fsrMax = FSR_DEFAULT_MAX;
int lastFsr = 0;
uint32_t lastReport = 0;

const char* stateName(State s) {
  switch (s) {
    case ST_OPENING: return "OPENING";
    case ST_CLOSING: return "CLOSING";
    case ST_HOLDING: return "HOLDING";
    case ST_LIMIT:   return "LIMIT";
    case ST_FAULT:   return "FAULT";
    default:         return "IDLE";
  }
}

int readFsr() {
  long acc = 0;
  for (int i = 0; i < 4; i++) acc += analogRead(FSR_PIN);
  return (int)(acc / 4);
}

void motorMove(int pos) {
#if USE_DYNAMIXEL
  Dynamixel.moveSpeed(DXL_ID, pos, MOVE_SPEED);
#else
  (void)pos;
#endif
}

void motorHoldHere() {
#if USE_DYNAMIXEL
  int here = Dynamixel.readPosition(DXL_ID);
  if (here < 0) here = (POS_OPEN + POS_CLOSE) / 2;
  Dynamixel.moveSpeed(DXL_ID, here, 0);
#endif
}

void doOpen() {
  state = ST_OPENING;
  fsrMax = FSR_DEFAULT_MAX;
  motorMove(POS_OPEN);
  Serial.println("ACK OPEN");
}

void doClose(int maxAdc) {
  fsrMax = constrain(maxAdc, 50, 4095);
  lastFsr = readFsr();
  if (lastFsr >= fsrMax) {
    motorHoldHere();
    state = ST_LIMIT;
    Serial.print("ACK CLOSE ");
    Serial.println(fsrMax);
    return;
  }
  state = ST_CLOSING;
  motorMove(POS_CLOSE);
  Serial.print("ACK CLOSE ");
  Serial.println(fsrMax);
}

void doStop() {
  motorHoldHere();
  state = ST_IDLE;
  Serial.println("ACK STOP");
}

void handleLine(String line) {
  line.trim();
  if (line.length() == 0) return;
  line.toUpperCase();
  if (line == "PING") {
    Serial.println("PONG");
    return;
  }
  if (line == "OPEN") {
    doOpen();
    return;
  }
  if (line == "STOP") {
    doStop();
    return;
  }
  if (line.startsWith("CLOSE")) {
    int sp = line.indexOf(' ');
    int mx = FSR_DEFAULT_MAX;
    if (sp > 0) mx = line.substring(sp + 1).toInt();
    doClose(mx);
    return;
  }
  Serial.print("ERR unknown ");
  Serial.println(line);
}

void setup() {
  Serial.begin(115200);
  Serial.setTimeout(30);
  pinMode(FSR_PIN, INPUT);
#if USE_DYNAMIXEL
  Dynamixel.begin(DXL_BAUD, DXL_DIR_PIN);
#endif
  delay(200);
  Serial.println("PONG");
  Serial.println("FSR 0 IDLE");
}

void loop() {
  while (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    handleLine(line);
  }

  lastFsr = readFsr();

  if (state == ST_CLOSING && lastFsr >= fsrMax) {
    motorHoldHere();
    state = ST_LIMIT;
  }

  if (state == ST_OPENING) {
#if USE_DYNAMIXEL
    int pos = Dynamixel.readPosition(DXL_ID);
    if (pos >= 0 && abs(pos - POS_OPEN) < 15) state = ST_IDLE;
#else
    state = ST_IDLE;
#endif
  }

  uint32_t now = millis();
  if (now - lastReport >= REPORT_MS) {
    lastReport = now;
    Serial.print("FSR ");
    Serial.print(lastFsr);
    Serial.print(' ');
    Serial.println(stateName(state));
  }
}
