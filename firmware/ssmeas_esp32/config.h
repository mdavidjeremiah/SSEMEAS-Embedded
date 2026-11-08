// ===== Edit this file only. =====
#pragma once

// Wi-Fi (the ESP32 needs a 2.4 GHz network)
#define WIFI_SSID  "YOUR_WIFI_NAME"
#define WIFI_PASS  "YOUR_WIFI_PASSWORD"

// Backend. Use your computer's LAN address while testing; use https://your-domain once deployed.
#define SERVER_URL "http://192.168.1.50:8000"
#define USE_TLS    0                      // set to 1 when SERVER_URL starts with https://
#define DEVICE_KEY "dev-device-key"       // shown once when you add the tank on the dashboard's Admin page

// Tank. These must match the tank's settings in the Admin page, or the device lights and the dashboard will disagree.
#define DEPTH_CM   180.0f                 // sensor face to tank floor
#define OFFSET_CM  20.0f                  // sensor face to the "full" line
#define WARN_PCT   70.0f
#define DANGER_PCT 85.0f
#define HYST_PCT   3.0f

// Timing
#define SAMPLE_MS  10000UL                // one reading every 10 s (the backend marks the tank offline after 120 s of silence)

// Optional SMS on Danger through a SIM800L on Serial2
#define USE_GSM    0
#define SMS_TO     "+256700000000"
#define SMS_COOLDOWN_MS 3600000UL         // at most one SMS per hour

// Pins (check against your circuit)
#define PIN_TRIG   5
#define PIN_ECHO   18                     // ECHO needs a 1k/2k voltage divider: the HC-SR04 outputs 5 V
#define PIN_LED_G  25
#define PIN_LED_Y  26
#define PIN_LED_R  27
#define PIN_BUZZER 14                     // drives the buzzer's transistor
#define PIN_GSM_RX 16
#define PIN_GSM_TX 17
