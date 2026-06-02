"""Tkinter Canvas robot renderer.

*TkinterRobotRenderer* is stateless.  Caller provides the canvas and
position; this class handles all drawing.  No Tkinter imports at module
level — the caller owns the root/canvas lifecycle.
"""

from __future__ import annotations

import math
import tkinter as tk
from dataclasses import dataclass

from models import Direction
from .colors import Palette as C

__all__ = ["TkRobotState", "TkinterRobotRenderer"]


@dataclass
class TkRobotState:
    preview_angle: float
    velocidade: float
    direction: Direction


class TkinterRobotRenderer:
    """Draws the ATR robot components onto a tk.Canvas.

    All positions are relative to *(cart_x, cart_y)* where *cart_y* is
    roughly the vertical midpoint of the robot body.
    """

    def render(
        self,
        canvas: tk.Canvas,
        cart_x: int,
        cart_y: int,
        state: TkRobotState,
    ) -> None:
        self._draw_tracks(canvas, cart_x, cart_y, state)
        self._draw_body(canvas, cart_x, cart_y)
        self._draw_equipment_box(canvas, cart_x, cart_y)
        self._draw_antenna(canvas, cart_x, cart_y)
        self._draw_lidar(canvas, cart_x, cart_y, state)
        self._draw_camera_arm(canvas, cart_x, cart_y, state)
        if state.direction != "STOP":
            self._draw_direction_arrow(canvas, cart_x, cart_y, state.direction)

    # ── private helpers ────────────────────────────────────────────────────

    def _draw_tracks(self, canvas, cart_x, cart_y, state):
        x1 = cart_x - 2
        x2 = cart_x + 142
        y1 = cart_y + 36
        y2 = cart_y + 54
        mid = (y1 + y2) // 2

        canvas.create_polygon(
            x1,
            y1,
            x2,
            y1,
            x2,
            y2,
            x1,
            y2,
            fill=C.TRACK_FILL.hex(),
            outline=C.TRACK_OUTLINE.hex(),
            width=1,
        )
        canvas.create_line(
            x1, y1 + 2, x2, y1 + 2, fill=C.TRACK_HIGHLIGHT.hex(), width=1
        )

        for ti in range(0, 144, 11):
            tx = x1 + ti
            canvas.create_line(
                tx, y1 + 2, tx, y2 - 2, fill=C.TRACK_TREAD.hex(), width=2
            )

        for sx in (x1, x2):
            canvas.create_oval(
                sx - 11,
                mid - 11,
                sx + 11,
                mid + 11,
                fill=C.SPROCKET_FILL.hex(),
                outline=C.SPROCKET_OUTLINE.hex(),
                width=2,
            )
            for k in range(6):
                a = state.preview_angle + k * math.pi / 3
                ex, ey = int(sx + math.cos(a) * 7), int(mid + math.sin(a) * 7)
                canvas.create_line(
                    sx, mid, ex, ey, fill=C.SPROCKET_SPOKE.hex(), width=1
                )
            canvas.create_oval(
                sx - 3, mid - 3, sx + 3, mid + 3, fill=C.SPROCKET_HUB.hex(), outline=""
            )

        for ri in range(1, 4):
            rwx = x1 + int(144 * ri / 4)
            canvas.create_oval(
                rwx - 7,
                mid - 7,
                rwx + 7,
                mid + 7,
                fill=C.ROAD_WHEEL_FILL.hex(),
                outline=C.ROAD_WHEEL_OUTLINE.hex(),
                width=1,
            )
            canvas.create_oval(
                rwx - 2,
                mid - 2,
                rwx + 2,
                mid + 2,
                fill=C.ROAD_WHEEL_HUB.hex(),
                outline="",
            )

    def _draw_body(self, canvas, cart_x, cart_y):
        bx1, bx2 = cart_x + 8, cart_x + 132
        by1, by2 = cart_y + 8, cart_y + 36
        canvas.create_polygon(
            bx1,
            by1,
            bx2,
            by1,
            bx2,
            by2,
            bx1,
            by2,
            fill=C.BODY_FILL.hex(),
            outline=C.BODY_OUTLINE.hex(),
            width=2,
        )
        canvas.create_line(
            bx1 + 6,
            (by1 + by2) // 2,
            bx2 - 6,
            (by1 + by2) // 2,
            fill=C.BODY_PANEL.hex(),
            width=1,
        )

    def _draw_equipment_box(self, canvas, cart_x, cart_y):
        bx1 = cart_x + 8
        by1 = cart_y + 8
        eq1x, eq2x = bx1 + 6, bx1 + 64
        eq1y, eq2y = by1 - 20, by1
        canvas.create_polygon(
            eq1x,
            eq1y,
            eq2x,
            eq1y,
            eq2x,
            eq2y,
            eq1x,
            eq2y,
            fill=C.EQ_BOX_FILL.hex(),
            outline=C.EQ_BOX_OUTLINE.hex(),
            width=1,
        )
        for slot in range(4):
            sx = eq1x + 7 + slot * 12
            canvas.create_line(
                sx, eq1y + 5, sx, eq1y + 14, fill=C.EQ_BOX_VENT.hex(), width=2
            )

    def _draw_antenna(self, canvas, cart_x, cart_y):
        by1 = cart_y + 8
        eq1y = by1 - 20
        ant_x = cart_x + 8 + 18
        canvas.create_line(
            ant_x, eq1y, ant_x, cart_y - 48, fill=C.ANTENNA_STEM.hex(), width=2
        )
        canvas.create_oval(
            ant_x - 4,
            cart_y - 52,
            ant_x + 4,
            cart_y - 44,
            fill=C.ANTENNA_TIP.hex(),
            outline="",
        )
        canvas.create_oval(
            ant_x - 3,
            cart_y - 51,
            ant_x + 3,
            cart_y - 45,
            fill=C.ANTENNA_GLOW.hex(),
            outline="",
        )

    def _draw_lidar(self, canvas, cart_x, cart_y, state):
        by1 = cart_y + 8
        lidar_x = cart_x + 84
        lidar_cy = by1 - 14
        lidar_r = 15

        canvas.create_rectangle(
            lidar_x - 14,
            by1 - 9,
            lidar_x + 14,
            by1,
            fill=C.LIDAR_MOUNT_FILL.hex(),
            outline=C.LIDAR_MOUNT_OUTLINE.hex(),
            width=1,
        )

        beam_colors = [
            C.LIDAR_LENS_RING,
            C.LIDAR_LENS_RING,
            C.LIDAR_LENS,
            C.LIDAR_LENS,
            C.LIDAR_SHELL_OUTLINE,
            C.LIDAR_SHELL_OUTLINE,
            C.LIDAR_SHELL,
        ]
        n = 15
        for b in range(n):
            ang = math.radians(-78.0 + b * (156.0 / (n - 1)))
            bx_e = int(lidar_x + math.sin(ang) * 120)
            by_e = int(lidar_cy - lidar_r - math.cos(ang) * 120)
            cdist = abs(b - (n - 1) / 2.0) / ((n - 1) / 2.0)
            cidx = min(len(beam_colors) - 1, int(cdist * len(beam_colors)))
            canvas.create_line(
                lidar_x,
                lidar_cy - lidar_r + 2,
                bx_e,
                by_e,
                fill=beam_colors[cidx].hex(),
                width=1,
            )

        canvas.create_oval(
            lidar_x - lidar_r - 4,
            lidar_cy - lidar_r - 4,
            lidar_x + lidar_r + 4,
            lidar_cy + lidar_r + 4,
            fill=C.LIDAR_SHELL.hex(),
            outline=C.LIDAR_SHELL_OUTLINE.hex(),
            width=2,
        )
        canvas.create_oval(
            lidar_x - lidar_r,
            lidar_cy - lidar_r,
            lidar_x + lidar_r,
            lidar_cy + lidar_r,
            fill=C.LIDAR_LENS.hex(),
            outline=C.LIDAR_LENS_RING.hex(),
            width=2,
        )
        canvas.create_oval(
            lidar_x - lidar_r + 2,
            lidar_cy - lidar_r + 2,
            lidar_x - lidar_r + 9,
            lidar_cy - lidar_r + 9,
            fill=C.LIDAR_SHINE_OUTER.hex(),
            outline="",
        )

    def _draw_camera_arm(self, canvas, cart_x, cart_y, state):
        bx2, by1 = cart_x + 132, cart_y + 8
        cb_x, cb_y = bx2 - 18, by1
        pt_y = by1 - 24
        at_x, at_y = cb_x + 28, by1 - 28

        canvas.create_line(cb_x, cb_y, cb_x, pt_y, fill=C.ARM_STEEL.hex(), width=3)
        canvas.create_oval(
            cb_x - 4,
            pt_y - 4,
            cb_x + 4,
            pt_y + 4,
            fill=C.ARM_JOINT.hex(),
            outline=C.ARM_JOINT_OUTLINE.hex(),
            width=1,
        )
        canvas.create_line(cb_x, pt_y, at_x, at_y, fill=C.ARM_STEEL.hex(), width=3)

        canvas.create_rectangle(
            at_x - 4,
            at_y - 16,
            at_x + 22,
            at_y + 2,
            fill=C.CAM_BODY.hex(),
            outline=C.CAM_BODY_OUTLINE.hex(),
            width=1,
        )
        canvas.create_oval(
            at_x + 2,
            at_y - 13,
            at_x + 16,
            at_y - 1,
            fill=C.CAM_LENS.hex(),
            outline=C.CAM_LENS_RING.hex(),
            width=1,
        )
        canvas.create_oval(
            at_x + 3,
            at_y - 12,
            at_x + 8,
            at_y - 7,
            fill=C.LIDAR_SHINE_OUTER.hex(),
            outline="",
        )

        led = C.LED_ACTIVE if abs(state.velocidade) > 0.05 else C.LED_IDLE
        canvas.create_oval(
            at_x + 18, at_y - 16, at_x + 23, at_y - 11, fill=led.hex(), outline=""
        )
        canvas.create_text(
            at_x + 9,
            at_y + 6,
            text="CAM",
            fill=C.ANTENNA_STEM.hex(),
            font=("Helvetica", 8, "bold"),
        )

    def _draw_direction_arrow(self, canvas, cart_x, cart_y, direction):
        color = C.SLOPE_DOWN.hex() if direction == "LEFT" else C.SLOPE_UP.hex()
        arrow_end = cart_x - 28 if direction == "LEFT" else cart_x + 160
        canvas.create_line(
            cart_x + 68,
            cart_y - 12,
            arrow_end,
            cart_y - 12,
            fill=color,
            width=4,
            arrow=tk.LAST,
        )
