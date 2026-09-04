#include <Arduino.h>

// The ESP32 DOIT DevKit V1 has an onboard LED wired to GPIO 2.
// It is also exposed as LED_BUILTIN in the ESP32 Arduino core.
const int LED_PIN = LED_BUILTIN;

// Blink timing in milliseconds.
const int ON_MS = 500;
const int OFF_MS = 500;

void setup() {
  pinMode(LED_PIN, OUTPUT);
}

void loop() {
  digitalWrite(LED_PIN, HIGH);  // LED on
  delay(ON_MS);                 // wait 500 ms
  digitalWrite(LED_PIN, LOW);   // LED off
  delay(OFF_MS);                // wait 500 ms
}