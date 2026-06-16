"""Constantes de configuração globais do projeto ATR.

Todas as strings especiais e valores ajustáveis ficam aqui para que
alterar um tópico ou limiar não exija procurar no código de renderização.
"""

from __future__ import annotations

__all__ = ["Topics", "MQTT_BROKER", "MQTT_PORT", "MQTT_QOS", "Limits"]

MQTT_BROKER: str = "localhost"
MQTT_PORT: int = 1883
MQTT_QOS: int = 2


class Topics:
    """Namespace de tópicos MQTT; evite strings cruas fora desta classe."""

    # Telemetria de entrada (C++ → Python)
    TELEMETRY_ROBOT: str = "telemetry/robot"
    TELEMETRY_YOLO: str = "telemetry/yolo"
    STATE_INSPECTION: str = "state/inspection"
    SENSOR_LIDAR: str = "sensor/lidar"
    SENSOR_IMU: str = "sensor/imu"
    SENSOR_ENCODER: str = "sensor/encoder"

    # Comandos de saída (Python → C++)
    CMD_MODE: str = "cmd/mode"
    CMD_DIRECTION: str = "cmd/direction"
    CMD_SPEED: str = "cmd/speed_sp"
    CMD_CAMERA: str = "cmd/camera"


class Limits:
    """Limites numéricos e limiares usados por toda a aplicação."""

    ANOMALY_LIDAR_THRESHOLD: float = 0.35
    ANOMALY_MIN_SPACING_M: float = 0.18
    ROBOT_HISTORY_MAX: int = 360
    ANOMALY_MARKS_MAX: int = 48
    OPERATOR_HISTORY_MAX: int = 240
    YOLO_RESULT_TTL_S: float = 5.0
    SPEED_MIN: int = 0
    SPEED_MAX: int = 100
    SPEED_DEFAULT_MANUAL: int = 40
