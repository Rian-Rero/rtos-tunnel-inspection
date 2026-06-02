"""Renderer components — one per graphics backend.

Each renderer is a stateless class whose only job is to draw the ATR
robot onto whatever surface the calling application provides (Pygame
Surface, Tkinter Canvas or OpenCV ndarray).
"""

from .pygame_robot import PygameRobotRenderer, RobotRenderState
from .tk_robot import TkinterRobotRenderer, TkRobotState
from .cv_robot import OpenCVRobotRenderer

__all__ = [
    "PygameRobotRenderer",
    "RobotRenderState",
    "TkinterRobotRenderer",
    "TkRobotState",
    "OpenCVRobotRenderer",
]
