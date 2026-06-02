"""Auxiliares puros de terreno e transformação de coordenadas.

Todas as funções aqui são puras, sem efeitos colaterais e sem dependência
do Pygame. Elas são compartilhadas entre os renderizadores da cena e do
robô.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

__all__ = [
    "floor_elevation",
    "floor_slope",
    "local_imu",
    "slope_label",
    "slope_color_rgb",
    "slope_color_hex",
    "ViewTransform",
]


def floor_elevation(world_x: float) -> float:
    """Altura senoidal do piso usada pela simulação física."""
    return 0.62 * math.sin(world_x / 5.4) + 0.16 * math.sin(world_x / 1.8)


def floor_slope(world_x: float) -> float:
    """Primeira derivada de *floor_elevation*."""
    return (0.62 / 5.4) * math.cos(world_x / 5.4) + (0.16 / 1.8) * math.cos(
        world_x / 1.8
    )


def local_imu(world_x: float) -> float:
    """Ângulo IMU simulado, em graus, na posição *world_x*."""
    return math.degrees(math.atan(floor_slope(world_x)))


def slope_label(angle: float) -> str:
    if angle > 0.4:
        return "SUBIDA"
    if angle < -0.4:
        return "DESCIDA"
    return "PLANO"


def slope_color_rgb(angle: float) -> tuple[int, int, int]:
    if angle > 0.4:
        return (250, 204, 21)
    if angle < -0.4:
        return (96, 165, 250)
    return (148, 163, 184)


def slope_color_hex(angle: float) -> str:
    r, g, b = slope_color_rgb(angle)
    return f"#{r:02x}{g:02x}{b:02x}"


@dataclass
class ViewTransform:
    """Mapeamento bidirecional entre coordenadas do mundo (metros) e pixels
    de tela. Atualizado uma vez por quadro em *update()*.
    """

    view_start_m: float = 0.0
    view_scale: float = 60.0
    view_left_px: float = 70.0
    floor_vertical_scale: float = 118.0

    def update(self, visual_pos_x: float, screen_width: int) -> None:
        """Recalcula a janela de visão para manter o robô centralizado."""
        view_width_m = 18.0
        self.view_left_px = 70.0
        robot_center_px = screen_width / 2.0
        self.view_scale = (screen_width - 140) / view_width_m
        center_offset_m = (robot_center_px - self.view_left_px) / self.view_scale
        self.view_start_m = visual_pos_x - center_offset_m

    @property
    def view_end_m(self) -> float:
        return self.view_start_m + 18.0

    def screen_x(self, world_x: float) -> int:
        return int(self.view_left_px + (world_x - self.view_start_m) * self.view_scale)

    def world_x(self, screen_x: int) -> float:
        return self.view_start_m + (screen_x - self.view_left_px) / max(
            self.view_scale, 1.0
        )

    def floor_y(self, screen_height: int, screen_x: int, visual_pos_x: float) -> int:
        wx = self.world_x(screen_x)
        centre_elev = floor_elevation(visual_pos_x)
        local_elev = floor_elevation(wx) - centre_elev
        return int((screen_height - 116) - local_elev * self.floor_vertical_scale)

    def make_floor_fn(
        self, screen_height: int, visual_pos_x: float
    ) -> Callable[[int], int]:
        """Retorna um closure ``floor_y(screen_x)`` vinculado ao estado atual."""

        def _fn(sx: int) -> int:
            return self.floor_y(screen_height, sx, visual_pos_x)

        return _fn
