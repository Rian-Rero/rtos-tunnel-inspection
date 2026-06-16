"""Constantes de configuração globais do projeto ATR.

Todas as strings especiais e valores ajustáveis ficam aqui para que
alterar um tópico ou limiar não exija procurar no código de renderização.
"""

from __future__ import annotations

__all__ = ["Topics", "MQTT_BROKER", "MQTT_PORT", "MQTT_QOS", "Limits"]

## Endereço do broker MQTT usado pelos serviços Python.
MQTT_BROKER: str = "localhost"
## Porta TCP padrão do broker MQTT local.
MQTT_PORT: int = 1883
## Nível de qualidade de serviço usado em publicações e assinaturas MQTT.
MQTT_QOS: int = 2


class Topics:
    """Namespace de tópicos MQTT; evite strings cruas fora desta classe."""

    # Telemetria de entrada (C++ → Python)
    ## Telemetria agregada do robô publicada pelo coletor C++.
    TELEMETRY_ROBOT: str = "telemetry/robot"
    ## Resultado da inspeção visual publicado pelo serviço YOLO.
    TELEMETRY_YOLO: str = "telemetry/yolo"
    ## Estado binário que indica inspeção de câmera em andamento.
    STATE_INSPECTION: str = "state/inspection"
    ## Leitura bruta do LIDAR publicada pelo núcleo C++.
    SENSOR_LIDAR: str = "sensor/lidar"
    ## Leitura bruta da inclinação IMU publicada pelo núcleo C++.
    SENSOR_IMU: str = "sensor/imu"
    ## Contagem simulada de encoder publicada pelo núcleo C++.
    SENSOR_ENCODER: str = "sensor/encoder"

    # Comandos de saída (Python → C++)
    ## Comando de modo de operação manual ou automático.
    CMD_MODE: str = "cmd/mode"
    ## Comando de direção manual do carrinho.
    CMD_DIRECTION: str = "cmd/direction"
    ## Comando de setpoint de velocidade manual.
    CMD_SPEED: str = "cmd/speed_sp"
    ## Comando que solicita uma inspeção visual por câmera.
    CMD_CAMERA: str = "cmd/camera"


class Limits:
    """Limites numéricos e limiares usados por toda a aplicação."""

    ## Variação mínima de LIDAR, em metros, para marcar anomalia visual.
    ANOMALY_LIDAR_THRESHOLD: float = 0.35
    ## Espaçamento mínimo, em metros, entre marcadores visuais de anomalia.
    ANOMALY_MIN_SPACING_M: float = 0.18
    ## Quantidade máxima de amostras históricas do robô mantidas na GUI.
    ROBOT_HISTORY_MAX: int = 360
    ## Quantidade máxima de marcadores de anomalia exibidos no simulador.
    ANOMALY_MARKS_MAX: int = 48
    ## Quantidade máxima de amostras mantidas no painel do operador.
    OPERATOR_HISTORY_MAX: int = 240
    ## Tempo de vida, em segundos, do último resultado YOLO na interface.
    YOLO_RESULT_TTL_S: float = 5.0
    ## Velocidade manual mínima permitida pela interface.
    SPEED_MIN: int = 0
    ## Velocidade manual máxima permitida pela interface.
    SPEED_MAX: int = 100
    ## Velocidade manual inicial usada pela interface.
    SPEED_DEFAULT_MANUAL: int = 40
