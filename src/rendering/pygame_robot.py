"""Renderizador do robô em Pygame.

*PygameRobotRenderer* é uma classe de desenho sem estado: recebe tudo o
que precisa pelos argumentos de *render()* e não conhece MQTT, gerência
de estado nem o loop principal.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

import pygame

from models import Direction
from .colors import Palette as C

__all__ = ["RobotRenderState", "PygameRobotRenderer"]


@dataclass
class RobotRenderState:
    """Tudo que o renderizador precisa, passado explicitamente e sem mutação."""

    ## Ângulo acumulado usado para animar esteiras e rodas.
    spin_angle: float
    ## Indica se o feixe da câmera de inspeção deve ser exibido.
    inspection_active: bool
    ## Direção atual do robô.
    direction: Direction
    ## Contagem do encoder exibida junto ao robô.
    encoder_count: int
    ## Velocidade atual usada para animação visual.
    velocidade: float


class PygameRobotRenderer:
    """Desenha o robô ATR em uma superfície Pygame.

    O chamador é responsável pelo posicionamento: informe *rx* (X da
    esteira traseira), *fx* (X da esteira dianteira) e uma *floor_y_fn*
    que retorna o Y de tela do piso para um X de tela.
    """

    def render(
        self,
        screen: pygame.Surface,
        rx: int,
        fx: int,
        floor_y_fn: Callable[[int], int],
        state: RobotRenderState,
    ) -> None:
        """Desenha todos os componentes do robô na superfície informada."""
        cx = (rx + fx) // 2
        tr = 13
        body_gap = 3
        body_h = 44
        body_lift = tr * 2 + body_gap

        def ty(x: int, lift: float = 0.0) -> int:
            t = max(0.0, min(1.0, (x - rx) / max(1, fx - rx)))
            return int(floor_y_fn(rx) + (floor_y_fn(fx) - floor_y_fn(rx)) * t - lift)

        floor_mid = int((floor_y_fn(rx) + floor_y_fn(fx)) / 2)
        self._draw_shadow(screen, rx, fx, floor_mid)
        self._draw_tracks(screen, rx, fx, tr, ty, state.spin_angle)
        self._draw_body(screen, rx, fx, tr, body_gap, body_h, body_lift, ty)
        self._draw_equipment_box(screen, rx, tr, body_gap, body_h, body_lift, ty)
        self._draw_antenna(screen, rx, tr, body_gap, body_h, body_lift, ty)
        self._draw_lidar(screen, cx, tr, body_gap, body_h, body_lift, ty)
        self._draw_camera_arm(
            screen, rx, fx, tr, body_gap, body_h, body_lift, ty, state
        )
        if state.direction != "STOP":
            self._draw_direction_arrow(
                screen, rx, fx, cx, tr, body_gap, body_h, body_lift, ty, state.direction
            )
        self._draw_encoder_label(
            screen, cx, tr, body_gap, body_h, body_lift, ty, state.encoder_count
        )

    # ── auxiliares privados de desenho ──────────────────────────────────────

    def _draw_shadow(self, screen, rx, fx, floor_mid):
        """Desenha a sombra inferior do robô."""
        shd = pygame.Surface((fx - rx + 40, 28), pygame.SRCALPHA)
        pygame.draw.ellipse(shd, (0, 0, 0, 72), (4, 8, fx - rx + 32, 14))
        screen.blit(shd, (rx - 8, floor_mid - 10))

    def _draw_tracks(self, screen, rx, fx, tr, ty, spin_angle):
        """Desenha esteiras, rodas e animação de tração."""
        track_span = fx - rx
        track_pts = [
            (rx, ty(rx, 0)),
            (fx, ty(fx, 0)),
            (fx, ty(fx, tr * 2)),
            (rx, ty(rx, tr * 2)),
        ]
        pygame.draw.polygon(screen, C.TRACK_FILL, track_pts)
        pygame.draw.polygon(screen, C.TRACK_OUTLINE, track_pts, 2)

        tread_off = int(spin_angle * 10) % 12
        for i in range(-tread_off, track_span + 12, 12):
            tx_pos = rx + i
            if not (rx <= tx_pos <= fx):
                continue
            pygame.draw.line(
                screen,
                C.TRACK_TREAD,
                (tx_pos, ty(tx_pos, tr * 2 - 3)),
                (tx_pos, ty(tx_pos, 3)),
                2,
            )

        pygame.draw.line(
            screen,
            C.TRACK_HIGHLIGHT,
            (rx, ty(rx, tr * 2 - 1)),
            (fx, ty(fx, tr * 2 - 1)),
            2,
        )

        for center_x, center_y in ((rx, ty(rx, tr)), (fx, ty(fx, tr))):
            pygame.draw.circle(screen, C.SPROCKET_FILL, (center_x, center_y), tr)
            pygame.draw.circle(screen, C.SPROCKET_OUTLINE, (center_x, center_y), tr, 2)
            for k in range(6):
                a = spin_angle + k * math.pi / 3
                pygame.draw.line(
                    screen,
                    C.SPROCKET_SPOKE,
                    (center_x, center_y),
                    (
                        int(center_x + math.cos(a) * (tr - 3)),
                        int(center_y + math.sin(a) * (tr - 3)),
                    ),
                    2,
                )
            pygame.draw.circle(screen, C.SPROCKET_HUB, (center_x, center_y), 4)

        for i in range(1, 4):
            t = i / 4.0
            wx = int(rx + track_span * t)
            wy = ty(wx, tr)
            pygame.draw.circle(screen, C.ROAD_WHEEL_FILL, (wx, wy), 8)
            pygame.draw.circle(screen, C.ROAD_WHEEL_OUTLINE, (wx, wy), 8, 1)
            pygame.draw.circle(screen, C.ROAD_WHEEL_HUB, (wx, wy), 3)

    def _draw_body(self, screen, rx, fx, tr, body_gap, body_h, body_lift, ty):
        """Desenha a carroceria principal do robô."""
        bx_l = rx + 14
        bx_r = fx - 14
        body_pts = [
            (bx_l, ty(bx_l, body_lift + body_h)),
            (bx_r, ty(bx_r, body_lift + body_h)),
            (bx_r, ty(bx_r, body_lift)),
            (bx_l, ty(bx_l, body_lift)),
        ]
        pygame.draw.polygon(screen, C.BODY_FILL, body_pts)
        pygame.draw.polygon(screen, C.BODY_OUTLINE, body_pts, 2)
        mid_x1, mid_x2 = bx_l + 6, bx_r - 6
        pygame.draw.line(
            screen,
            C.BODY_PANEL,
            (mid_x1, (ty(mid_x1, body_lift + body_h) + ty(mid_x1, body_lift)) // 2),
            (mid_x2, (ty(mid_x2, body_lift + body_h) + ty(mid_x2, body_lift)) // 2),
            1,
        )

    def _draw_equipment_box(self, screen, rx, tr, body_gap, body_h, body_lift, ty):
        """Desenha a caixa de equipamentos embarcada."""
        bx_l = rx + 14
        eq_l = bx_l + 8
        eq_r = bx_l + 74
        eq_h = 26

        def top(x):
            return ty(x, body_lift + body_h)

        eq_pts = [
            (eq_l, top(eq_l) - eq_h),
            (eq_r, top(eq_r) - eq_h),
            (eq_r, top(eq_r)),
            (eq_l, top(eq_l)),
        ]
        pygame.draw.polygon(screen, C.EQ_BOX_FILL, eq_pts)
        pygame.draw.polygon(screen, C.EQ_BOX_OUTLINE, eq_pts, 2)
        for slot in range(4):
            sx = eq_l + 9 + slot * 13
            pygame.draw.line(
                screen,
                C.EQ_BOX_VENT,
                (sx, top(sx) - eq_h + 6),
                (sx, top(sx) - eq_h + 16),
                3,
            )

    def _draw_antenna(self, screen, rx, tr, body_gap, body_h, body_lift, ty):
        """Desenha a antena de comunicação."""
        bx_l = rx + 14
        ant_x = bx_l + 22
        eq_h = 26
        base_y = ty(ant_x, body_lift + body_h) - eq_h
        tip_y = base_y - 48
        pygame.draw.line(screen, C.ANTENNA_STEM, (ant_x, base_y), (ant_x, tip_y), 2)
        pygame.draw.circle(screen, C.ANTENNA_TIP, (ant_x, tip_y), 4)
        pygame.draw.circle(screen, C.ANTENNA_GLOW, (ant_x, tip_y + 1), 3)

    def _draw_lidar(self, screen, cx, tr, body_gap, body_h, body_lift, ty):
        """Desenha o LIDAR e seu cone de varredura."""
        lidar_x = cx + 10
        lidar_base = ty(lidar_x, body_lift + body_h)
        lidar_cy = lidar_base - 16
        lidar_r = 18

        pygame.draw.rect(
            screen,
            C.LIDAR_MOUNT_FILL,
            (lidar_x - 16, lidar_base - 10, 32, 11),
            border_radius=3,
        )
        pygame.draw.rect(
            screen,
            C.LIDAR_MOUNT_OUTLINE,
            (lidar_x - 16, lidar_base - 10, 32, 11),
            1,
            border_radius=3,
        )

        beam_surf = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        origin = (lidar_x, lidar_cy - lidar_r + 2)
        n = 17
        for b in range(n):
            ang = math.radians(-82.0 + b * (164.0 / (n - 1)))
            length = 290 + int(math.cos(ang * 1.5) * 28)
            end = (
                int(origin[0] + math.sin(ang) * length),
                int(origin[1] - math.cos(ang) * length),
            )
            cdist = abs(b - (n - 1) / 2.0) / ((n - 1) / 2.0)
            alpha = max(35, int(192 - cdist * 138))
            g_val = max(168, int(212 - cdist * 42))
            pygame.draw.line(beam_surf, (48, g_val, 255, alpha), origin, end, 1)
        screen.blit(beam_surf, (0, 0))

        pygame.draw.circle(screen, C.LIDAR_SHELL, (lidar_x, lidar_cy), lidar_r + 4)
        pygame.draw.circle(
            screen, C.LIDAR_SHELL_OUTLINE, (lidar_x, lidar_cy), lidar_r + 4, 2
        )
        pygame.draw.circle(screen, C.LIDAR_LENS, (lidar_x, lidar_cy), lidar_r)
        pygame.draw.circle(screen, C.LIDAR_LENS_RING, (lidar_x, lidar_cy), lidar_r, 2)
        pygame.draw.circle(screen, C.LIDAR_SHINE_OUTER, (lidar_x - 5, lidar_cy - 5), 5)
        pygame.draw.circle(screen, C.LIDAR_SHINE_INNER, (lidar_x - 5, lidar_cy - 5), 2)

    def _draw_camera_arm(
        self,
        screen,
        rx,
        fx,
        tr,
        body_gap,
        body_h,
        body_lift,
        ty,
        state: RobotRenderState,
    ):
        """Desenha o braço de câmera e o feixe de inspeção quando ativo."""
        bx_r = fx - 14
        cam_base_x = bx_r - 22
        cam_base_y = ty(cam_base_x, body_lift + body_h)
        post_top = (cam_base_x, cam_base_y - 28)

        pygame.draw.line(screen, C.ARM_STEEL, (cam_base_x, cam_base_y), post_top, 4)
        pygame.draw.line(screen, C.ARM_HIGHLIGHT, (cam_base_x, cam_base_y), post_top, 2)
        pygame.draw.circle(screen, C.ARM_JOINT, post_top, 5)
        pygame.draw.circle(screen, C.ARM_JOINT_OUTLINE, post_top, 5, 1)

        arm_tip = (cam_base_x + 30, cam_base_y - 34)
        pygame.draw.line(screen, C.ARM_STEEL, post_top, arm_tip, 4)
        pygame.draw.line(screen, C.ARM_HIGHLIGHT, post_top, arm_tip, 2)

        cam_rect = pygame.Rect(arm_tip[0] - 6, arm_tip[1] - 18, 24, 16)
        pygame.draw.rect(screen, C.CAM_BODY, cam_rect, border_radius=4)
        pygame.draw.rect(screen, C.CAM_BODY_OUTLINE, cam_rect, 1, border_radius=4)

        cam_lens = (arm_tip[0] + 7, arm_tip[1] - 10)
        pygame.draw.circle(screen, C.CAM_LENS, cam_lens, 7)
        pygame.draw.circle(screen, C.CAM_LENS_RING, cam_lens, 7, 1)
        pygame.draw.circle(screen, C.CAM_SHINE, (cam_lens[0] - 2, cam_lens[1] - 2), 2)

        led = C.LED_ACTIVE if state.inspection_active else C.LED_IDLE
        pygame.draw.circle(screen, led, (arm_tip[0] + 18, arm_tip[1] - 18), 3)

        font = pygame.font.SysFont("arial", 10, bold=True)
        screen.blit(
            font.render("CAM", True, (205, 220, 238)), (arm_tip[0] - 2, arm_tip[1] + 2)
        )

        if state.inspection_active:
            beam = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            tip_y = max(20, cam_lens[1] - 190)
            pts = [
                (cam_lens[0] - 5, cam_lens[1] - 4),
                (cam_lens[0] + 5, cam_lens[1] - 4),
                (cam_lens[0] + 68, tip_y),
                (cam_lens[0] - 68, tip_y),
            ]
            pygame.draw.polygon(beam, (96, 165, 250, 82), pts)
            pygame.draw.line(
                beam, (218, 234, 254, 168), cam_lens, (cam_lens[0], tip_y), 2
            )
            screen.blit(beam, (0, 0))

    def _draw_direction_arrow(
        self, screen, rx, fx, cx, tr, body_gap, body_h, body_lift, ty, direction
    ):
        """Desenha a seta lateral de direção quando o robô está em movimento."""
        color = C.SLOPE_DOWN if direction == "LEFT" else C.SLOPE_UP
        arrow_y = ty(cx, body_lift + body_h // 2)
        tip_x = rx - 36 if direction == "LEFT" else fx + 36
        pygame.draw.line(screen, color, (cx, arrow_y), (tip_x, arrow_y), 4)
        dx = -1 if direction == "LEFT" else 1
        pygame.draw.polygon(
            screen,
            color,
            [
                (tip_x, arrow_y),
                (tip_x - dx * 14, arrow_y - 8),
                (tip_x - dx * 14, arrow_y + 8),
            ],
        )

    def _draw_encoder_label(
        self, screen, cx, tr, body_gap, body_h, body_lift, ty, encoder
    ):
        """Desenha a contagem do encoder abaixo do robô."""
        font = pygame.font.SysFont("arial", 13, bold=True)
        screen.blit(
            font.render(f"Enc {encoder}", True, (190, 208, 226)),
            (cx - 30, ty(cx, body_lift + body_h + 32)),
        )
