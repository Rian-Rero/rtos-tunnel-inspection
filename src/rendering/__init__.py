"""Componentes de renderização, um por mecanismo gráfico.

Cada renderizador é uma classe sem estado cuja única responsabilidade é
desenhar o robô ATR na superfície fornecida pela aplicação chamadora
(Surface do Pygame, Canvas do Tkinter ou ndarray do OpenCV).
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
