"""ATR colour palette — single source of truth for both Pygame (RGB tuples)
and Tkinter (hex strings).

All rendering modules import from here; no colour constants should appear
in application code.
"""

from __future__ import annotations

from typing import NamedTuple

__all__ = ["RGB", "Palette", "hex_palette"]


class RGB(NamedTuple):
    r: int
    g: int
    b: int

    def hex(self) -> str:
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}"

    def with_alpha(self, a: int) -> tuple[int, int, int, int]:
        return (self.r, self.g, self.b, a)


class Palette:
    """Pygame-ready RGB tuples for the ATR robot."""

    # ── Tracks ───────────────────────────────────────────────────────────────
    TRACK_FILL = RGB(26, 31, 39)
    TRACK_OUTLINE = RGB(55, 65, 76)
    TRACK_TREAD = RGB(17, 21, 27)
    TRACK_HIGHLIGHT = RGB(70, 82, 96)
    SPROCKET_FILL = RGB(45, 52, 62)
    SPROCKET_OUTLINE = RGB(88, 100, 114)
    SPROCKET_SPOKE = RGB(106, 120, 136)
    SPROCKET_HUB = RGB(65, 75, 88)
    ROAD_WHEEL_FILL = RGB(38, 45, 54)
    ROAD_WHEEL_OUTLINE = RGB(72, 84, 98)
    ROAD_WHEEL_HUB = RGB(52, 62, 74)

    # ── Body ─────────────────────────────────────────────────────────────────
    BODY_FILL = RGB(65, 84, 98)
    BODY_OUTLINE = RGB(106, 128, 146)
    BODY_PANEL = RGB(46, 63, 76)

    # ── Equipment box ────────────────────────────────────────────────────────
    EQ_BOX_FILL = RGB(52, 68, 82)
    EQ_BOX_OUTLINE = RGB(88, 108, 124)
    EQ_BOX_VENT = RGB(32, 48, 60)

    # ── Antenna ──────────────────────────────────────────────────────────────
    ANTENNA_STEM = RGB(168, 186, 204)
    ANTENNA_TIP = RGB(200, 218, 236)
    ANTENNA_GLOW = RGB(96, 170, 255)

    # ── LiDAR dome ───────────────────────────────────────────────────────────
    LIDAR_MOUNT_FILL = RGB(48, 62, 76)
    LIDAR_MOUNT_OUTLINE = RGB(84, 102, 118)
    LIDAR_SHELL = RGB(38, 50, 63)
    LIDAR_SHELL_OUTLINE = RGB(70, 86, 102)
    LIDAR_LENS = RGB(18, 94, 168)
    LIDAR_LENS_RING = RGB(50, 154, 248)
    LIDAR_SHINE_OUTER = RGB(155, 210, 255)
    LIDAR_SHINE_INNER = RGB(215, 240, 255)

    # ── Camera arm ───────────────────────────────────────────────────────────
    ARM_STEEL = RGB(128, 146, 162)
    ARM_HIGHLIGHT = RGB(158, 175, 192)
    ARM_JOINT = RGB(76, 92, 108)
    ARM_JOINT_OUTLINE = RGB(124, 142, 160)
    CAM_BODY = RGB(20, 26, 34)
    CAM_BODY_OUTLINE = RGB(104, 120, 138)
    CAM_LENS = RGB(28, 100, 178)
    CAM_LENS_RING = RGB(52, 150, 238)
    CAM_SHINE = RGB(170, 212, 252)
    LED_ACTIVE = RGB(248, 113, 113)
    LED_IDLE = RGB(74, 222, 128)

    # ── Slope indicator ──────────────────────────────────────────────────────
    SLOPE_UP = RGB(250, 204, 21)
    SLOPE_DOWN = RGB(96, 165, 250)
    SLOPE_FLAT = RGB(148, 163, 184)


def hex_palette() -> dict[str, str]:
    """Return all Palette entries as a {name: hex_string} dict (for Tkinter)."""
    return {
        name: value.hex()
        for name, value in vars(Palette).items()
        if isinstance(value, RGB)
    }
