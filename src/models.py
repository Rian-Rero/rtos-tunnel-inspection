"""Modelos de domínio compartilhados do sistema de inspeção ATR.

Fonte única para as estruturas de dados trocadas entre o núcleo RTOS em
C++ (via MQTT) e a camada de visualização em Python.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

__all__ = [
    "Direction",
    "OperationMode",
    "AnomalyKind",
    "parse_direction",
    "RobotTelemetry",
    "AnomalyMark",
    "YoloResult",
    "InspectionState",
]

## Direções normalizadas aceitas pela interface e pela telemetria.
Direction = Literal["LEFT", "STOP", "RIGHT"]
## Modos de operação aceitos pelo robô.
OperationMode = Literal["MANUAL", "AUTO"]
## Rótulos visuais de anomalia exibidos no simulador.
AnomalyKind = Literal["Buraco", "Saliencia"]

## Mapa de conversão entre direção numérica do C++ e rótulo textual.
_DIR_MAP: dict[int, Direction] = {-1: "LEFT", 0: "STOP", 1: "RIGHT"}
## Conjunto de direções textuais aceitas como entrada.
_VALID_DIRS: frozenset[str] = frozenset({"LEFT", "STOP", "RIGHT"})


def parse_direction(raw: object, fallback: Direction = "STOP") -> Direction:
    """Normaliza uma direção MQTT bruta (int ou string) para Direction."""
    if isinstance(raw, (int, float)):
        return _DIR_MAP.get(int(raw), fallback)
    candidate = str(raw).upper()
    return candidate if candidate in _VALID_DIRS else fallback  # type: ignore[return-value]


@dataclass
class RobotTelemetry:
    """Retrato completo do estado do robô publicado pelo núcleo C++."""

    ## Posição horizontal atual no túnel, em metros.
    pos_x: float = 0.0
    ## Distância acumulada reportada pela odometria, em metros.
    distance_m: float = 0.0
    ## Velocidade atual simulada do robô.
    velocidade: float = 0.0
    ## Setpoint efetivo de velocidade publicado pelo controle.
    speed_setpoint: int = 0
    ## Inclinação local medida pela IMU, em graus.
    imu: float = 0.0
    ## Distância vertical medida pelo LIDAR, em metros.
    lidar: float = 2.0
    ## Contagem simulada de pulsos do encoder.
    encoder: int = 0
    ## Modo de operação atual do robô.
    mode: OperationMode = "MANUAL"
    ## Direção textual usada pela visualização.
    direction: Direction = "STOP"
    ## Confiança da amostra de superfície.
    confidence_level: float = 0.0

    @classmethod
    def from_payload(
        cls,
        data: dict,
        previous: RobotTelemetry | None = None,
    ) -> RobotTelemetry:
        """Constrói a telemetria a partir de JSON MQTT, usando *previous* para chaves ausentes."""
        prev = previous or cls()
        raw_dir = data.get("direction", data.get("direction_label", prev.direction))
        return cls(
            pos_x=float(data.get("pos_x", prev.pos_x)),
            distance_m=float(data.get("distance_m", prev.distance_m)),
            velocidade=float(
                data.get("current_speed", data.get("velocidade", prev.velocidade))
            ),
            speed_setpoint=int(data.get("speed_setpoint", prev.speed_setpoint)),
            imu=float(data.get("imu", prev.imu)),
            lidar=float(data.get("lidar_distance_y", data.get("lidar", prev.lidar))),
            encoder=int(data.get("encoder", prev.encoder)),
            mode=str(data.get("mode", prev.mode)),  # type: ignore[arg-type]
            direction=parse_direction(raw_dir, prev.direction),
            confidence_level=float(data.get("confidence_level", prev.confidence_level)),
        )


@dataclass
class AnomalyMark:
    """Anomalia detectada em uma posição específica do túnel."""

    ## Posição horizontal em que a anomalia foi marcada.
    pos_x: float
    ## Leitura de LIDAR associada à anomalia.
    lidar: float
    ## Tipo visual da anomalia.
    kind: AnomalyKind


@dataclass
class YoloResult:
    """Resultado de inferência publicado pelo serviço de inspeção YOLO."""

    ## @var timestamp
    # Instante de geração do resultado.
    timestamp: float  ##< Instante de geração do resultado.
    ## @var anomalia_detectada
    # Indica se modelo ou simulação detectaram anomalia.
    anomalia_detectada: bool  ##< Indica se modelo ou simulação detectaram anomalia.
    ## @var confianca
    # Maior confiança retornada pela inferência.
    confianca: float  ##< Maior confiança retornada pela inferência.
    ## @var tipo
    # Rótulo textual do tipo detectado.
    tipo: str  ##< Rótulo textual do tipo detectado.
    ## Lista de detecções brutas retornadas pelo modelo.
    deteccoes: list[dict] = field(default_factory=list)
    ## Tipo de anomalia sintética desenhada no quadro de câmera.
    anomalia_visual_simulada: str = ""
    ## Origem do resultado, como modelo ou simulação.
    origem: str = ""

    def to_payload(self) -> dict:
        """Serializa o resultado para publicação em JSON via MQTT."""
        return {
            "timestamp": self.timestamp,
            "anomalia_detectada": self.anomalia_detectada,
            "confianca": self.confianca,
            "tipo": self.tipo,
            "deteccoes": self.deteccoes,
            "anomalia_visual_simulada": self.anomalia_visual_simulada,
            "origem": self.origem,
        }


@dataclass
class InspectionState:
    """Estado ao vivo de YOLO/inspeção consumido pela camada de visualização."""

    ## Indica se uma inspeção visual está em andamento.
    active: bool = False
    ## Mensagem textual exibida na interface sobre o estado do YOLO.
    yolo_state: str = "Aguardando inspeção..."
    ## Último tipo de anomalia informado pelo serviço visual.
    last_type: str = "Aguardando"
    ## Última confiança informada pelo serviço visual.
    last_confidence: float = 0.0
    ## Instante em que o resultado visual deve expirar na interface.
    result_expires_at: float | None = None
