EVENT_LABELS = {
    "warning": "Warning",
    "danger": "Danger",
    "recovery": "Back to Safe",
    "offline": "Device offline",
}

DEFAULT_PREFS = {
    "warning": True,
    "danger": True,
    "recovery": True,
    "offline": False,
    "quiet_on": False,   # mute Warning messages overnight (Danger is never muted)
    "quiet_from": 22,
    "quiet_to": 6,
}

# Valid range of the HC-SR04 ultrasonic sensor, in centimetres.
SENSOR_MIN_CM, SENSOR_MAX_CM = 2, 400
