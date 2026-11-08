// HC-SR04 ultrasonic sensor and the level calculation.
#pragma once
#include <Arduino.h>
#include "config.h"

inline void sensorBegin() {
  pinMode(PIN_TRIG, OUTPUT);
  pinMode(PIN_ECHO, INPUT);
}

// One ping. Returns the distance in cm, or -1 if no echo came back.
inline float pingOnce() {
  digitalWrite(PIN_TRIG, LOW);  delayMicroseconds(2);
  digitalWrite(PIN_TRIG, HIGH); delayMicroseconds(10);
  digitalWrite(PIN_TRIG, LOW);
  unsigned long echoMicros = pulseIn(PIN_ECHO, HIGH, 30000);   // 30 ms timeout is about 5 m
  if (echoMicros == 0) return -1;
  return echoMicros * 0.0343f / 2.0f;                          // distance = time x speed of sound / 2
}

// Median of 5 pings: ignores ripples and stray echoes. Returns -1 if fewer than 3 good readings.
inline float readDistanceCm() {
  float good[5];
  int count = 0;
  for (int i = 0; i < 5; i++) {
    float d = pingOnce();
    if (d >= 2 && d <= 400) good[count++] = d;                 // the sensor's valid range
    delay(60);
  }
  if (count < 3) return -1;
  for (int i = 1; i < count; i++)                               // tiny insertion sort
    for (int j = i; j > 0 && good[j] < good[j - 1]; j--) { float t = good[j]; good[j] = good[j - 1]; good[j - 1] = t; }
  return good[count / 2];
}

// A small distance means a full tank.
inline float levelPercent(float distanceCm) {
  float pct = (DEPTH_CM - distanceCm) / (DEPTH_CM - OFFSET_CM) * 100.0f;
  return pct < 0 ? 0 : (pct > 100 ? 100 : pct);
}
