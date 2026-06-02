"""System-wide configuration constants for the ATR project.

All magic strings and tuneable values live here so that changing
a topic name or threshold never requires hunting through render code.
"""

from __future__ import annotations

__all__ = ["Topics", "MQTT_BROKER", "MQTT_PORT", "Limits"]

MQTT_BROKER: str = "localhost"
MQTT_PORT: int = 1883


class Topics:
    """MQTT topic namespace — never use raw strings outside this class."""

    # Upstream telemetry (C++ → Python)
    TELEMETRY_ROBOT: str = "telemetry/robot"
    TELEMETRY_YOLO: str = "telemetry/yolo"
    STATE_INSPECTION: str = "state/inspection"
    SENSOR_LIDAR: str = "sensor/lidar"
    SENSOR_IMU: str = "sensor/imu"
    SENSOR_ENCODER: str = "sensor/encoder"

    # Downstream commands (Python → C++)
    CMD_MODE: str = "cmd/mode"
    CMD_DIRECTION: str = "cmd/direction"
    CMD_SPEED: str = "cmd/speed_sp"
    CMD_CAMERA: str = "cmd/camera"


class Limits:
    """Application-wide numeric limits and thresholds."""

    ANOMALY_LIDAR_THRESHOLD: float = 0.35
    ANOMALY_MIN_SPACING_M: float = 0.18
    ROBOT_HISTORY_MAX: int = 360
    ANOMALY_MARKS_MAX: int = 48
    OPERATOR_HISTORY_MAX: int = 240
    YOLO_RESULT_TTL_S: float = 5.0
    SPEED_MIN: int = 0
    SPEED_MAX: int = 100
    SPEED_DEFAULT_MANUAL: int = 40
