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

        self._draw_ceiling(screen, path_pts, view, width, height)

        self._draw_floor_terrain(
            screen, floor_top, width, height, view, floor_fn, state.visual_pos_x
        )
        self._draw_slope_scan(screen, view, state.imu)
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

    def _draw_floor_terrain(
        self,
        screen,
        floor_top,
        width: int,
        height: int,
        view: ViewTransform,
        floor_fn,
        visual_pos_x: float,
    ) -> None:
        """Render a realistic layered-earth floor with world-anchored detail."""
        # ── Bedrock fill — deepest layer ──────────────────────────────────────
        floor_poly = floor_top + [(width + 24, height), (-24, height)]
        pygame.draw.polygon(screen, (42, 25, 11), floor_poly)

        # ── Sub-surface clay band ─────────────────────────────────────────────
        clay_bot = [(x, min(height, y + 72)) for x, y in reversed(floor_top)]
        pygame.draw.polygon(screen, (64, 40, 19), floor_top + clay_bot)

        # ── Topsoil surface crust ─────────────────────────────────────────────
        top_bot = [(x, min(height, y + 26)) for x, y in reversed(floor_top)]
        pygame.draw.polygon(screen, (92, 58, 31), floor_top + top_bot)

        # ── World-anchored stones / pebbles ───────────────────────────────────
        # Anchored to world x (not screen x) so they don't shift as camera scrolls.
        w_step = 0.18  # metres between stone slots
        wi_start = int(view.view_start_m / w_step) - 1
        wi_end = int(view.view_end_m / w_step) + 2

        for wi in range(wi_start, wi_end):
            wx = wi * w_step
            sx = view.screen_x(wx)
            if not (-30 <= sx <= width + 30):
                continue
            sy = floor_fn(sx)

            # Deterministic mixing from world index (LCG-style, no Python hash)
            a = ((wi * 1664525 + 1013904223) >> 4) & 0xFF
            b = ((wi * 22695477 + 12345678) >> 5) & 0xFF
            c = ((wi * 134775813 + 1) >> 6) & 0xFF

            # Small surface pebble
            px = sx + (a % 34) - 17
            py = sy + 2 + (b % 5)
            pw = 2 + (c % 3)
            ph = max(1, pw - 1)
            pygame.draw.ellipse(
                screen,
                (76 + a % 34, 50 + b % 26, 31 + c % 18),
                (px - pw, py - ph, pw * 2, ph * 2),
            )

            # Medium rock — every ~3rd slot, slightly offset
            if a % 3 == 0:
                rx = sx + (b % 44) - 22
                ry = sy + 5 + (c % 7)
                rw = 7 + (a % 9)
                rh = 4 + (b % 4)
                pygame.draw.ellipse(
                    screen,
                    (68 + c % 24, 46 + a % 20, 29 + b % 14),
                    (rx - rw // 2, ry - rh // 2, rw, rh),
                )

            # Rare hairline crack on the surface
            if c % 11 == 0:
                cx1, cy1 = sx + (a % 22) - 11, sy
                cx2, cy2 = cx1 + (b % 14) - 7, sy + 2 + (c % 4)
                pygame.draw.line(screen, (33, 19, 7), (cx1, cy1), (cx2, cy2), 1)

        # ── Surface edge — crisp ground boundary with shadow ─────────────────
        if len(floor_top) >= 2:
            pygame.draw.lines(screen, (148, 96, 52), False, floor_top, 4)
            shadow = [(x, y + 9) for x, y in floor_top]
            pygame.draw.lines(screen, (30, 17, 6), False, shadow, 2)

    def _draw_slope_scan(self, screen, view: ViewTransform, imu: float):
        width, height = screen.get_size()
        layer = pygame.Surface((width, height), pygame.SRCALPHA)
        font = pygame.font.SysFont("arial", 12, bold=True)
        last_label, cooldown_x = None, -999
        for x in range(24, width - 92, 52):
            wx = view.world_x(x)
            angle = local_imu(wx)
            lbl = slope_label(angle)
            if lbl == "PLANO":
                continue
            color = slope_color_rgb(angle)
            y = view.floor_y(height, x, 0.0)
            nx, ny = x + 42, view.floor_y(height, x + 42, 0.0)
            pygame.draw.line(layer, (*color, 155), (x, y - 17), (nx, ny - 17), 4)
            tip = (nx, ny - 17)
            pygame.draw.polygon(
                layer,
                (*color, 155),
                [tip, (tip[0] - 9, tip[1] - 5), (tip[0] - 9, tip[1] + 5)],
            )
            if lbl != last_label and x - cooldown_x > 150:
                layer.blit(font.render(lbl, True, color), (x + 2, y - 42))
                cooldown_x, last_label = x, lbl
        screen.blit(layer, (0, 0))

    def _draw_anomaly_marks(
        self, screen, state: SceneState, view: ViewTransform, roof_mid_y: int
    ):
        height = screen.get_size()[1]
        width = screen.get_size()[0]
        font = pygame.font.SysFont("arial", 13, bold=True)

        visible: list[tuple[int, int, AnomalyMark]] = []
        for mark in state.anomaly_marks:
            if not (view.view_start_m <= mark.pos_x <= view.view_end_m):
                continue
            x = view.screen_x(mark.pos_x)
            y = roof_mid_y - (mark.lidar - 2.0) * 82.0
            y += math.sin(math.radians(state.imu)) * (x - width / 2) * 0.045
            y = max(86, min(height - 230, y))
            visible.append((int(x), int(y), mark))

        last_x_by_kind: dict[str, int] = {}
        for x, y, mark in visible:
            prev = last_x_by_kind.get(mark.kind, -9999)
            if abs(x - prev) < 75:
                continue
            last_x_by_kind[mark.kind] = x
            color = (96, 165, 250) if mark.kind == "Buraco" else (252, 165, 165)
            screen.blit(font.render(mark.kind, True, color), (x - 18, y - 38))

    def _draw_ceiling(
        self, screen, path_pts: list, view: ViewTransform, width: int, height: int
    ) -> None:
        """Realistic rocky tunnel ceiling with integrated anomaly rendering."""
        ROOF_TOP = 78
        FACE_H = 22  # visible face thickness in px

        if not path_pts:
            return

        face_pts = [(int(x), int(y)) for x, y in path_pts]
        if len(face_pts) < 2:
            if face_pts:
                pygame.draw.circle(screen, (82, 76, 70), face_pts[0], 5)
            return
        body_bot = [(x, y - FACE_H) for x, y in face_pts]

        # ── Rock body — dark stone mass filling from ROOF_TOP to ceiling face ─
        body_poly = [(0, ROOF_TOP)] + body_bot + [(width, ROOF_TOP)]
        pygame.draw.polygon(screen, (66, 62, 57), body_poly)

        # Depth layer — slightly darker inner pass to simulate thick rock mass
        inner_top = ROOF_TOP + 12
        inner_bot = [(x, max(ROOF_TOP + 14, y - FACE_H - 8)) for x, y in face_pts]
        depth_srf = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.polygon(
            depth_srf,
            (28, 24, 20, 130),
            [(0, inner_top)] + inner_bot + [(width, inner_top)],
        )
        screen.blit(depth_srf, (0, 0))

        # Rock strata — subtle horizontal geological bands in the body
        strata_srf = pygame.Surface((width, height), pygame.SRCALPHA)
        for si in range(7):
            ofs = 8 + si * 11
            pts = [(x, min(y - FACE_H, ROOF_TOP + ofs)) for x, y in face_pts]
            if len(pts) >= 2:
                alpha = 18 + (si % 3) * 14
                pygame.draw.lines(strata_srf, (18, 14, 11, alpha), False, pts, 1)
        screen.blit(strata_srf, (0, 0))

        # ── Visible face — underside of the rock facing the tunnel interior ───
        face_poly = body_bot + [(x, y) for x, y in reversed(face_pts)]
        pygame.draw.polygon(screen, (82, 76, 70), face_poly)

        # ── World-anchored rock surface details on the face ───────────────────
        w_step = 0.20
        wi_start = int(view.view_start_m / w_step) - 1
        wi_end = int(view.view_end_m / w_step) + 2

        for wi in range(wi_start, wi_end):
            wx = wi * w_step
            sx = view.screen_x(wx)
            if not (-30 <= sx <= width + 30):
                continue
            cy = self._interp_path_y(face_pts, sx)

            a = ((wi * 1664525 + 1013904223) >> 4) & 0xFF
            b = ((wi * 22695477 + 12345678) >> 5) & 0xFF
            c = ((wi * 134775813 + 1) >> 6) & 0xFF

            # Rock nodule on the face
            px, py = sx + (a % 28) - 14, cy - 5 - (b % 7)
            pr = 2 + (c % 4)
            pygame.draw.ellipse(
                screen,
                (74 + a % 28, 69 + b % 24, 63 + c % 20),
                (px - pr, py - pr // 2, pr * 2, pr),
            )

            # Hairline crack / fissure
            if b % 5 == 0:
                pygame.draw.line(
                    screen,
                    (48, 43, 39),
                    (sx + (a % 18) - 9, cy - 2),
                    (sx + (c % 16) - 8, cy - 10 - (a % 10)),
                    1,
                )

        # ── Profile-based anomaly shading — emergent from LIDAR geometry ───────
        # Median y as stable baseline (robust against isolated anomaly segments)
        sorted_ys = sorted(y for _, y in face_pts)
        baseline_y = sorted_ys[len(sorted_ys) // 2]

        anom_srf = pygame.Surface((width, height), pygame.SRCALPHA)
        for i in range(len(face_pts) - 1):
            x0, y0 = face_pts[i]
            x1, y1 = face_pts[i + 1]
            mid_y = (y0 + y1) * 0.5
            dev = (
                mid_y - baseline_y
            )  # positive = saliência (lower), negative = buraco (higher)

            if dev < -10:  # Buraco — ceiling above baseline → dark void opening
                t = min(1.0, (-dev - 10) / 55.0)
                alpha = int(80 + t * 155)
                # Black void fills the face segment
                pygame.draw.polygon(
                    anom_srf,
                    (3, 2, 1, alpha),
                    [(x0, y0 - FACE_H), (x1, y1 - FACE_H), (x1, y1), (x0, y0)],
                )
                # Lit rock rim at opening edge — edge catching ambient light
                rim_a = int(50 + t * 80)
                pygame.draw.line(
                    anom_srf, (126, 114, 101, rim_a), (x0, y0), (x1, y1), 2
                )

            elif dev > 10:  # Saliência — ceiling below baseline → 3-D protrusion
                t = min(1.0, (dev - 10) / 40.0)
                # Shadow on the face of the protrusion (sides face away from light)
                shd_a = int(30 + t * 55)
                pygame.draw.polygon(
                    anom_srf,
                    (0, 0, 0, shd_a),
                    [(x0, y0 - FACE_H), (x1, y1 - FACE_H), (x1, y1), (x0, y0)],
                )
                # Highlight on bottom edge — underside of protrusion catches tunnel light
                hl_a = int(35 + t * 60)
                pygame.draw.line(anom_srf, (200, 190, 178, hl_a), (x0, y0), (x1, y1), 3)

        screen.blit(anom_srf, (0, 0))

        # ── Profile edge — the lower boundary of the ceiling face ─────────────
        if len(face_pts) >= 2:
            pygame.draw.lines(screen, (96, 90, 83), False, face_pts, 3)
        elif face_pts:
            pygame.draw.circle(screen, (96, 90, 83), face_pts[0], 4)

    def _interp_path_y(self, face_pts: list, target_x: float) -> int:
        """Linear interpolation of ceiling face y at target_x."""
        if not face_pts:
            return 178
        if len(face_pts) == 1:
            return face_pts[0][1]
        for i in range(len(face_pts) - 1):
            x0, y0 = face_pts[i]
            x1, y1 = face_pts[i + 1]
            if x0 <= target_x <= x1 and x1 != x0:
                t = (target_x - x0) / (x1 - x0)
                return int(y0 + t * (y1 - y0))
        return face_pts[0][1] if target_x <= face_pts[0][0] else face_pts[-1][1]

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
