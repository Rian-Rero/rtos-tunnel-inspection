"""Visualização física do túnel (Pygame).

O simulador consome exclusivamente a telemetria MQTT publicada pelo núcleo C++
e renderiza o carrinho, o túnel, LIDAR, IMU, encoder e inspeção visual.
"""

from __future__ import annotations

import json
import logging
import math
import time

import paho.mqtt.client as mqtt
import pygame

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


class TunelSimulator:
    """Visualizador 2D do túnel sincronizado pelo broker MQTT."""

    def __init__(self, broker: str = "localhost", port: int = 1883):
        self.broker = broker
        self.port = port
        try:
            self.client = mqtt.Client(
                client_id="Python_Simulador",
                callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
            )
        except TypeError:
            self.client = mqtt.Client(client_id="Python_Simulador")

        self.pos_x = 0.0
        self.target_pos_x = 0.0
        self.visual_pos_x = 0.0
        self.reveal_pos_x = 0.0
        self.distance_m = 0.0
        self.velocidade = 0.0
        self.modo_operacao = "MANUAL"
        self.direcao = "STOP"
        self.encoder_count = 0
        self.last_encoder_count = 0
        self.imu = 0.0
        self.lidar = 2.0
        self.inspection_active = False
        self.robot_history: list[dict] = []
        self.anomaly_marks: list[dict] = []
        self.yolo_state = "Aguardando inspeção..."
        self.yolo_result_expires_at: float | None = None
        self.last_yolo_type = "Aguardando"
        self.last_yolo_confidence = 0.0
        self.preview_angle = 0.0
        self.view_start_m = 0.0
        self.view_scale = 60.0

        self._setup_mqtt()

    def _setup_mqtt(self):
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(self.broker, self.port, 60)
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        logging.info("Simulador conectado ao MQTT Broker.")
        client.subscribe("telemetry/robot")
        client.subscribe("telemetry/yolo")
        client.subscribe("state/inspection")

    def on_message(self, client, userdata, msg):
        payload = msg.payload.decode(errors="replace")

        if msg.topic == "telemetry/robot":
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                logging.warning("Telemetria inválida recebida: %s", payload)
                return

            self.robot_history.append(data)
            self.robot_history = self.robot_history[-360:]
            self.target_pos_x = float(data.get("pos_x", self.target_pos_x))
            self.pos_x = self.target_pos_x
            self.distance_m = float(data.get("distance_m", self.target_pos_x))
            self.velocidade = float(
                data.get("current_speed", data.get("velocidade", 0.0))
            )
            self.modo_operacao = "MANUAL" if data.get("manual_mode") else "AUTO"
            self.imu = float(data.get("imu", self.imu))
            self.lidar = float(
                data.get("lidar_distance_y", data.get("lidar", self.lidar))
            )
            deviation = self.lidar - 2.0
            if abs(deviation) >= 0.35:
                anomaly_type = "Buraco" if deviation > 0 else "Saliencia"
                if (
                    not self.anomaly_marks
                    or abs(self.target_pos_x - float(self.anomaly_marks[-1]["pos_x"]))
                    > 0.18
                ):
                    self.anomaly_marks.append(
                        {
                            "pos_x": self.target_pos_x,
                            "lidar": self.lidar,
                            "type": anomaly_type,
                        }
                    )
                    self.anomaly_marks = self.anomaly_marks[-48:]
            self.last_encoder_count = self.encoder_count
            self.encoder_count = int(data.get("encoder", self.encoder_count))

            raw_direction = data.get("direction", 0)
            if isinstance(raw_direction, (int, float)):
                self.direcao = {-1: "LEFT", 0: "STOP", 1: "RIGHT"}.get(
                    int(raw_direction), "STOP"
                )
            else:
                self.direcao = (
                    str(data.get("direction_label", raw_direction)).upper() or "STOP"
                )
            return

        if msg.topic == "telemetry/yolo":
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                self.yolo_state = payload
                return

            status = (
                "Anomalia detectada"
                if data.get("anomalia_detectada")
                else "Sem anomalia"
            )
            confidence = data.get("confianca")
            if isinstance(confidence, (int, float)):
                self.last_yolo_confidence = float(confidence)
                self.yolo_state = f"{status} | confiança {confidence:.2f}"
            else:
                self.yolo_state = status
            self.last_yolo_type = str(
                data.get("tipo", data.get("anomalia_visual_simulada", status))
            )
            self.yolo_result_expires_at = time.monotonic() + 5.0

        if msg.topic == "state/inspection":
            self.inspection_active = payload.strip() == "1"
            if self.inspection_active:
                self.yolo_state = "Inspeção em andamento..."
                self.yolo_result_expires_at = None
            elif self.yolo_result_expires_at is None:
                self.yolo_state = "Sistema em regime normal"

    def _draw_background(self, screen):
        width, height = screen.get_size()
        screen.fill((7, 13, 24))
        pygame.draw.rect(screen, (12, 19, 32), (0, 0, width, height))
        pygame.draw.rect(screen, (16, 24, 39), (0, 78, width, height - 154))
        pygame.draw.rect(screen, (5, 10, 18), (0, height - 76, width, 76))

        for index, x in enumerate(range(-80, width + 120, 110)):
            color = (22, 31, 46) if index % 2 else (28, 38, 54)
            points = [
                (x, 78),
                (x + 72, 78),
                (x + 118, height - 104),
                (x + 18, height - 104),
            ]
            pygame.draw.polygon(screen, color, points)

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

    def _draw_overlay(self, screen):
        width, height = screen.get_size()
        shadow = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (3, 7, 18, 42), (0, 0, width, height))
        screen.blit(shadow, (0, 0))

    def _screen_x(self, world_x: float) -> int:
        return int(70 + (world_x - self.view_start_m) * self.view_scale)

    def _world_x(self, screen_x: int) -> float:
        return self.view_start_m + (screen_x - 70) / max(self.view_scale, 1.0)

    def _floor_elevation(self, world_x: float) -> float:
        return 0.32 * math.sin(world_x / 7.5) + 0.08 * math.sin(world_x / 2.4)

    def _floor_y(self, screen, x: int) -> int:
        width, height = screen.get_size()
        world_x = self._world_x(x)
        center_elevation = self._floor_elevation(self.visual_pos_x)
        local_elevation = self._floor_elevation(world_x) - center_elevation
        imu_slope = math.sin(math.radians(self.imu)) * 0.035
        return int((height - 116) - local_elevation * 82 - (x - width / 2) * imu_slope)

    def _draw_unmapped_overlay(self, screen):
        width, height = screen.get_size()
        reveal_x = self._screen_x(self.reveal_pos_x)
        if reveal_x >= width:
            return

        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        fade_width = 190
        start_x = max(0, reveal_x - 70)
        for x in range(start_x, width, 6):
            progress = min(1.0, max(0.0, (x - start_x) / fade_width))
            alpha = int(82 + progress * 154)
            pygame.draw.rect(overlay, (3, 7, 18, alpha), (x, 78, 8, height - 154))
            pygame.draw.rect(
                overlay, (4, 8, 14, min(245, alpha + 10)), (x, height - 118, 8, 76)
            )

        edge = pygame.Surface((36, height), pygame.SRCALPHA)
        pygame.draw.rect(edge, (96, 165, 250, 55), (0, 84, 2, height - 174))
        screen.blit(overlay, (0, 0))
        screen.blit(edge, (start_x, 0))

    def _draw_tunnel_profile(self, screen):
        width, height = screen.get_size()
        roof_mid_y = 178
        history = self.robot_history

        if not history:
            font = pygame.font.SysFont("arial", 22, bold=True)
            screen.blit(
                font.render(
                    "Aguardando telemetria do C++ via MQTT...", True, (226, 232, 240)
                ),
                (28, 120),
            )
            return

        view_width_m = 18.0
        self.view_start_m = max(0.0, self.visual_pos_x - 4.0)
        self.view_scale = (width - 140) / view_width_m
        view_end_m = self.view_start_m + view_width_m

        visible_samples = [
            sample
            for sample in history
            if self.view_start_m
            <= float(sample.get("pos_x", self.visual_pos_x))
            <= view_end_m
        ]
        if not visible_samples:
            visible_samples = history[-1:]

        raw_points = []
        for sample in visible_samples:
            sample_x = float(sample.get("pos_x", self.visual_pos_x))
            lidar = float(sample.get("lidar_distance_y", sample.get("lidar", 2.0)))
            x = self._screen_x(sample_x)
            roof_y = roof_mid_y - (lidar - 2.0) * 82.0
            roof_y += math.sin(math.radians(self.imu)) * (x - width / 2) * 0.045
            roof_y = max(86, min(height - 230, roof_y))
            raw_points.append((x, roof_y, lidar))

        path_points = []
        for index, (x, _, _) in enumerate(raw_points):
            window = raw_points[max(0, index - 2) : min(len(raw_points), index + 3)]
            smooth_y = sum(point[1] for point in window) / len(window)
            path_points.append((x, smooth_y))

        floor_left_y = self._floor_y(screen, 0)
        floor_right_y = self._floor_y(screen, width)
        floor_poly = [
            (0, floor_left_y),
            (width, floor_right_y),
            (width, height),
            (0, height),
        ]

        if path_points:
            ceiling_poly = (
                [(0, 78)] + [(x, y - 24) for x, y in path_points] + [(width, 78)]
            )
            pygame.draw.polygon(screen, (45, 55, 72), ceiling_poly)
            for index, (x, y) in enumerate(path_points[::3]):
                vein_color = (78, 90, 110) if index % 2 else (62, 75, 94)
                pygame.draw.line(
                    screen,
                    vein_color,
                    (int(x) - 28, int(y) - 26),
                    (int(x) + 26, int(y) - 14),
                    2,
                )
            if len(path_points) >= 2:
                pygame.draw.lines(screen, (203, 213, 225), False, path_points, 4)
            else:
                pygame.draw.circle(
                    screen,
                    (203, 213, 225),
                    (int(path_points[0][0]), int(path_points[0][1])),
                    4,
                )

        pygame.draw.polygon(screen, (57, 38, 26), floor_poly)
        pygame.draw.polygon(
            screen,
            (80, 52, 32),
            [
                (0, floor_left_y),
                (width, floor_right_y),
                (width, min(height, floor_right_y + 34)),
                (0, min(height, floor_left_y + 34)),
            ],
        )
        for x in range(-40, width + 40, 58):
            y = self._floor_y(screen, x)
            pygame.draw.ellipse(
                screen,
                (43, 29, 20),
                (x, y + 12, 44, 12),
            )
            pygame.draw.circle(screen, (102, 72, 45), (x + 18, y + 8), 3)
            pygame.draw.circle(screen, (128, 88, 53), (x + 34, y + 18), 2)
        pygame.draw.line(
            screen, (151, 101, 55), (0, floor_left_y), (width, floor_right_y), 5
        )
        pygame.draw.line(
            screen,
            (92, 64, 42),
            (0, floor_left_y + 28),
            (width, floor_right_y + 28),
            2,
        )

        marker_font = pygame.font.SysFont("arial", 13, bold=True)
        for mark in self.anomaly_marks:
            mark_x = float(mark["pos_x"])
            if not (self.view_start_m <= mark_x <= view_end_m):
                continue
            x = self._screen_x(mark_x)
            y = roof_mid_y - (float(mark["lidar"]) - 2.0) * 82.0
            y += math.sin(math.radians(self.imu)) * (x - width / 2) * 0.045
            y = max(86, min(height - 230, y))
            if mark["type"] == "Buraco":
                color = (59, 130, 246)
                label = "Buraco"
            else:
                color = (248, 113, 113)
                label = "Saliencia"
            pygame.draw.circle(screen, color, (int(x), int(y)), 7)
            screen.blit(
                marker_font.render(label, True, color), (int(x) - 22, int(y) - 26)
            )

        axis_font = pygame.font.SysFont("arial", 13)
        for meter in range(int(self.view_start_m), int(view_end_m) + 1, 3):
            x = self._screen_x(float(meter))
            if 0 <= x <= width:
                y = self._floor_y(screen, x)
                pygame.draw.line(screen, (71, 85, 105), (x, y - 10), (x, y + 10), 1)
                screen.blit(
                    axis_font.render(f"{meter} m", True, (148, 163, 184)),
                    (x - 16, y + 14),
                )

        info_font = pygame.font.SysFont("arial", 14, bold=True)
        screen.blit(
            info_font.render(f"IMU {self.imu:.1f}°", True, (191, 219, 254)),
            (width - 120, 26),
        )
        self._draw_unmapped_overlay(screen)

    def _draw_camera_monitor(self, screen):
        width, _ = screen.get_size()
        if not self.inspection_active and self.yolo_result_expires_at is None:
            return

        panel = pygame.Rect(width - 300, 84, 264, 122)
        monitor = pygame.Surface((panel.width, panel.height), pygame.SRCALPHA)
        pygame.draw.rect(monitor, (8, 13, 23, 232), monitor.get_rect(), border_radius=6)
        pygame.draw.rect(
            monitor, (96, 165, 250, 190), monitor.get_rect(), 2, border_radius=6
        )

        view_rect = pygame.Rect(12, 18, 154, 76)
        pygame.draw.rect(monitor, (64, 67, 73), view_rect, border_radius=4)
        for y in range(view_rect.y + 8, view_rect.bottom - 4, 13):
            pygame.draw.line(
                monitor,
                (92, 96, 104),
                (view_rect.x + 4, y),
                (view_rect.right - 4, y + 8),
                2,
            )

        if self.inspection_active:
            beam_color = (96, 165, 250, 95)
            defect_label = "CAPTURANDO"
        else:
            beam_color = (96, 165, 250, 45)
            defect_label = self.last_yolo_type.upper()
        pygame.draw.polygon(
            monitor,
            beam_color,
            [(89, 90), (24, 24), (154, 24)],
        )
        pygame.draw.circle(monitor, (219, 234, 254), (89, 88), 7)
        pygame.draw.line(monitor, (15, 23, 42), (44, 48), (132, 58), 5)

        font = pygame.font.SysFont("arial", 12, bold=True)
        small = pygame.font.SysFont("arial", 11)
        monitor.blit(font.render("CAMERA DO ROBO", True, (226, 232, 240)), (12, 5))
        monitor.blit(font.render(defect_label[:16], True, (191, 219, 254)), (178, 28))
        monitor.blit(
            small.render(
                f"conf {self.last_yolo_confidence:.2f}", True, (148, 163, 184)
            ),
            (178, 48),
        )
        monitor.blit(
            small.render("imagem sintética", True, (148, 163, 184)),
            (178, 68),
        )
        screen.blit(monitor, panel)

    def _draw_robot(self, screen):
        width, _ = screen.get_size()
        robot_x = self._screen_x(self.visual_pos_x)
        robot_x = max(130, min(width - 260, robot_x))
        floor_y = self._floor_y(screen, robot_x)
        tilt = math.sin(math.radians(self.imu)) * 10.0
        robot_y = floor_y - 86

        body_points = [
            (robot_x, robot_y + 12 + tilt),
            (robot_x + 160, robot_y - tilt),
            (robot_x + 160, robot_y + 54 - tilt),
            (robot_x, robot_y + 66 + tilt),
        ]
        shadow = pygame.Surface((220, 80), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 90), (8, 28, 196, 34))
        screen.blit(shadow, (robot_x - 22, floor_y - 42))

        pygame.draw.polygon(screen, (34, 197, 94), body_points)
        pygame.draw.polygon(screen, (187, 247, 208), body_points, 3)
        pygame.draw.line(
            screen,
            (134, 239, 172),
            (robot_x + 18, robot_y + 23 + tilt),
            (robot_x + 146, robot_y + 11 - tilt),
            3,
        )

        cab_points = [
            (robot_x + 18, robot_y + 16 + tilt),
            (robot_x + 128, robot_y + 9 - tilt),
            (robot_x + 142, robot_y + 34 - tilt),
            (robot_x + 12, robot_y + 42 + tilt),
        ]
        pygame.draw.polygon(screen, (15, 23, 42), cab_points)
        pygame.draw.polygon(screen, (51, 65, 85), cab_points, 2)

        cockpit_glow = pygame.Surface((160, 56), pygame.SRCALPHA)
        pygame.draw.ellipse(cockpit_glow, (34, 211, 238, 28), (18, 4, 124, 28))
        screen.blit(cockpit_glow, (robot_x + 6, robot_y + 6))

        camera_mount = (int(robot_x + 96), int(robot_y + 3 - tilt))
        camera_tip = (camera_mount[0], camera_mount[1] - 30)
        camera_rect = pygame.Rect(camera_tip[0] - 22, camera_tip[1] - 12, 44, 24)
        pygame.draw.line(screen, (203, 213, 225), camera_mount, camera_tip, 5)
        pygame.draw.rect(screen, (15, 23, 42), camera_rect, border_radius=6)
        pygame.draw.rect(screen, (148, 163, 184), camera_rect, 2, border_radius=6)
        pygame.draw.circle(screen, (96, 165, 250), camera_tip, 9)
        pygame.draw.circle(
            screen, (219, 234, 254), (camera_tip[0] + 2, camera_tip[1] - 2), 2
        )
        status_color = (248, 113, 113) if self.inspection_active else (74, 222, 128)
        pygame.draw.circle(
            screen, status_color, (camera_tip[0] + 16, camera_tip[1] - 7), 3
        )
        camera_font = pygame.font.SysFont("arial", 10, bold=True)
        screen.blit(
            camera_font.render("CAM", True, (226, 232, 240)),
            (camera_tip[0] - 11, camera_tip[1] + 13),
        )

        if self.inspection_active:
            beam = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            beam_top_y = max(78, camera_tip[1] - 230)
            beam_points = [
                (camera_tip[0] - 8, camera_tip[1] - 3),
                (camera_tip[0] + 8, camera_tip[1] - 3),
                (camera_tip[0] + 86, beam_top_y),
                (camera_tip[0] - 86, beam_top_y),
            ]
            pygame.draw.polygon(beam, (96, 165, 250, 108), beam_points)
            pygame.draw.line(
                beam,
                (219, 234, 254, 185),
                camera_tip,
                (camera_tip[0], beam_top_y),
                3,
            )
            screen.blit(beam, (0, 0))

        wheel_radius = 16
        wheel_centers = [
            (robot_x + 28, floor_y - wheel_radius),
            (robot_x + 132, floor_y - wheel_radius),
        ]
        spin_angle = self.preview_angle * (1 if self.velocidade >= 0 else -1)
        if self.encoder_count != self.last_encoder_count:
            spin_angle += (self.encoder_count - self.last_encoder_count) * 0.02

        for index, center in enumerate(wheel_centers):
            pygame.draw.circle(screen, (15, 23, 42), center, wheel_radius + 4)
            pygame.draw.circle(screen, (148, 163, 184), center, wheel_radius, 2)
            angle = spin_angle + index * math.pi / 2.0
            for offset in (0, math.pi / 2, math.pi, 3 * math.pi / 2):
                x = center[0] + math.cos(angle + offset) * (wheel_radius - 2)
                y = center[1] + math.sin(angle + offset) * (wheel_radius - 2)
                pygame.draw.line(screen, (226, 232, 240), center, (x, y), 2)

        pygame.draw.line(
            screen,
            (226, 232, 240),
            wheel_centers[0],
            wheel_centers[1],
            2,
        )
        pygame.draw.line(
            screen,
            (96, 165, 250),
            (robot_x + 12, robot_y + 58 + tilt),
            (robot_x + 148, robot_y + 52 - tilt),
            2,
        )

        if self.direcao != "STOP":
            arrow_color = (96, 165, 250) if self.direcao == "LEFT" else (250, 204, 21)
            arrow_tip_x = robot_x - 30 if self.direcao == "LEFT" else robot_x + 190
            pygame.draw.line(
                screen,
                arrow_color,
                (robot_x + 80, robot_y - 10),
                (arrow_tip_x, robot_y - 10),
                4,
            )
            pygame.draw.polygon(
                screen,
                arrow_color,
                [
                    (arrow_tip_x, robot_y - 10),
                    (
                        arrow_tip_x - 12 * (-1 if arrow_tip_x > robot_x + 80 else 1),
                        robot_y - 18,
                    ),
                    (
                        arrow_tip_x - 12 * (-1 if arrow_tip_x > robot_x + 80 else 1),
                        robot_y - 2,
                    ),
                ],
            )

        label_font = pygame.font.SysFont("arial", 14, bold=True)
        screen.blit(
            label_font.render(f"Encoder {self.encoder_count}", True, (226, 232, 240)),
            (robot_x + 18, robot_y - 30),
        )

    def run(self):
        """Loop principal do simulador integrado com Pygame."""
        pygame.init()
        screen = pygame.display.set_mode((1200, 560))
        pygame.display.set_caption("Simulador do Túnel (ATR)")
        clock = pygame.time.Clock()
        font = pygame.font.SysFont("arial", 22, bold=True)
        small_font = pygame.font.SysFont("arial", 18)

        running = True
        while running:
            dt = clock.tick(60) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            position_alpha = min(1.0, max(0.08, dt * 7.0))
            self.visual_pos_x += (
                self.target_pos_x - self.visual_pos_x
            ) * position_alpha
            reveal_target = max(0.0, self.visual_pos_x + 0.85)
            reveal_alpha = min(1.0, max(0.04, dt * 4.0))
            self.reveal_pos_x += (reveal_target - self.reveal_pos_x) * reveal_alpha

            if abs(self.velocidade) > 0.05:
                self.preview_angle += abs(self.velocidade) * 0.055 * dt * 20.0
            if (
                self.yolo_result_expires_at is not None
                and time.monotonic() >= self.yolo_result_expires_at
            ):
                self.yolo_result_expires_at = None
                if not self.inspection_active:
                    self.yolo_state = "Sistema em regime normal"

            self._draw_background(screen)
            self._draw_tunnel_profile(screen)
            self._draw_camera_monitor(screen)
            self._draw_robot(screen)
            self._draw_overlay(screen)

            header = (
                f"POS {self.distance_m:.2f} m | VEL {self.velocidade:.1f}% | "
                f"LIDAR {self.lidar:.2f} m | IMU {self.imu:.1f}° | "
                f"MODO {self.modo_operacao} | DIR {self.direcao}"
            )
            screen.blit(font.render(header, True, (248, 250, 252)), (28, 18))

            subtitle = "Visualização guiada somente por MQTT: C++ publica sensores, atuador, IMU e telemetria"
            screen.blit(small_font.render(subtitle, True, (226, 232, 240)), (28, 44))

            inspection = (
                f"Inspeção YOLO: {self.yolo_state} | Encoder {self.encoder_count}"
            )
            screen.blit(
                small_font.render(inspection, True, (148, 163, 184)),
                (28, 510),
            )

            pygame.display.flip()

        pygame.quit()
        self.client.loop_stop()
        self.client.disconnect()


if __name__ == "__main__":
    sim = TunelSimulator()
    sim.run()
