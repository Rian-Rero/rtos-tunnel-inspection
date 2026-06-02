"""Visualização física do túnel (Pygame).

O simulador consome exclusivamente a telemetria MQTT publicada pelo núcleo C++
e renderiza o carrinho, o túnel, LIDAR, IMU, encoder e inspeção visual.
"""

from __future__ import annotations

import json
import logging
import math
import os
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
        self.view_left_px = 70.0
        self.robot_center_px = 600.0
        self.floor_vertical_scale = 118.0

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
        return int(self.view_left_px + (world_x - self.view_start_m) * self.view_scale)

    def _world_x(self, screen_x: int) -> float:
        return self.view_start_m + (screen_x - self.view_left_px) / max(
            self.view_scale, 1.0
        )

    def _floor_elevation(self, world_x: float) -> float:
        return 0.62 * math.sin(world_x / 5.4) + 0.16 * math.sin(world_x / 1.8)

    def _floor_slope(self, world_x: float) -> float:
        return (0.62 / 5.4) * math.cos(world_x / 5.4) + (0.16 / 1.8) * math.cos(
            world_x / 1.8
        )

    def _local_imu(self, world_x: float) -> float:
        return math.degrees(math.atan(self._floor_slope(world_x)))

    def _slope_label(self) -> str:
        return self._slope_label_for_angle(self.imu)

    def _slope_color(self) -> tuple[int, int, int]:
        return self._slope_color_for_angle(self.imu)

    def _slope_label_for_angle(self, angle: float) -> str:
        if angle > 0.4:
            return "SUBIDA"
        if angle < -0.4:
            return "DESCIDA"
        return "PLANO"

    def _slope_color_for_angle(self, angle: float) -> tuple[int, int, int]:
        if angle > 0.4:
            return (250, 204, 21)
        if angle < -0.4:
            return (96, 165, 250)
        return (148, 163, 184)

    def _floor_y(self, screen, x: int) -> int:
        _, height = screen.get_size()
        world_x = self._world_x(x)
        center_elevation = self._floor_elevation(self.visual_pos_x)
        local_elevation = self._floor_elevation(world_x) - center_elevation
        return int((height - 116) - local_elevation * self.floor_vertical_scale)

    def _draw_slope_scan(self, screen):
        width, height = screen.get_size()
        slope_layer = pygame.Surface((width, height), pygame.SRCALPHA)
        font = pygame.font.SysFont("arial", 12, bold=True)

        last_label = None
        label_cooldown_px = -999
        for x in range(24, width - 92, 52):
            world_x = self._world_x(x)
            angle = self._local_imu(world_x)
            label = self._slope_label_for_angle(angle)
            color = self._slope_color_for_angle(angle)
            alpha = 168 if label != "PLANO" else 90
            y = self._floor_y(screen, x)
            next_x = x + 42
            next_y = self._floor_y(screen, next_x)

            pygame.draw.line(
                slope_layer,
                (*color, alpha),
                (x, y - 17),
                (next_x, next_y - 17),
                5,
            )
            arrow_tip = (next_x, next_y - 17)
            pygame.draw.polygon(
                slope_layer,
                (*color, alpha),
                [
                    arrow_tip,
                    (arrow_tip[0] - 10, arrow_tip[1] - 6),
                    (arrow_tip[0] - 10, arrow_tip[1] + 6),
                ],
            )

            if label != last_label and x - label_cooldown_px > 150:
                slope_layer.blit(
                    font.render(label, True, color),
                    (x + 2, y - 42),
                )
                label_cooldown_px = x
                last_label = label

        screen.blit(slope_layer, (0, 0))

    def _draw_anomaly_shape(self, screen, x: int, y: int, anomaly_type: str):
        if anomaly_type == "Buraco":
            pygame.draw.ellipse(screen, (4, 8, 14), (x - 38, y - 20, 76, 34))
            pygame.draw.ellipse(screen, (37, 99, 235), (x - 41, y - 23, 82, 40), 3)
            pygame.draw.arc(
                screen, (147, 197, 253), (x - 34, y - 16, 68, 28), 0, math.pi, 2
            )
            for offset in (-26, -12, 18, 30):
                pygame.draw.line(
                    screen,
                    (96, 165, 250),
                    (x + offset, y - 12),
                    (x + offset + 10, y - 30),
                    2,
                )
            return

        points = [
            (x - 36, y - 20),
            (x - 18, y + 18),
            (x + 4, y + 34),
            (x + 26, y + 12),
            (x + 40, y - 18),
        ]
        pygame.draw.polygon(screen, (120, 57, 48), points)
        pygame.draw.polygon(screen, (248, 113, 113), points, 3)
        pygame.draw.line(screen, (254, 202, 202), (x - 12, y + 8), (x + 16, y + 20), 2)

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

        view_width_m = 18.0
        self.view_left_px = 70.0
        self.robot_center_px = width / 2
        self.view_scale = (width - 140) / view_width_m
        center_offset_m = (self.robot_center_px - self.view_left_px) / self.view_scale
        self.view_start_m = self.visual_pos_x - center_offset_m
        view_end_m = self.view_start_m + view_width_m

        if not history:
            font = pygame.font.SysFont("arial", 22, bold=True)
            screen.blit(
                font.render(
                    "Aguardando telemetria do C++ via MQTT...", True, (226, 232, 240)
                ),
                (28, 120),
            )

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

        floor_top_points = [
            (x, self._floor_y(screen, x)) for x in range(-24, width + 25, 24)
        ]
        floor_poly = floor_top_points + [(width + 24, height), (-24, height)]

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
        floor_crust = floor_top_points + [
            (x, min(height, y + 38)) for x, y in reversed(floor_top_points)
        ]
        pygame.draw.polygon(screen, (80, 52, 32), floor_crust)
        for x in range(-40, width + 40, 58):
            y = self._floor_y(screen, x)
            pygame.draw.ellipse(
                screen,
                (43, 29, 20),
                (x, y + 12, 44, 12),
            )
            pygame.draw.circle(screen, (102, 72, 45), (x + 18, y + 8), 3)
            pygame.draw.circle(screen, (128, 88, 53), (x + 34, y + 18), 2)
        if len(floor_top_points) >= 2:
            pygame.draw.lines(screen, (151, 101, 55), False, floor_top_points, 5)
            pygame.draw.lines(
                screen,
                (92, 64, 42),
                False,
                [(x, y + 28) for x, y in floor_top_points],
                2,
            )
        self._draw_slope_scan(screen)

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
            self._draw_anomaly_shape(screen, int(x), int(y), str(mark["type"]))
            screen.blit(
                marker_font.render(label, True, color), (int(x) - 22, int(y) - 26)
            )

        axis_font = pygame.font.SysFont("arial", 13)
        for meter in range(max(0, int(self.view_start_m)), int(view_end_m) + 1, 3):
            x = self._screen_x(float(meter))
            if 0 <= x <= width:
                y = self._floor_y(screen, x)
                pygame.draw.line(screen, (71, 85, 105), (x, y - 10), (x, y + 10), 1)
                screen.blit(
                    axis_font.render(f"{meter} m", True, (148, 163, 184)),
                    (x - 16, y + 14),
                )

        info_font = pygame.font.SysFont("arial", 14, bold=True)
        slope_label = self._slope_label()
        slope_color = self._slope_color()
        screen.blit(
            info_font.render(
                f"IMU {self.imu:+.1f}° | {slope_label}", True, slope_color
            ),
            (width - 188, 26),
        )
        gauge_x = width - 230
        gauge_y = 58
        gauge_len = 160
        slope_pixels = max(-34, min(34, int(self.imu * 5.0)))
        pygame.draw.line(
            screen,
            (71, 85, 105),
            (gauge_x, gauge_y),
            (gauge_x + gauge_len, gauge_y),
            2,
        )
        pygame.draw.line(
            screen,
            slope_color,
            (gauge_x, gauge_y + slope_pixels),
            (gauge_x + gauge_len, gauge_y - slope_pixels),
            5,
        )
        arrow_tip = (gauge_x + gauge_len, gauge_y - slope_pixels)
        pygame.draw.polygon(
            screen,
            slope_color,
            [
                arrow_tip,
                (arrow_tip[0] - 12, arrow_tip[1] - 7),
                (arrow_tip[0] - 12, arrow_tip[1] + 7),
            ],
        )
        terrain_font = pygame.font.SysFont("arial", 15, bold=True)
        label_x = min(width - 230, max(38, self._screen_x(self.visual_pos_x) + 185))
        label_y = self._floor_y(screen, int(label_x)) - 48
        screen.blit(
            terrain_font.render(f"{slope_label} {self.imu:+.1f}°", True, slope_color),
            (label_x, label_y),
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

        # Anchor X positions for terrain conforming
        rx = int(width / 2 - 88)  # rear track edge
        fx = rx + 176  # front track edge
        cx = (rx + fx) // 2
        rear_floor_y = self._floor_y(screen, rx)
        front_floor_y = self._floor_y(screen, fx)
        floor_y = int((rear_floor_y + front_floor_y) / 2)

        def ty(x, lift=0):
            """Screen-Y at world-X, lifted above floor."""
            t = max(0.0, min(1.0, (x - rx) / max(1, fx - rx)))
            return int(rear_floor_y + (front_floor_y - rear_floor_y) * t - lift)

        tr = 13  # sprocket radius
        body_gap = 3
        body_h = 44
        body_lift = tr * 2 + body_gap

        spin_angle = self.preview_angle * (1 if self.velocidade >= 0 else -1)

        # ── SHADOW ──────────────────────────────────────────────────────────
        shd = pygame.Surface((216, 28), pygame.SRCALPHA)
        pygame.draw.ellipse(shd, (0, 0, 0, 72), (4, 8, 208, 14))
        screen.blit(shd, (rx - 8, floor_y - 10))

        # ── CATERPILLAR TRACKS ──────────────────────────────────────────────
        track_pts = [
            (rx, ty(rx, 0)),
            (fx, ty(fx, 0)),
            (fx, ty(fx, tr * 2)),
            (rx, ty(rx, tr * 2)),
        ]
        pygame.draw.polygon(screen, (26, 31, 39), track_pts)
        pygame.draw.polygon(screen, (55, 65, 76), track_pts, 2)

        # Animated tread marks
        track_span = fx - rx
        tread_off = int(spin_angle * 10) % 12
        for i in range(-tread_off, track_span + 12, 12):
            tx_pos = rx + i
            if not (rx <= tx_pos <= fx):
                continue
            t_top = ty(tx_pos, tr * 2 - 3)
            t_bot = ty(tx_pos, 3)
            pygame.draw.line(screen, (17, 21, 27), (tx_pos, t_top), (tx_pos, t_bot), 2)

        # Upper-track highlight strip
        pygame.draw.line(
            screen, (70, 82, 96), (rx, ty(rx, tr * 2 - 1)), (fx, ty(fx, tr * 2 - 1)), 2
        )

        # Rear sprocket
        rs = (rx, ty(rx, tr))
        pygame.draw.circle(screen, (45, 52, 62), rs, tr)
        pygame.draw.circle(screen, (88, 100, 114), rs, tr, 2)
        for k in range(6):
            a = spin_angle + k * math.pi / 3
            pygame.draw.line(
                screen,
                (106, 120, 136),
                rs,
                (
                    int(rs[0] + math.cos(a) * (tr - 3)),
                    int(rs[1] + math.sin(a) * (tr - 3)),
                ),
                2,
            )
        pygame.draw.circle(screen, (65, 75, 88), rs, 4)

        # Front sprocket
        fs = (fx, ty(fx, tr))
        pygame.draw.circle(screen, (45, 52, 62), fs, tr)
        pygame.draw.circle(screen, (88, 100, 114), fs, tr, 2)
        for k in range(6):
            a = spin_angle + k * math.pi / 3
            pygame.draw.line(
                screen,
                (106, 120, 136),
                fs,
                (
                    int(fs[0] + math.cos(a) * (tr - 3)),
                    int(fs[1] + math.sin(a) * (tr - 3)),
                ),
                2,
            )
        pygame.draw.circle(screen, (65, 75, 88), fs, 4)

        # Road wheels (3 between sprockets)
        for i in range(1, 4):
            t = i / 4.0
            wx = int(rx + track_span * t)
            wy = ty(wx, tr)
            pygame.draw.circle(screen, (38, 45, 54), (wx, wy), 8)
            pygame.draw.circle(screen, (72, 84, 98), (wx, wy), 8, 1)
            pygame.draw.circle(screen, (52, 62, 74), (wx, wy), 3)

        # ── MAIN BODY ───────────────────────────────────────────────────────
        bx_l = rx + 14
        bx_r = fx - 14

        def btop(x):
            return ty(x, body_lift + body_h)

        def bbot(x):
            return ty(x, body_lift)

        body_pts = [
            (bx_l, btop(bx_l)),
            (bx_r, btop(bx_r)),
            (bx_r, bbot(bx_r)),
            (bx_l, bbot(bx_l)),
        ]
        pygame.draw.polygon(screen, (65, 84, 98), body_pts)
        pygame.draw.polygon(screen, (106, 128, 146), body_pts, 2)

        # Mid-body panel detail
        pygame.draw.line(
            screen,
            (46, 63, 76),
            (bx_l + 6, (btop(bx_l + 6) + bbot(bx_l + 6)) // 2),
            (bx_r - 6, (btop(bx_r - 6) + bbot(bx_r - 6)) // 2),
            1,
        )

        # ── EQUIPMENT BOX (rear/left of body top) ───────────────────────────
        eq_l = bx_l + 8
        eq_r = bx_l + 74
        eq_h_box = 26
        eq_pts = [
            (eq_l, btop(eq_l) - eq_h_box),
            (eq_r, btop(eq_r) - eq_h_box),
            (eq_r, btop(eq_r)),
            (eq_l, btop(eq_l)),
        ]
        pygame.draw.polygon(screen, (52, 68, 82), eq_pts)
        pygame.draw.polygon(screen, (88, 108, 124), eq_pts, 2)
        for slot in range(4):
            sx = eq_l + 9 + slot * 13
            pygame.draw.line(
                screen,
                (32, 48, 60),
                (sx, btop(sx) - eq_h_box + 6),
                (sx, btop(sx) - eq_h_box + 16),
                3,
            )

        # ── ANTENNA ─────────────────────────────────────────────────────────
        ant_x = bx_l + 22
        ant_base = btop(ant_x) - eq_h_box
        ant_tip = ant_base - 48
        pygame.draw.line(
            screen, (168, 186, 204), (ant_x, ant_base), (ant_x, ant_tip), 2
        )
        pygame.draw.circle(screen, (200, 218, 236), (ant_x, ant_tip), 4)
        pygame.draw.circle(screen, (96, 170, 255), (ant_x, ant_tip + 1), 3)

        # ── LIDAR DOME ──────────────────────────────────────────────────────
        lidar_x = cx + 10
        lidar_base = btop(lidar_x)
        lidar_cy = lidar_base - 16
        lidar_r = 18

        # Mount pedestal
        pygame.draw.rect(
            screen,
            (48, 62, 76),
            (lidar_x - 16, lidar_base - 10, 32, 11),
            border_radius=3,
        )
        pygame.draw.rect(
            screen,
            (84, 102, 118),
            (lidar_x - 16, lidar_base - 10, 32, 11),
            1,
            border_radius=3,
        )

        # Scan beams drawn BEFORE dome so dome overlaps at root
        beam_surf = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        beam_origin = (lidar_x, lidar_cy - lidar_r + 2)
        n_beams = 17
        for b in range(n_beams):
            ang = math.radians(-82.0 + b * (164.0 / (n_beams - 1)))
            beam_len = 290 + int(math.cos(ang * 1.5) * 28)
            bx_e = int(beam_origin[0] + math.sin(ang) * beam_len)
            by_e = int(beam_origin[1] - math.cos(ang) * beam_len)
            cdist = abs(b - (n_beams - 1) / 2.0) / ((n_beams - 1) / 2.0)
            alpha = max(35, int(192 - cdist * 138))
            g_val = max(168, int(212 - cdist * 42))
            pygame.draw.line(
                beam_surf, (48, g_val, 255, alpha), beam_origin, (bx_e, by_e), 1
            )
        screen.blit(beam_surf, (0, 0))

        # Dome outer shell
        pygame.draw.circle(screen, (38, 50, 63), (lidar_x, lidar_cy), lidar_r + 4)
        pygame.draw.circle(screen, (70, 86, 102), (lidar_x, lidar_cy), lidar_r + 4, 2)
        # Dome lens (blue)
        pygame.draw.circle(screen, (18, 94, 168), (lidar_x, lidar_cy), lidar_r)
        pygame.draw.circle(screen, (50, 154, 248), (lidar_x, lidar_cy), lidar_r, 2)
        # Lens shine
        pygame.draw.circle(screen, (155, 210, 255), (lidar_x - 5, lidar_cy - 5), 5)
        pygame.draw.circle(screen, (215, 240, 255), (lidar_x - 5, lidar_cy - 5), 2)

        # ── CAMERA ARM ──────────────────────────────────────────────────────
        cam_base_x = bx_r - 22
        cam_base_y = btop(cam_base_x)
        post_top = (cam_base_x, cam_base_y - 28)
        # Post
        pygame.draw.line(screen, (128, 146, 162), (cam_base_x, cam_base_y), post_top, 4)
        pygame.draw.line(screen, (158, 175, 192), (cam_base_x, cam_base_y), post_top, 2)
        # Elbow joint
        pygame.draw.circle(screen, (76, 92, 108), post_top, 5)
        pygame.draw.circle(screen, (124, 142, 160), post_top, 5, 1)
        # Horizontal boom
        arm_tip = (cam_base_x + 30, cam_base_y - 34)
        pygame.draw.line(screen, (128, 146, 162), post_top, arm_tip, 4)
        pygame.draw.line(screen, (158, 175, 192), post_top, arm_tip, 2)
        # Camera head body
        cam_rect = pygame.Rect(arm_tip[0] - 6, arm_tip[1] - 18, 24, 16)
        pygame.draw.rect(screen, (20, 26, 34), cam_rect, border_radius=4)
        pygame.draw.rect(screen, (104, 120, 138), cam_rect, 1, border_radius=4)
        # Camera lens
        cam_lens = (arm_tip[0] + 7, arm_tip[1] - 10)
        pygame.draw.circle(screen, (28, 100, 178), cam_lens, 7)
        pygame.draw.circle(screen, (52, 150, 238), cam_lens, 7, 1)
        pygame.draw.circle(
            screen, (170, 212, 252), (cam_lens[0] - 2, cam_lens[1] - 2), 2
        )
        # Status LED
        led_color = (248, 113, 113) if self.inspection_active else (74, 222, 128)
        pygame.draw.circle(screen, led_color, (arm_tip[0] + 18, arm_tip[1] - 18), 3)
        cam_font = pygame.font.SysFont("arial", 10, bold=True)
        screen.blit(
            cam_font.render("CAM", True, (205, 220, 238)),
            (arm_tip[0] - 2, arm_tip[1] + 2),
        )

        # Camera inspection beam cone
        if self.inspection_active:
            beam = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            tip_y = max(20, cam_lens[1] - 190)
            beam_pts = [
                (cam_lens[0] - 5, cam_lens[1] - 4),
                (cam_lens[0] + 5, cam_lens[1] - 4),
                (cam_lens[0] + 68, tip_y),
                (cam_lens[0] - 68, tip_y),
            ]
            pygame.draw.polygon(beam, (96, 165, 250, 82), beam_pts)
            pygame.draw.line(
                beam, (218, 234, 254, 168), cam_lens, (cam_lens[0], tip_y), 2
            )
            screen.blit(beam, (0, 0))

        # ── DIRECTION ARROW ─────────────────────────────────────────────────
        if self.direcao != "STOP":
            arrow_color = (96, 165, 250) if self.direcao == "LEFT" else (250, 204, 21)
            arrow_y = ty(cx, body_lift + body_h // 2)
            tip_x = rx - 36 if self.direcao == "LEFT" else fx + 36
            pygame.draw.line(screen, arrow_color, (cx, arrow_y), (tip_x, arrow_y), 4)
            dx = -1 if self.direcao == "LEFT" else 1
            pygame.draw.polygon(
                screen,
                arrow_color,
                [
                    (tip_x, arrow_y),
                    (tip_x - dx * 14, arrow_y - 8),
                    (tip_x - dx * 14, arrow_y + 8),
                ],
            )

        # ── ENCODER LABEL ───────────────────────────────────────────────────
        lbl_font = pygame.font.SysFont("arial", 13, bold=True)
        screen.blit(
            lbl_font.render(f"Enc {self.encoder_count}", True, (190, 208, 226)),
            (cx - 30, ty(cx, body_lift + body_h + 32)),
        )

    def run(self):
        """Loop principal do simulador integrado com Pygame."""
        pygame.init()
        display_info = pygame.display.Info()
        screen_w = int(getattr(display_info, "current_w", 1920) or 1920)
        screen_h = int(getattr(display_info, "current_h", 1080) or 1080)
        window_w = min(1200, max(920, screen_w - 80))
        window_h = 560
        if "SDL_VIDEO_WINDOW_POS" not in os.environ:
            if screen_w >= 2200:
                window_x, window_y = 1240, 40
            elif screen_h >= 1260:
                window_x, window_y = 24, 780
            else:
                window_x, window_y = 160, 130
            os.environ["SDL_VIDEO_WINDOW_POS"] = f"{window_x},{window_y}"

        screen = pygame.display.set_mode((window_w, window_h))
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
                f"LIDAR {self.lidar:.2f} m | IMU {self.imu:+.1f}° {self._slope_label()} | "
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
