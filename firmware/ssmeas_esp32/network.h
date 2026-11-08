// Wi-Fi, sending readings to the backend, and buffering them while offline.
#pragma once
#include <Arduino.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <time.h>
#include "config.h"

struct PendingReading { float distanceCm; uint64_t timestampMs; };
const int MAX_PENDING = 120;                    // about 20 minutes of readings at 10 s
PendingReading pending[MAX_PENDING];
int pendingCount = 0;
unsigned long lastWifiAttempt = 0;

inline void networkBegin() {
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("Connecting to Wi-Fi");
  for (int i = 0; i < 40 && WiFi.status() != WL_CONNECTED; i++) { delay(500); Serial.print("."); }
  if (WiFi.status() == WL_CONNECTED)
    Serial.printf("\nConnected, IP %s, signal %d dBm\n", WiFi.localIP().toString().c_str(), WiFi.RSSI());
  else
    Serial.println("\nNo Wi-Fi yet. Local alerts still work; will keep retrying.");
  configTime(0, 0, "pool.ntp.org", "time.google.com");   // a clock, for timestamps on buffered readings
}

// Call every loop: retries the connection every 15 s if it dropped.
inline void networkKeepAlive() {
  if (WiFi.status() != WL_CONNECTED && millis() - lastWifiAttempt > 15000) {
    lastWifiAttempt = millis();
    WiFi.disconnect();
    WiFi.begin(WIFI_SSID, WIFI_PASS);
  }
}

inline bool clockReady() { return time(nullptr) > 1700000000; }
inline uint64_t nowMs() { return (uint64_t)time(nullptr) * 1000ULL; }

// POST a JSON body with the device key. Returns true on 2xx.
inline bool postJson(const char* path, const String& body) {
#if USE_TLS
  WiFiClientSecure client;
  client.setInsecure();                         // testing only. For production use client.setCACert(rootCertificate)
#else
  WiFiClient client;
#endif
  HTTPClient http;
  if (!http.begin(client, String(SERVER_URL) + path)) return false;
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-Key", DEVICE_KEY);
  http.setTimeout(5000);
  int code = http.POST(body);
  Serial.printf("POST %s -> %d\n", path, code);  // 201 stored, -1 cannot reach server, 401 wrong key, 429 too fast
  http.end();
  return code >= 200 && code < 300;
}

// Upload readings saved during an outage, 40 at a time, oldest first.
inline void flushPending() {
  while (pendingCount > 0) {
    int n = pendingCount < 40 ? pendingCount : 40;
    String body = "[";
    for (int i = 0; i < n; i++) {
      char item[96];
      snprintf(item, sizeof item, "%s{\"distance_cm\":%.1f,\"ts\":%llu}", i ? "," : "", pending[i].distanceCm, (unsigned long long)pending[i].timestampMs);
      body += item;
    }
    body += "]";
    if (!postJson("/api/v1/readings/batch", body)) return;     // try again next cycle
    memmove(pending, pending + n, (pendingCount - n) * sizeof(PendingReading));
    pendingCount -= n;
  }
}

// Send one reading now; if that fails, keep it for later.
inline void reportReading(float distanceCm) {
  if (WiFi.status() == WL_CONNECTED) {
    if (pendingCount) flushPending();
    char body[64];
    snprintf(body, sizeof body, "{\"distance_cm\":%.1f,\"rssi\":%d}", distanceCm, WiFi.RSSI());
    if (postJson("/api/v1/readings", body)) return;
  }
  if (clockReady() && pendingCount < MAX_PENDING) pending[pendingCount++] = { distanceCm, nowMs() };
}
