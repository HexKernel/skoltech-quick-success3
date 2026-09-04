/*
  QS Force-sensitive gripper — ESP32 DevKit V1
  AX-12A on Serial2. Laptop commands on USB Serial and Bluetooth SPP.

  BT name: GRIPPER_TEST  (same as bluetooth_test.ino)
  USB 115200 still works without pairing.

  Pins (Yara fsr_test / dynamixel_move):
    FSR        GPIO 34   3.3V → FSR → GPIO34 → 47k → GND
    Direction  GPIO 21
    Serial2 TX GPIO 17
    Serial2 RX GPIO 16
*/

#include <Arduino.h>
#include <AX12A.h>
#include <BluetoothSerial.h>

#if !defined(CONFIG_BT_ENABLED) || !defined(CONFIG_BLUEDROID_ENABLED)
#error Bluetooth is not enabled in this ESP32 core
#endif

#define BT_NAME          "GRIPPER_TEST"
#define FSR_PIN          34
#define DXL_DIR_PIN      21
#define DXL_BAUD         1000000ul
#define DXL_ID           1
#define POS_OPEN         0
#define POS_CLOSE        131
#define MOVE_SPEED       400
#define HOLD_SPEED       80
#define FSR_DEFAULT_MAX  650
#define REPORT_MS        40
#define OPEN_MS          400
#define CLOSE_TIMEOUT_MS 4000
#define FSR_HITS         2
#define LINE_MAX         64

BluetoothSerial SerialBT;

enum State { ST_IDLE, ST_OPENING, ST_CLOSING, ST_HOLDING, ST_LIMIT, ST_FAULT };

State state = ST_IDLE;
int fsrMax = FSR_DEFAULT_MAX;
int lastFsr = 0;
uint8_t overHits = 0;
uint32_t lastReport = 0;
uint32_t moveStarted = 0;
char usbBuf[LINE_MAX];
uint8_t usbLen = 0;
char btBuf[LINE_MAX];
uint8_t btLen = 0;

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

void reply(const String& line) {
  Serial.println(line);
  SerialBT.println(line);
}

int readFsr() {
  long acc = 0;
  for (int i = 0; i < 8; i++) {
    acc += analogRead(FSR_PIN);
    delayMicroseconds(200);
  }
  return (int)(acc / 8);
}

void motorMove(int pos) {
  ax12a.moveSpeed(DXL_ID, pos, MOVE_SPEED);
}

void motorHoldHere() {
  int here = ax12a.readPosition(DXL_ID);
  if (here < 0) {
    ax12a.moveSpeed(DXL_ID, POS_OPEN, MOVE_SPEED);
    state = ST_FAULT;
    return;
  }
  ax12a.moveSpeed(DXL_ID, here, HOLD_SPEED);
}

void doOpen() {
  state = ST_OPENING;
  fsrMax = FSR_DEFAULT_MAX;
  overHits = 0;
  moveStarted = millis();
  motorMove(POS_OPEN);
  reply("ACK OPEN");
}

void doClose(int maxAdc) {
  fsrMax = constrain(maxAdc, 50, 4095);
  lastFsr = readFsr();
  overHits = 0;
  moveStarted = millis();
  if (lastFsr >= fsrMax) {
    motorHoldHere();
    if (state != ST_FAULT) state = ST_LIMIT;
    reply(String("ACK CLOSE ") + fsrMax);
    return;
  }
  state = ST_CLOSING;
  motorMove(POS_CLOSE);
  reply(String("ACK CLOSE ") + fsrMax);
}

void doStop() {
  motorHoldHere();
  if (state != ST_FAULT) state = ST_IDLE;
  overHits = 0;
  reply("ACK STOP");
}

void handleLine(const char* raw) {
  String line = String(raw);
  line.trim();
  if (line.length() == 0) return;
  line.toUpperCase();
  if (line == "PING") {
    reply("PONG");
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
    if (sp < 0) {
      reply("ERR CLOSE needs adc");
      return;
    }
    int mx = line.substring(sp + 1).toInt();
    if (mx < 50) {
      reply("ERR CLOSE adc");
      return;
    }
    doClose(mx);
    return;
  }
  reply(String("ERR unknown ") + line);
}

void feed(char c, char* buf, uint8_t* len) {
  if (c == '\r') return;
  if (c == '\n') {
    buf[*len] = 0;
    *len = 0;
    handleLine(buf);
    return;
  }
  if (*len < LINE_MAX - 1) buf[(*len)++] = c;
  else *len = 0;
}

void pollLinks() {
  while (Serial.available()) feed((char)Serial.read(), usbBuf, &usbLen);
  while (SerialBT.available()) feed((char)SerialBT.read(), btBuf, &btLen);
}

void setup() {
  Serial.begin(115200);
  pinMode(FSR_PIN, INPUT);
#if defined(ADC_11db)
  analogSetPinAttenuation(FSR_PIN, ADC_11db);
#endif
#if defined(ESP32)
  analogReadResolution(12);
#endif
  SerialBT.begin(BT_NAME);
  delay(1000);
  ax12a.begin(DXL_BAUD, DXL_DIR_PIN, &Serial2);
  ax12a.setEndless(DXL_ID, OFF);
  reply("PONG");
  reply("FSR 0 IDLE");
}

void loop() {
  lastFsr = readFsr();

  if (state == ST_CLOSING) {
    if (lastFsr >= fsrMax) overHits++;
    else if (overHits > 0) overHits--;
    if (overHits >= FSR_HITS) {
      motorHoldHere();
      if (state != ST_FAULT) state = ST_LIMIT;
    }
    int pos = ax12a.readPosition(DXL_ID);
    if (state == ST_CLOSING && pos >= 0 && abs(pos - POS_CLOSE) < 8) {
      motorHoldHere();
      if (state != ST_FAULT) state = ST_HOLDING;
    }
    if (state == ST_CLOSING && (millis() - moveStarted) > CLOSE_TIMEOUT_MS) {
      motorHoldHere();
      if (state != ST_FAULT) state = (overHits > 0) ? ST_LIMIT : ST_HOLDING;
    }
  }

  if (state == ST_OPENING) {
    int pos = ax12a.readPosition(DXL_ID);
    if (pos >= 0 && abs(pos - POS_OPEN) < 8) state = ST_IDLE;
    else if ((millis() - moveStarted) > OPEN_MS) state = ST_IDLE;
  }

  pollLinks();

  uint32_t now = millis();
  if (now - lastReport >= REPORT_MS) {
    lastReport = now;
    reply(String("FSR ") + lastFsr + " " + stateName(state));
  }
}
