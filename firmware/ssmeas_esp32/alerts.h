// Local alerts: LEDs, buzzer and optional SMS. These never wait on Wi-Fi.
#pragma once
#include <Arduino.h>
#include "config.h"

enum TankState { STATE_SAFE, STATE_WARNING, STATE_DANGER };

TankState currentState = STATE_SAFE;
unsigned long lastSmsAt = 0;

inline void alertsBegin() {
  pinMode(PIN_LED_G, OUTPUT); pinMode(PIN_LED_Y, OUTPUT); pinMode(PIN_LED_R, OUTPUT); pinMode(PIN_BUZZER, OUTPUT);
#if USE_GSM
  Serial2.begin(9600, SERIAL_8N1, PIN_GSM_RX, PIN_GSM_TX);
#endif
  digitalWrite(PIN_LED_G, HIGH); digitalWrite(PIN_LED_Y, HIGH); digitalWrite(PIN_LED_R, HIGH);   // lamp test
  delay(600);
}

// Same hysteresis rule as the backend: stepping down needs the level to fall HYST_PCT below the threshold.
inline TankState classify(float level) {
  if (level >= DANGER_PCT || (currentState == STATE_DANGER && level >= DANGER_PCT - HYST_PCT)) return STATE_DANGER;
  if (level >= WARN_PCT || (currentState != STATE_SAFE && level >= WARN_PCT - HYST_PCT)) return STATE_WARNING;
  return STATE_SAFE;
}

inline void sendSms(const String& text) {
#if USE_GSM
  Serial2.println("AT+CMGF=1");  delay(500);                      // text mode
  Serial2.print("AT+CMGS=\""); Serial2.print(SMS_TO); Serial2.println("\"");  delay(500);
  Serial2.print(text);
  Serial2.write(26);                                              // Ctrl+Z ends the message
  delay(3000);
#endif
}

inline void applyState(TankState next, float level) {
  digitalWrite(PIN_LED_G, next == STATE_SAFE);
  digitalWrite(PIN_LED_Y, next == STATE_WARNING);
  digitalWrite(PIN_LED_R, next == STATE_DANGER);
  bool enteredDanger = next == STATE_DANGER && currentState != STATE_DANGER;
  if (enteredDanger && (lastSmsAt == 0 || millis() - lastSmsAt > SMS_COOLDOWN_MS)) {
    sendSms("SSMEAS DANGER: sewage tank at " + String((int)level) + "%. Please arrange emptying.");
    lastSmsAt = millis();
  }
  currentState = next;
}

// Call every loop: beeps (half a second on, half off) while in Danger, without blocking.
inline void updateBuzzer() {
  digitalWrite(PIN_BUZZER, currentState == STATE_DANGER ? (millis() / 500) % 2 : LOW);
}
