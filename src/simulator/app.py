"""Main tunnel simulator application.

*TunelSimulator* is now a lean orchestrator: it owns the MQTT state,
the main Pygame loop, and delegates all rendering to *TunnelScene*
and *PygameRobotRenderer*.
"""

from __future__ import annotations

import json
import logging
import os
import time

import pygame

from config import Topics, Limits, MQTT_BROKER, MQTT_PORT
from models import AnomalyMark, InspectionState, RobotTelemetry
from mqtt import MqttComponent
from rendering import PygameRobotRenderer, RobotRenderState
from .scene import SceneState, TunnelScene
from .terrain import ViewTransform, slope_label

__all__ = ["TunelSimulator"]

logger = logging.getLogger(__name__)


class TunelSimulator(MqttComponent):
    """Pygame-based 2D tunnel visualiser driven exclusively by MQTT telemetry."""

    def __init__(self, broker: str = MQTT_BROKER, port: int = MQTT_PORT) -> None:
        super().__init__(broker, port, "Python_Simulador")

        # ── Robot state ──────────────────────────────────────────────────────
        self._telemetry = RobotTelemetry()
        self._inspection = InspectionState()
        self._target_pos_x: float = 0.0
        self._visual_pos_x: float = 0.0
        self._reveal_pos_x: float = 0.0
        self._robot_history: list[dict] = []
        self._anomaly_marks: list[AnomalyMark] = []

        # ── Animation state ──────────────────────────────────────────────────
        self._preview_angle: float = 0.0
        self._view = ViewTransform()

        # ── Renderers ────────────────────────────────────────────────────────
        self._scene = TunnelScene()
        self._robot_renderer = PygameRobotRenderer()

    # ── MQTT hooks ───────────────────────────────────────────────────────────

    def _on_connect(self, client) -> None:
        client.subscribe(Topics.TELEMETRY_ROBOT)
        client.subscribe(Topics.TELEMETRY_YOLO)
        client.subscribe(Topics.STATE_INSPECTION)

    def _on_message(self, topic: str, payload: str) -> None:
        if topic == Topics.TELEMETRY_ROBOT:
            self._handle_robot_telemetry(payload)
        elif topic == Topics.TELEMETRY_YOLO:
            self._handle_yolo(payload)
        elif topic == Topics.STATE_INSPECTION:
            self._handle_inspection_state(payload)

    def _handle_robot_telemetry(self, payload: str) -> None:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            logger.warning("Invalid telemetry: %s", payload)
            return

        self._robot_history.append(data)
        self._robot_history = self._robot_history[-Limits.ROBOT_HISTORY_MAX :]
        self._telemetry = RobotTelemetry.from_payload(data, self._telemetry)
        self._target_pos_x = self._telemetry.pos_x

        deviation = self._telemetry.lidar - 2.0
        if abs(deviation) >= Limits.ANOMALY_LIDAR_THRESHOLD:
            kind = "Buraco" if deviation > 0 else "Saliencia"
            if (
                not self._anomaly_marks
                or abs(self._telemetry.pos_x - self._anomaly_marks[-1].pos_x)
                > Limits.ANOMALY_MIN_SPACING_M
            ):
                self._anomaly_marks.append(
                    AnomalyMark(self._telemetry.pos_x, self._telemetry.lidar, kind)
                )
                self._anomaly_marks = self._anomaly_marks[-Limits.ANOMALY_MARKS_MAX :]

    def _handle_yolo(self, payload: str) -> None:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            self._inspection.yolo_state = payload
            return
        status = (
            "Anomalia detectada" if data.get("anomalia_detectada") else "Sem anomalia"
        )
        conf = data.get("confianca")
        self._inspection.last_confidence = (
            float(conf) if isinstance(conf, (int, float)) else 0.0
        )
        self._inspection.yolo_state = (
            f"{status} | confiança {self._inspection.last_confidence:.2f}"
            if isinstance(conf, (int, float))
            else status
        )
        self._inspection.last_type = str(
            data.get("tipo", data.get("anomalia_visual_simulada", status))
        )
        self._inspection.result_expires_at = time.monotonic() + Limits.YOLO_RESULT_TTL_S

    def _handle_inspection_state(self, payload: str) -> None:
        self._inspection.active = payload.strip() == "1"
        if self._inspection.active:
            self._inspection.yolo_state = "Inspeção em andamento..."
            self._inspection.result_expires_at = None
        elif self._inspection.result_expires_at is None:
            self._inspection.yolo_state = "Sistema em regime normal"

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self) -> None:
        pygame.init()
        screen, clock = self._create_window()
        font_hdr = pygame.font.SysFont("arial", 22, bold=True)
        font_sub = pygame.font.SysFont("arial", 18)

        self.connect_async()

        try:
            running = True
            while running:
                dt = clock.tick(60) / 1000.0

                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False

                self._tick_animation(dt)

                # ── Build scene state snapshot ───────────────────────────────
                self._view.update(self._visual_pos_x, screen.get_width())
                floor_fn = self._view.make_floor_fn(
                    screen.get_height(), self._visual_pos_x
                )

                scene_state = SceneState(
                    visual_pos_x=self._visual_pos_x,
                    reveal_pos_x=self._reveal_pos_x,
                    imu=self._telemetry.imu,
                    lidar=self._telemetry.lidar,
                    robot_history=self._robot_history,
                    anomaly_marks=self._anomaly_marks,
                    inspection=self._inspection,
                )

                # ── Render ───────────────────────────────────────────────────
                self._scene.draw_background(screen)
                self._scene.draw_tunnel_profile(screen, scene_state, self._view)
                self._scene.draw_camera_monitor(screen, self._inspection)

                width = screen.get_width()
                rx = int(width / 2 - 88)
                fx = rx + 176
                robot_state = RobotRenderState(
                    spin_angle=self._preview_angle,
                    inspection_active=self._inspection.active,
                    direction=self._telemetry.direction,
                    encoder_count=self._telemetry.encoder,
                    velocidade=self._telemetry.velocidade,
                )
                self._robot_renderer.render(screen, rx, fx, floor_fn, robot_state)
                self._scene.draw_overlay(screen)

                # ── HUD ──────────────────────────────────────────────────────
                lbl = slope_label(self._telemetry.imu)
                header = (
                    f"POS {self._telemetry.distance_m:.2f} m | VEL {self._telemetry.velocidade:.1f}% | "
                    f"LIDAR {self._telemetry.lidar:.2f} m | IMU {self._telemetry.imu:+.1f}° {lbl} | "
                    f"MODO {self._telemetry.mode} | DIR {self._telemetry.direction}"
                )
                screen.blit(font_hdr.render(header, True, (248, 250, 252)), (28, 18))
                screen.blit(
                    font_sub.render(
                        "Visualização guiada somente por MQTT: C++ publica sensores, atuador, IMU e telemetria",
                        True,
                        (226, 232, 240),
                    ),
                    (28, 44),
                )
                screen.blit(
                    font_sub.render(
                        f"Inspeção YOLO: {self._inspection.yolo_state} | Encoder {self._telemetry.encoder}",
                        True,
                        (148, 163, 184),
                    ),
                    (28, 510),
                )

                pygame.display.flip()
        finally:
            pygame.quit()
            self.disconnect()

    # ── helpers ───────────────────────────────────────────────────────────────

    def _tick_animation(self, dt: float) -> None:
        alpha = min(1.0, max(0.08, dt * 7.0))
        self._visual_pos_x += (self._target_pos_x - self._visual_pos_x) * alpha

        reveal_target = max(0.0, self._visual_pos_x + 0.85)
        self._reveal_pos_x += (reveal_target - self._reveal_pos_x) * min(
            1.0, max(0.04, dt * 4.0)
        )

        if abs(self._telemetry.velocidade) > 0.05:
            self._preview_angle += abs(self._telemetry.velocidade) * 0.055 * dt * 20.0

        expires = self._inspection.result_expires_at
        if expires is not None and time.monotonic() >= expires:
            self._inspection.result_expires_at = None
            if not self._inspection.active:
                self._inspection.yolo_state = "Sistema em regime normal"

    def _create_window(self) -> tuple[pygame.Surface, pygame.time.Clock]:
        info = pygame.display.Info()
        sw = int(getattr(info, "current_w", 1920) or 1920)
        sh = int(getattr(info, "current_h", 1080) or 1080)
        ww = min(1200, max(920, sw - 80))
        if "SDL_VIDEO_WINDOW_POS" not in os.environ:
            if sw >= 2200:
                wx, wy = 1240, 40
            elif sh >= 1260:
                wx, wy = 24, 780
            else:
                wx, wy = 160, 130
            os.environ["SDL_VIDEO_WINDOW_POS"] = f"{wx},{wy}"
        screen = pygame.display.set_mode((ww, 560))
        pygame.display.set_caption("Simulador do Túnel (ATR)")
        return screen, pygame.time.Clock()
