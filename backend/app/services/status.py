"""Pure functions: level calculation and Safe/Warning/Danger classification."""


def level_pct(distance_cm: float, depth_cm: float, sensor_offset_cm: float) -> float:
    """Distance is measured from the sensor down to the sewage surface, so a small distance means a full tank."""
    usable = depth_cm - sensor_offset_cm
    return max(0.0, min(100.0, (depth_cm - distance_cm) / usable * 100))


def classify(level: float, previous: str, warn: float, danger: float, hysteresis: float) -> str:
    """Hysteresis: once in a higher state, the level must fall `hysteresis` points below the threshold to step down.
    This stops alerts flapping when the surface ripples around a threshold."""
    if level >= danger or (previous == "danger" and level >= danger - hysteresis):
        return "danger"
    if level >= warn or (previous in ("warning", "danger") and level >= warn - hysteresis):
        return "warning"
    return "safe"
