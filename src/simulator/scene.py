"""Pygame scene renderer — everything except the robot model.

*TunnelScene* receives a *SceneState* snapshot per frame and draws:
  - background grid / panels
  - tunnel ceiling profile (LIDAR-driven)
  - floor geology
  - slope scan overlay
  - anomaly markers
  - distance ruler
  - camera-monitor panel
  - dark overlay vignette
  - unmapped fog-of-war
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import pygame

from models import AnomalyMark, InspectionState
from .terrain import ViewTransform, slope_label, slope_color_rgb, local_imu

__all__ = ["SceneState", "TunnelScene"]


@dataclass
class SceneState:
    """Snapshot of simulator state required for a single frame render."""

    visual_pos_x: float
    reveal_pos_x: float
    imu: float
    lidar: float
    robot_history: list[dict] = field(default_factory=list)
    anomaly_marks: list[AnomalyMark] = field(default_factory=list)
    inspection: InspectionState = field(default_factory=InspectionState)


class TunnelScene:
    """Stateless Pygame renderer for the tunnel environment."""

    def draw_background(self, screen: pygame.Surface) -> None:
        width, height = screen.get_size()
        screen.fill((7, 13, 24))
        pygame.draw.rect(screen, (12, 19, 32), (0, 0, width, height))
        pygame.draw.rect(screen, (16, 24, 39), (0, 78, width, height - 154))
        pygame.draw.rect(screen, (5, 10, 18), (0, height - 76, width, 76))

        for i, x in enumerate(range(-80, width + 120, 110)):
            color = (22, 31, 46) if i % 2 else (28, 38, 54)
            pygame.draw.polygon(
                screen,
                color,
                [
                    (x, 78),
                    (x + 72, 78),
                    (x + 118, height - 104),
                    (x + 18, height - 104),
                ],
            )

        for x in range(40, width, 80):
            pygame.draw.line(screen, (31, 41, 55), (x, 92), (x, height - 100), 1)
        for y in range(120, height - 92, 60):
            pygame.draw.line(screen, (31, 41, 55), (0, y), (width, y), 1)

        for x in range(20, width, 46):
            y = 98 + int(18 * math.sin(x * 0.031))
            pygame.draw.circle(screen, (55, 65, 81), (x, y), 2)
        for x in range(0, width, 64):
            y = height - 92 + int(8 * math.sin(x * 0.04))
            pygame.draw.line(screen, (30, 41, 59), (x, y), (x + 34, y - 7), 2)

    def draw_overlay(self, screen: pygame.Surface) -> None:
        width, height = screen.get_size()
        srf = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.rect(srf, (3, 7, 18, 42), (0, 0, width, height))
        screen.blit(srf, (0, 0))

    def draw_tunnel_profile(
        self, screen: pygame.Surface, state: SceneState, view: ViewTransform
    ) -> None:
        width, height = screen.get_size()
        floor_fn = view.make_floor_fn(height, state.visual_pos_x)
        roof_mid_y = 178

        history = state.robot_history
        if not history:
            font = pygame.font.SysFont("arial", 22, bold=True)
            screen.blit(
                font.render(
                    "Aguardando telemetria do C++ via MQTT...", True, (226, 232, 240)
                ),
                (28, 120),
            )

        visible = [
            s
            for s in history
            if view.view_start_m
            <= float(s.get("pos_x", state.visual_pos_x))
            <= view.view_end_m
        ] or history[-1:]

        raw_pts = []
        for s in visible:
            sx = float(s.get("pos_x", state.visual_pos_x))
            lidar = float(s.get("lidar_distance_y", s.get("lidar", 2.0)))
            x = view.screen_x(sx)
            ry = roof_mid_y - (lidar - 2.0) * 82.0
            ry += math.sin(math.radians(state.imu)) * (x - width / 2) * 0.045
            raw_pts.append((x, max(86, min(height - 230, ry)), lidar))

        path_pts = []
        for i, (x, _, _) in enumerate(raw_pts):
            win = raw_pts[max(0, i - 2) : i + 3]
            path_pts.append((x, sum(p[1] for p in win) / len(win)))

        floor_top = [(x, floor_fn(x)) for x in range(-24, width + 25, 24)]
        floor_poly = floor_top + [(width + 24, height), (-24, height)]

        if path_pts:
            ceil_poly = [(0, 78)] + [(x, y - 24) for x, y in path_pts] + [(width, 78)]
            pygame.draw.polygon(screen, (45, 55, 72), ceil_poly)
            for i, (x, y) in enumerate(path_pts[::3]):
                c = (78, 90, 110) if i % 2 else (62, 75, 94)
                pygame.draw.line(
                    screen, c, (int(x) - 28, int(y) - 26), (int(x) + 26, int(y) - 14), 2
                )
            if len(path_pts) >= 2:
                pygame.draw.lines(screen, (203, 213, 225), False, path_pts, 4)
            else:
                pygame.draw.circle(
                    screen,
                    (203, 213, 225),
                    (int(path_pts[0][0]), int(path_pts[0][1])),
                    4,
                )

        pygame.draw.polygon(screen, (57, 38, 26), floor_poly)
        crust = floor_top + [(x, min(height, y + 38)) for x, y in reversed(floor_top)]
        pygame.draw.polygon(screen, (80, 52, 32), crust)
        for x in range(-40, width + 40, 58):
            y = floor_fn(x)
            pygame.draw.ellipse(screen, (43, 29, 20), (x, y + 12, 44, 12))
            pygame.draw.circle(screen, (102, 72, 45), (x + 18, y + 8), 3)
            pygame.draw.circle(screen, (128, 88, 53), (x + 34, y + 18), 2)
        if len(floor_top) >= 2:
            pygame.draw.lines(screen, (151, 101, 55), False, floor_top, 5)
            pygame.draw.lines(
                screen, (92, 64, 42), False, [(x, y + 28) for x, y in floor_top], 2
            )

        self._draw_slope_scan(screen, view, state.imu)
        self._draw_anomaly_marks(screen, state, view, roof_mid_y)
        self._draw_distance_ruler(screen, view, floor_fn)
        self._draw_imu_gauge(screen, state.imu)
        self._draw_unmapped_overlay(screen, view, state.reveal_pos_x)

    def draw_camera_monitor(
        self, screen: pygame.Surface, insp: InspectionState
    ) -> None:
        width, _ = screen.get_size()
        if not insp.active and insp.result_expires_at is None:
            return

        rect = pygame.Rect(width - 300, 84, 264, 122)
        srf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(srf, (8, 13, 23, 232), srf.get_rect(), border_radius=6)
        pygame.draw.rect(srf, (96, 165, 250, 190), srf.get_rect(), 2, border_radius=6)

        view_rect = pygame.Rect(12, 18, 154, 76)
        pygame.draw.rect(srf, (64, 67, 73), view_rect, border_radius=4)
        for y in range(view_rect.y + 8, view_rect.bottom - 4, 13):
            pygame.draw.line(
                srf,
                (92, 96, 104),
                (view_rect.x + 4, y),
                (view_rect.right - 4, y + 8),
                2,
            )

        beam_alpha = 95 if insp.active else 45
        label = "CAPTURANDO" if insp.active else insp.last_type.upper()
        pygame.draw.polygon(
            srf, (96, 165, 250, beam_alpha), [(89, 90), (24, 24), (154, 24)]
        )
        pygame.draw.circle(srf, (219, 234, 254), (89, 88), 7)
        pygame.draw.line(srf, (15, 23, 42), (44, 48), (132, 58), 5)

        font = pygame.font.SysFont("arial", 12, bold=True)
        small = pygame.font.SysFont("arial", 11)
        srf.blit(font.render("CAMERA DO ROBO", True, (226, 232, 240)), (12, 5))
        srf.blit(font.render(label[:16], True, (191, 219, 254)), (178, 28))
        srf.blit(
            small.render(f"conf {insp.last_confidence:.2f}", True, (148, 163, 184)),
            (178, 48),
        )
        srf.blit(small.render("imagem sintética", True, (148, 163, 184)), (178, 68))
        screen.blit(srf, rect)

    # ── private helpers ──────────────────────────────────────────────────────

    def _draw_slope_scan(self, screen, view: ViewTransform, imu: float):
        width, height = screen.get_size()
        layer = pygame.Surface((width, height), pygame.SRCALPHA)
        font = pygame.font.SysFont("arial", 12, bold=True)
        last_label, cooldown_x = None, -999
        for x in range(24, width - 92, 52):
            wx = view.world_x(x)
            angle = local_imu(wx)
            lbl = slope_label(angle)
            color = slope_color_rgb(angle)
            alpha = 168 if lbl != "PLANO" else 90
            y = view.floor_y(height, x, 0.0)
            nx, ny = x + 42, view.floor_y(height, x + 42, 0.0)
            pygame.draw.line(layer, (*color, alpha), (x, y - 17), (nx, ny - 17), 5)
            tip = (nx, ny - 17)
            pygame.draw.polygon(
                layer,
                (*color, alpha),
                [tip, (tip[0] - 10, tip[1] - 6), (tip[0] - 10, tip[1] + 6)],
            )
            if lbl != last_label and x - cooldown_x > 150:
                layer.blit(font.render(lbl, True, color), (x + 2, y - 42))
                cooldown_x, last_label = x, lbl
        screen.blit(layer, (0, 0))

    def _draw_anomaly_marks(
        self, screen, state: SceneState, view: ViewTransform, roof_mid_y: int
    ):
        _, height = screen.get_size()
        font = pygame.font.SysFont("arial", 13, bold=True)
        for mark in state.anomaly_marks:
            if not (view.view_start_m <= mark.pos_x <= view.view_end_m):
                continue
            x = view.screen_x(mark.pos_x)
            _, width = screen.get_size()[1], screen.get_size()[0]
            y = roof_mid_y - (mark.lidar - 2.0) * 82.0
            y += math.sin(math.radians(state.imu)) * (x - width / 2) * 0.045
            y = max(86, min(height - 230, y))
            self._draw_anomaly_shape(screen, int(x), int(y), mark.kind)
            color = (59, 130, 246) if mark.kind == "Buraco" else (248, 113, 113)
            screen.blit(font.render(mark.kind, True, color), (int(x) - 22, int(y) - 26))

    def _draw_anomaly_shape(self, screen, x: int, y: int, kind: str):
        if kind == "Buraco":
            pygame.draw.ellipse(screen, (4, 8, 14), (x - 38, y - 20, 76, 34))
            pygame.draw.ellipse(screen, (37, 99, 235), (x - 41, y - 23, 82, 40), 3)
            pygame.draw.arc(
                screen, (147, 197, 253), (x - 34, y - 16, 68, 28), 0, math.pi, 2
            )
            for off in (-26, -12, 18, 30):
                pygame.draw.line(
                    screen, (96, 165, 250), (x + off, y - 12), (x + off + 10, y - 30), 2
                )
        else:
            pts = [
                (x - 36, y - 20),
                (x - 18, y + 18),
                (x + 4, y + 34),
                (x + 26, y + 12),
                (x + 40, y - 18),
            ]
            pygame.draw.polygon(screen, (120, 57, 48), pts)
            pygame.draw.polygon(screen, (248, 113, 113), pts, 3)
            pygame.draw.line(
                screen, (254, 202, 202), (x - 12, y + 8), (x + 16, y + 20), 2
            )

    def _draw_distance_ruler(self, screen, view: ViewTransform, floor_fn):
        width, _ = screen.get_size()
        font = pygame.font.SysFont("arial", 13)
        for meter in range(max(0, int(view.view_start_m)), int(view.view_end_m) + 1, 3):
            x = view.screen_x(float(meter))
            if not (0 <= x <= width):
                continue
            y = floor_fn(x)
            pygame.draw.line(screen, (71, 85, 105), (x, y - 10), (x, y + 10), 1)
            screen.blit(
                font.render(f"{meter} m", True, (148, 163, 184)), (x - 16, y + 14)
            )

    def _draw_imu_gauge(self, screen, imu: float):
        width, _ = screen.get_size()
        lbl = slope_label(imu)
        color = slope_color_rgb(imu)
        font = pygame.font.SysFont("arial", 14, bold=True)
        screen.blit(
            font.render(f"IMU {imu:+.1f}° | {lbl}", True, color), (width - 188, 26)
        )

        gx, gy, glen = width - 230, 58, 160
        sp = max(-34, min(34, int(imu * 5.0)))
        pygame.draw.line(screen, (71, 85, 105), (gx, gy), (gx + glen, gy), 2)
        pygame.draw.line(screen, color, (gx, gy + sp), (gx + glen, gy - sp), 5)
        tip = (gx + glen, gy - sp)
        pygame.draw.polygon(
            screen, color, [tip, (tip[0] - 12, tip[1] - 7), (tip[0] - 12, tip[1] + 7)]
        )

    def _draw_unmapped_overlay(self, screen, view: ViewTransform, reveal_pos_x: float):
        width, height = screen.get_size()
        reveal_x = view.screen_x(reveal_pos_x)
        if reveal_x >= width:
            return
        srf = pygame.Surface((width, height), pygame.SRCALPHA)
        fade_w, start_x = 190, max(0, reveal_x - 70)
        for x in range(start_x, width, 6):
            p = min(1.0, max(0.0, (x - start_x) / fade_w))
            a = int(82 + p * 154)
            pygame.draw.rect(srf, (3, 7, 18, a), (x, 78, 8, height - 154))
            pygame.draw.rect(
                srf, (4, 8, 14, min(245, a + 10)), (x, height - 118, 8, 76)
            )
        edge = pygame.Surface((36, height), pygame.SRCALPHA)
        pygame.draw.rect(edge, (96, 165, 250, 55), (0, 84, 2, height - 174))
        screen.blit(srf, (0, 0))
        screen.blit(edge, (start_x, 0))
