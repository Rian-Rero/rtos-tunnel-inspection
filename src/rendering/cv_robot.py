"""Renderizador OpenCV do robô para o quadro sintético da câmera YOLO.

*OpenCVRobotRenderer* desenha o robô como visto por sua câmera apontada
para cima. São usadas apenas primitivas padrão do OpenCV; o chamador
fornece o quadro numpy.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass  # usado apenas para alias de tipo

__all__ = ["OpenCVRobotRenderer"]


class OpenCVRobotRenderer:
    """Renderiza o robô ATR em um quadro OpenCV 640×480.

    Todo o desenho usa os módulos *cv2* e *np* injetados na construção
    para evitar importá-los no carregamento do módulo, pois são
    dependências opcionais pesadas.
    """

    def __init__(self, cv2, np) -> None:
        self._cv2 = cv2
        self._np = np

    def render(
        self, frame, center_x: int = 320, body_top: int = 358, body_bot: int = 408
    ) -> None:
        cv2, np = self._cv2, self._np
        bx_c, bx_l, bx_r = center_x, center_x - 118, center_x + 118

        self._draw_shadow(cv2, frame, bx_c)
        self._draw_tracks(cv2, frame, bx_l, bx_r, body_bot)
        self._draw_body(cv2, frame, bx_l, bx_r, body_top, body_bot)
        self._draw_equipment_box(cv2, frame, bx_l, body_top)
        self._draw_antenna(cv2, frame, bx_l, body_top)
        self._draw_lidar(cv2, np, frame, bx_c, body_top)
        self._draw_camera_arm(cv2, frame, bx_r, body_top)

    # ── auxiliares privados ─────────────────────────────────────────────────

    @staticmethod
    def _draw_shadow(cv2, frame, bx_c):
        cv2.ellipse(frame, (bx_c, 450), (132, 9), 0, 0, 360, (12, 14, 18), -1)

    @staticmethod
    def _draw_tracks(cv2, frame, bx_l, bx_r, body_bot):
        cv2.rectangle(
            frame, (bx_l - 14, body_bot), (bx_r + 14, body_bot + 30), (22, 27, 33), -1
        )
        cv2.rectangle(
            frame, (bx_l - 14, body_bot), (bx_r + 14, body_bot + 30), (50, 62, 72), 1
        )
        for ti in range(0, 248, 12):
            tx = bx_l - 12 + ti
            cv2.line(frame, (tx, body_bot + 2), (tx, body_bot + 28), (14, 18, 22), 2)
        cv2.line(
            frame, (bx_l - 14, body_bot + 2), (bx_r + 14, body_bot + 2), (64, 78, 90), 1
        )
        for center, radius in (
            ((bx_l - 12, body_bot + 15), 16),
            ((bx_r + 12, body_bot + 15), 16),
        ):
            cv2.circle(frame, center, radius, (40, 48, 58), -1)
            cv2.circle(frame, center, radius, (76, 92, 106), 2)
        for rwi in range(1, 4):
            rwx = bx_l + int(236 * rwi / 4)
            cv2.circle(frame, (rwx, body_bot + 15), 10, (32, 38, 46), -1)
            cv2.circle(frame, (rwx, body_bot + 15), 10, (60, 72, 84), 1)

    @staticmethod
    def _draw_body(cv2, frame, bx_l, bx_r, body_top, body_bot):
        cv2.rectangle(frame, (bx_l, body_top), (bx_r, body_bot), (60, 78, 92), -1)
        cv2.rectangle(frame, (bx_l, body_top), (bx_r, body_bot), (98, 120, 138), 2)
        mid_y = (body_top + body_bot) // 2
        cv2.line(frame, (bx_l + 8, mid_y), (bx_r - 8, mid_y), (42, 58, 70), 1)

    @staticmethod
    def _draw_equipment_box(cv2, frame, bx_l, body_top):
        eq_x1, eq_y1, eq_x2, eq_y2 = bx_l + 8, body_top - 30, bx_l + 88, body_top
        cv2.rectangle(frame, (eq_x1, eq_y1), (eq_x2, eq_y2), (46, 62, 76), -1)
        cv2.rectangle(frame, (eq_x1, eq_y1), (eq_x2, eq_y2), (80, 100, 116), 1)
        for slot in range(5):
            sx = eq_x1 + 8 + slot * 13
            cv2.line(frame, (sx, eq_y1 + 6), (sx, eq_y1 + 20), (30, 44, 56), 3)

    @staticmethod
    def _draw_antenna(cv2, frame, bx_l, body_top):
        ax = bx_l + 30
        cv2.line(frame, (ax, body_top - 30), (ax, body_top - 78), (158, 178, 198), 2)
        cv2.circle(frame, (ax, body_top - 80), 5, (188, 208, 228), -1)
        cv2.circle(frame, (ax, body_top - 80), 4, (72, 148, 230), -1)

    @staticmethod
    def _draw_lidar(cv2, np, frame, bx_c, body_top):
        lx, ly, lr = bx_c + 22, body_top - 18, 20

        overlay = frame.copy()
        cone = np.array(
            [[(lx - 6, ly), (lx + 6, ly), (lx + 320, 4), (lx - 320, 4)]], dtype=np.int32
        )
        cv2.fillPoly(overlay, cone, (34, 140, 215))
        for b in range(15):
            ang = math.radians(-78.0 + b * (156.0 / 14))
            bx_e = int(lx + math.sin(ang) * 390)
            by_e = max(0, int(ly - math.cos(ang) * 390))
            cv2.line(overlay, (lx, ly), (bx_e, by_e), (72, 195, 255), 1)
        frame[:] = cv2.addWeighted(overlay, 0.30, frame, 0.70, 0)

        cv2.rectangle(
            frame, (lx - 18, body_top - 12), (lx + 18, body_top), (44, 58, 72), -1
        )
        cv2.rectangle(
            frame, (lx - 18, body_top - 12), (lx + 18, body_top), (80, 98, 114), 1
        )
        cv2.circle(frame, (lx, ly), lr + 4, (36, 48, 60), -1)
        cv2.circle(frame, (lx, ly), lr + 4, (68, 84, 100), 2)
        cv2.circle(frame, (lx, ly), lr, (16, 88, 160), -1)
        cv2.circle(frame, (lx, ly), lr, (46, 148, 238), 2)
        cv2.circle(frame, (lx - 6, ly - 6), 6, (138, 198, 250), -1)
        cv2.circle(frame, (lx - 6, ly - 6), 3, (210, 238, 255), -1)

    @staticmethod
    def _draw_camera_arm(cv2, frame, bx_r, body_top):
        cb_x, pt_y = bx_r - 26, body_top - 36
        at_x, at_y = cb_x + 38, pt_y - 8
        cv2.line(frame, (cb_x, body_top), (cb_x, pt_y), (118, 136, 154), 4)
        cv2.circle(frame, (cb_x, pt_y), 6, (70, 86, 102), -1)
        cv2.circle(frame, (cb_x, pt_y), 6, (114, 132, 150), 2)
        cv2.line(frame, (cb_x, pt_y), (at_x, at_y), (118, 136, 154), 4)
        cv2.rectangle(
            frame, (at_x - 6, at_y - 20), (at_x + 26, at_y + 4), (18, 24, 32), -1
        )
        cv2.rectangle(
            frame, (at_x - 6, at_y - 20), (at_x + 26, at_y + 4), (94, 112, 130), 1
        )
        cv2.circle(frame, (at_x + 9, at_y - 8), 9, (24, 94, 168), -1)
        cv2.circle(frame, (at_x + 9, at_y - 8), 9, (48, 142, 228), 2)
        cv2.circle(frame, (at_x + 5, at_y - 12), 3, (168, 210, 252), -1)
        cv2.circle(frame, (at_x + 22, at_y - 18), 4, (52, 211, 114), -1)
