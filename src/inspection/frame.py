"""Gerador de quadros sintéticos da câmera.

*SyntheticFrameGenerator* produz um quadro BGR 640×480 que simula o que
a câmera superior do robô veria: teto do túnel, defeito alternado e o
próprio robô na parte inferior da imagem.

A renderização é delegada para *OpenCVRobotRenderer* para manter o visual
do robô consistente com os outros backends.
"""

from __future__ import annotations

from typing import Literal

from rendering import OpenCVRobotRenderer

__all__ = ["SyntheticFrameGenerator", "AnomalyFrameType"]

AnomalyFrameType = Literal["fissura", "buraco", "saliencia"]


class SyntheticFrameGenerator:
    """Gera quadros sintéticos de inspeção usando primitivas do OpenCV.

    Os módulos ``cv2`` e ``np`` são injetados para evitar importá-los no
    carregamento do módulo, pois são dependências opcionais pesadas.
    """

    _FRAME_H = 480
    _FRAME_W = 640

    def __init__(self, cv2, np) -> None:
        self._cv2 = cv2
        self._np = np
        self._robot_renderer = OpenCVRobotRenderer(cv2, np)
        self._frame_index = 0

    def generate(self) -> tuple[object, AnomalyFrameType]:
        """Retorna ``(frame_ndarray, tipo_de_anomalia_simulada)``."""
        self._frame_index += 1
        frame = self._np.full(
            (self._FRAME_H, self._FRAME_W, 3), (24, 28, 34), dtype=self._np.uint8
        )
        self._draw_ceiling(frame)
        anomaly_type = self._draw_defect(frame)
        self._robot_renderer.render(frame)
        self._draw_hud(frame, anomaly_type)
        return frame, anomaly_type

    # ── auxiliares privados ─────────────────────────────────────────────────

    def _draw_ceiling(self, frame) -> None:
        cv2 = self._cv2
        for y in range(0, 180, 18):
            tone = 42 + (y % 36)
            cv2.line(frame, (0, y), (640, y + 28), (tone, tone, tone + 8), 3)
        cv2.rectangle(frame, (0, 0), (640, 138), (76, 78, 82), -1)
        cv2.line(frame, (0, 138), (640, 168), (36, 39, 44), 10)

    def _draw_defect(self, frame) -> AnomalyFrameType:
        cv2 = self._cv2
        phase = self._frame_index % 3
        if phase == 0:
            cv2.line(frame, (150, 74), (505, 108), (10, 10, 10), 9)
            cv2.line(frame, (155, 74), (500, 108), (92, 92, 96), 2)
            return "fissura"
        if phase == 1:
            cv2.ellipse(frame, (410, 82), (78, 28), 4, 0, 360, (28, 28, 30), -1)
            cv2.ellipse(frame, (410, 82), (78, 28), 4, 0, 360, (118, 118, 120), 3)
            return "buraco"
        cv2.circle(frame, (320, 78), 42, (128, 128, 126), -1)
        cv2.circle(frame, (320, 78), 44, (44, 44, 48), 4)
        return "saliencia"

    def _draw_hud(self, frame, anomaly_type: str) -> None:
        self._cv2.putText(
            frame,
            f"CAMERA ATR | {anomaly_type.upper()}",
            (32, 34),
            self._cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (235, 238, 244),
            2,
        )
