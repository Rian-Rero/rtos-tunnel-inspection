"""Visualização física do túnel (Pygame).

O simulador consome exclusivamente a telemetria MQTT publicada pelo núcleo C++
e renderiza o carrinho, o túnel, LIDAR, IMU, encoder e inspeção visual.
"""

from __future__ import annotations

import json
import logging
import math

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
        self.yolo_state = "Aguardando inspeção..."
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
            self.pos_x = float(data.get("pos_x", self.pos_x))
            self.distance_m = float(data.get("distance_m", self.pos_x))
            self.velocidade = float(
                data.get("current_speed", data.get("velocidade", 0.0))
            )
            self.modo_operacao = "MANUAL" if data.get("manual_mode") else "AUTO"
            self.imu = float(data.get("imu", self.imu))
            self.lidar = float(
                data.get("lidar_distance_y", data.get("lidar", self.lidar))
            )
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
                self.yolo_state = f"{status} | confiança {confidence:.2f}"
            else:
                self.yolo_state = status

        if msg.topic == "state/inspection":
            self.inspection_active = payload.strip() == "1"

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

    def _floor_y(self, screen, x: int) -> int:
        width, height = screen.get_size()
        slope = math.sin(math.radians(self.imu)) * 0.055
        return int((height - 116) - (x - width / 2) * slope)

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
        self.view_start_m = max(0.0, self.pos_x - 4.0)
        self.view_scale = (width - 140) / view_width_m
        view_end_m = self.view_start_m + view_width_m

        visible_samples = [
            sample
            for sample in history
            if self.view_start_m <= float(sample.get("pos_x", self.pos_x)) <= view_end_m
        ]
        if not visible_samples:
            visible_samples = history[-1:]

        raw_points = []
        for sample in visible_samples:
            sample_x = float(sample.get("pos_x", self.pos_x))
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

        pygame.draw.polygon(screen, (15, 23, 42), floor_poly)
        for x in range(-40, width + 40, 58):
            y = self._floor_y(screen, x)
            pygame.draw.ellipse(
                screen,
                (23, 31, 45),
                (x, y + 12, 44, 12),
            )
        pygame.draw.line(
            screen, (34, 197, 94), (0, floor_left_y), (width, floor_right_y), 5
        )
        pygame.draw.line(
            screen,
            (148, 163, 184),
            (0, floor_left_y + 28),
            (width, floor_right_y + 28),
            2,
        )

        marker_font = pygame.font.SysFont("arial", 13, bold=True)
        for sample, (x, y) in zip(visible_samples[-10:], path_points[-10:]):
            lidar = float(sample.get("lidar_distance_y", sample.get("lidar", 2.0)))
            deviation = lidar - 2.0
            if abs(deviation) < 0.35:
                continue
            if deviation > 0:
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

    def _draw_robot(self, screen):
        width, _ = screen.get_size()
        robot_x = self._screen_x(self.pos_x)
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

        camera_mount = (int(robot_x + 91), int(robot_y + 2 - tilt))
        camera_tip = (camera_mount[0], camera_mount[1] - 22)
        pygame.draw.line(screen, (203, 213, 225), camera_mount, camera_tip, 4)
        pygame.draw.circle(screen, (15, 23, 42), camera_tip, 12)
        pygame.draw.circle(screen, (96, 165, 250), camera_tip, 7)
        pygame.draw.circle(
            screen, (219, 234, 254), (camera_tip[0] + 2, camera_tip[1] - 2), 2
        )

        beam_alpha = 92 if self.inspection_active else 36
        beam_color = (96, 165, 250, beam_alpha)
        beam = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        beam_top_y = max(78, camera_tip[1] - 210)
        beam_points = [
            (camera_tip[0] - 7, camera_tip[1] - 4),
            (camera_tip[0] + 7, camera_tip[1] - 4),
            (camera_tip[0] + 78, beam_top_y),
            (camera_tip[0] - 78, beam_top_y),
        ]
        pygame.draw.polygon(beam, beam_color, beam_points)
        pygame.draw.line(
            beam,
            (191, 219, 254, min(160, beam_alpha + 40)),
            camera_tip,
            (camera_tip[0], beam_top_y),
            2,
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

        arrow_color = (250, 204, 21) if self.direcao != "LEFT" else (96, 165, 250)
        arrow_tip_x = robot_x + 190 if self.direcao != "LEFT" else robot_x - 30
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

            self.preview_angle += max(0.04, abs(self.velocidade) * 0.055) * dt * 20.0

            self._draw_background(screen)
            self._draw_tunnel_profile(screen)
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
