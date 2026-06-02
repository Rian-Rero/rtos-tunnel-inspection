"""Shared domain models for the ATR inspection system.

Single source of truth for all data structures exchanged between
the C++ RTOS core (via MQTT) and the Python visualisation layer.
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

Direction = Literal["LEFT", "STOP", "RIGHT"]
OperationMode = Literal["MANUAL", "AUTO"]
AnomalyKind = Literal["Buraco", "Saliencia"]

_DIR_MAP: dict[int, Direction] = {-1: "LEFT", 0: "STOP", 1: "RIGHT"}
_VALID_DIRS: frozenset[str] = frozenset({"LEFT", "STOP", "RIGHT"})


def parse_direction(raw: object, fallback: Direction = "STOP") -> Direction:
    """Normalise a raw MQTT direction value (int or string) to a Direction."""
    if isinstance(raw, (int, float)):
        return _DIR_MAP.get(int(raw), fallback)
    candidate = str(raw).upper()
    return candidate if candidate in _VALID_DIRS else fallback  # type: ignore[return-value]


@dataclass
class RobotTelemetry:
    """Complete snapshot of robot state as published by the C++ core."""

    pos_x: float = 0.0
    distance_m: float = 0.0
    velocidade: float = 0.0
    imu: float = 0.0
    lidar: float = 2.0
    encoder: int = 0
    mode: OperationMode = "MANUAL"
    direction: Direction = "STOP"
    confidence_level: float = 0.0

    @classmethod
    def from_payload(
        cls,
        data: dict,
        previous: RobotTelemetry | None = None,
    ) -> RobotTelemetry:
        """Construct from a raw MQTT JSON payload, falling back to *previous* for missing keys."""
        prev = previous or cls()
        raw_dir = data.get("direction", data.get("direction_label", prev.direction))
        return cls(
            pos_x=float(data.get("pos_x", prev.pos_x)),
            distance_m=float(data.get("distance_m", prev.distance_m)),
            velocidade=float(
                data.get("current_speed", data.get("velocidade", prev.velocidade))
            ),
            imu=float(data.get("imu", prev.imu)),
            lidar=float(data.get("lidar_distance_y", data.get("lidar", prev.lidar))),
            encoder=int(data.get("encoder", prev.encoder)),
            mode=str(data.get("mode", prev.mode)),  # type: ignore[arg-type]
            direction=parse_direction(raw_dir, prev.direction),
            confidence_level=float(data.get("confidence_level", prev.confidence_level)),
        )


@dataclass
class AnomalyMark:
    """A detected anomaly recorded at a specific tunnel position."""

    pos_x: float
    lidar: float
    kind: AnomalyKind


@dataclass
class YoloResult:
    """Inference result published by the YOLO inspection service."""

    timestamp: float
    anomalia_detectada: bool
    confianca: float
    tipo: str
    deteccoes: list[dict] = field(default_factory=list)
    anomalia_visual_simulada: str = ""
    origem: str = ""

    def to_payload(self) -> dict:
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
    """Live YOLO / inspection status consumed by the visualisation layer."""

    active: bool = False
    yolo_state: str = "Aguardando inspeção..."
    last_type: str = "Aguardando"
    last_confidence: float = 0.0
    result_expires_at: float | None = None
