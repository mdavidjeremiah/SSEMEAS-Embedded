"""Pretend to be the ESP32:  python simulate.py [server] [device_key]
Fills the tank, then empties it, posting a reading every 2 seconds."""
import math
import sys
import time

import httpx

server = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
key = sys.argv[2] if len(sys.argv) > 2 else "dev-device-key"

step = 0
while True:
    distance = 100 + 80 * math.cos(step / 12)       # swings between about 20 cm (full) and 180 cm (empty)
    reply = httpx.post(f"{server}/api/v1/readings", json={"distance_cm": round(distance, 1), "rssi": -60}, headers={"X-API-Key": key})
    print(round(distance), reply.status_code, reply.json())
    step += 1
    time.sleep(2)
