/*
  SSMEAS ESP32 firmware: Smart Sewage Level Monitoring
  Reads the HC-SR04, runs the local alerts on its own, and reports to the FastAPI backend over Wi-Fi.
  Board: "ESP32 Dev Module" (Arduino IDE, esp32 board package). No extra libraries needed.
  Edit config.h, then upload. Open the Serial Monitor at 115200 baud to watch it work.
*/
#include "config.h"
#include "sensor.h"
#include "alerts.h"
#include "network.h"

unsigned long lastSampleAt = 0;
bool firstSample = true;

void setup() {
  Serial.begin(115200);
  sensorBegin();
  alertsBegin();
  networkBegin();
  applyState(STATE_SAFE, 0);
}

void loop() {
  networkKeepAlive();
  updateBuzzer();

  if (!firstSample && millis() - lastSampleAt < SAMPLE_MS) return;
  firstSample = false;
  lastSampleAt = millis();

  float distance = readDistanceCm();
  if (distance < 0) { Serial.println("Sensor read failed (check wiring)"); return; }

  float level = levelPercent(distance);
  Serial.printf("distance %.1f cm, level %.1f %%\n", distance, level);

  applyState(classify(level), level);   // local alerts first, so they never wait on the network
  reportReading(distance);
}
