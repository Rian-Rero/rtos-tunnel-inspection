"""Módulo de simulação física do túnel (Pygame).

O simulador atua como planta física do carrinho, recebe comandos MQTT,
calcula uma cinemática simples e publica telemetria em tempo real.
"""

from __future__ import annotations

import json
import logging
import math

import paho.mqtt.client as mqtt
import pygame

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


class TunelSimulator:
    """
    Classe principal do Simulador 2D do Túnel.
    """

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
        self.velocidade = 0.0
        self.modo_operacao = "MANUAL"
        self.direcao = "STOP"
        self.encoder_count = 0
        self.last_encoder_count = 0
        self.imu = 0.0
        self.robot_history: list[dict] = []
        self.yolo_state = "Aguardando inspeção..."
        self.preview_angle = 0.0
        self.camera_offset = 0.0
        self.surface_phase = 0.0

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

    def on_message(self, client, userdata, msg):
        payload = msg.payload.decode(errors="replace")

        if msg.topic == "telemetry/robot":
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                logging.warning("Telemetria inválida recebida: %s", payload)
                return

            self.robot_history.append(data)
            self.robot_history = self.robot_history[-240:]
            self.pos_x = float(data.get("pos_x", self.pos_x))
            self.velocidade = float(
                data.get("current_speed", data.get("velocidade", 0.0))
            )
            self.modo_operacao = "MANUAL" if data.get("manual_mode") else "AUTO"
            self.imu = float(data.get("imu", self.imu))
            self.last_encoder_count = self.encoder_count
            self.encoder_count = int(data.get("encoder", self.encoder_count))
            raw_direction = data.get("direction", 0)
            if isinstance(raw_direction, (int, float)):
                direction = int(raw_direction)
                self.direcao = {-1: "LEFT", 0: "STOP", 1: "RIGHT"}.get(
                    direction, "STOP"
                )
            else:
                self.direcao = str(raw_direction).upper() or "STOP"
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

    def _draw_background(self, screen):
        screen.fill((6, 12, 24))
        width, height = screen.get_size()
        pygame.draw.rect(screen, (12, 18, 31), (0, 0, width, height))
        pygame.draw.rect(screen, (20, 28, 46), (0, 72, width, height - 136))
        pygame.draw.rect(screen, (34, 197, 94), (0, height - 84, width, 24))
        pygame.draw.rect(screen, (8, 15, 28), (0, height - 60, width, 60))

        for x in range(0, width, 60):
            pygame.draw.line(screen, (31, 41, 55), (x, 80), (x, height - 92), 1)
        for y in range(100, height - 80, 50):
            pygame.draw.line(screen, (30, 41, 59), (0, y), (width, y), 1)

    def _draw_overlay(self, screen):
        width, height = screen.get_size()
        shadow = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (3, 7, 18, 60), (0, 0, width, height))
        screen.blit(shadow, (0, 0))

    def _draw_tunnel_profile(self, screen, leitura_lidar: int):
        width, height = screen.get_size()
        horizon = 120
        floor_y = height - 96
        history = self.robot_history
        imu_tilt = math.sin(math.radians(self.imu))
        terrain_shift = int(imu_tilt * 46)
        self.surface_phase += max(0.025, abs(self.velocidade) * 0.02)
        if not history:
            pygame.draw.rect(screen, (55, 65, 81), (0, 0, width, horizon))
            font = pygame.font.SysFont("arial", 22, bold=True)
            screen.blit(
                font.render(
                    "Aguardando telemetria do C++ via MQTT...", True, (226, 232, 240)
                ),
                (28, 110),
            )
            return

        start_x = float(history[0].get("pos_x", 0.0))
        max_x = max(float(sample.get("pos_x", start_x)) for sample in history)
        span = max(1.0, max_x - start_x)
        scale_x = (width - 140) / span

        path_points = []
        for sample in history:
            sample_x = float(sample.get("pos_x", start_x))
            x = 70 + (sample_x - start_x) * scale_x
            lidar = float(sample.get("lidar_distance_y", sample.get("lidar", 2.0)))
            slope_curve = math.sin((sample_x / 18.0) + self.surface_phase) * 10
            y = horizon + (lidar - 1.2) * 70 + terrain_shift + slope_curve
            y = max(horizon - 40, min(floor_y - 36, y))
            path_points.append((x, y))

        if len(path_points) >= 2:
            pygame.draw.polygon(
                screen,
                (55, 65, 81),
                [(0, 0)] + [(x, y - 20) for x, y in path_points] + [(width, 0)],
            )
            pygame.draw.lines(screen, (226, 232, 240), False, path_points, 3)
            pygame.draw.lines(
                screen,
                (74, 222, 128),
                False,
                [(60, floor_y)] + [(x, floor_y) for x, _ in path_points],
                4,
            )

        for sample, (x, y) in zip(history[-8:], path_points[-8:]):
            lidar = float(sample.get("lidar_distance_y", sample.get("lidar", 2.0)))
            if lidar > 2.0:
                color = (59, 130, 246)
                label = "Buraco"
            elif lidar < 2.0:
                color = (248, 113, 113)
                label = "Saliencia"
            else:
                color = (148, 163, 184)
                label = "Normal"
            pygame.draw.circle(screen, color, (int(x), int(y)), 8)
            font = pygame.font.SysFont("arial", 16, bold=True)
            screen.blit(font.render(label, True, color), (int(x) - 20, int(y) - 28))

        info_font = pygame.font.SysFont("arial", 14, bold=True)
        screen.blit(
            info_font.render(f"IMU {self.imu:.1f}°", True, (191, 219, 254)),
            (width - 120, 26),
        )

    def _draw_robot(self, screen):
        width, height = screen.get_size()
        robot_world_x = self.pos_x * 10.0
        self.camera_offset = max(0.0, robot_world_x - 240.0)
        robot_x = int(240 + math.sin(self.preview_angle * 0.45) * 2)
        base_y = height - 150
        slope_lift = math.sin(math.radians(self.imu)) * 24
        suspension = math.sin(self.preview_angle * 2.4) * (
            2.0 + abs(self.velocidade) * 0.15
        )
        robot_y = int(base_y - slope_lift + suspension)

        body_points = [
            (robot_x, robot_y + 10),
            (robot_x + 160, robot_y),
            (robot_x + 160, robot_y + 54),
            (robot_x, robot_y + 64),
        ]
        body_color = (34, 197, 94)
        outline_color = (187, 247, 208)
        pygame.draw.polygon(screen, body_color, body_points)
        pygame.draw.polygon(screen, outline_color, body_points, 3)

        cab_points = [
            (robot_x + 18, robot_y + 14),
            (robot_x + 128, robot_y + 8),
            (robot_x + 142, robot_y + 34),
            (robot_x + 12, robot_y + 40),
        ]
        pygame.draw.polygon(screen, (15, 23, 42), cab_points)
        pygame.draw.polygon(screen, (51, 65, 85), cab_points, 2)

        cockpit_glow = pygame.Surface((160, 56), pygame.SRCALPHA)
        pygame.draw.ellipse(cockpit_glow, (34, 211, 238, 35), (18, 4, 124, 28))
        screen.blit(cockpit_glow, (robot_x + 6, robot_y + 6))

        wheel_radius = 16
        wheel_centers = [(robot_x + 28, robot_y + 68), (robot_x + 132, robot_y + 68)]
        spin_angle = self.preview_angle * (1 if self.velocidade >= 0 else -1)
        if self.encoder_count != self.last_encoder_count:
            spin_angle += (self.encoder_count - self.last_encoder_count) * 0.03

        for index, center in enumerate(wheel_centers):
            pygame.draw.circle(screen, (15, 23, 42), center, wheel_radius + 4)
            pygame.draw.circle(screen, (148, 163, 184), center, wheel_radius, 2)
            angle = spin_angle + index * math.pi / 2.0
            for offset in (0, math.pi / 2, math.pi, 3 * math.pi / 2):
                x = center[0] + math.cos(angle + offset) * (wheel_radius - 2)
                y = center[1] + math.sin(angle + offset) * (wheel_radius - 2)
                pygame.draw.line(screen, (226, 232, 240), center, (x, y), 2)

            axle_color = (226, 232, 240)
            pygame.draw.line(
                screen,
                axle_color,
                (robot_x + 28, robot_y + 68),
                (robot_x + 132, robot_y + 68),
                2,
            )
            pygame.draw.line(
                screen,
                (96, 165, 250),
                (robot_x + 12, robot_y + 56),
                (robot_x + 148, robot_y + 52),
                2,
            )

        arrow_color = (250, 204, 21) if self.velocidade >= 0 else (96, 165, 250)
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
            (robot_x + 18, robot_y - 28),
        )

    def run(self):
        """Loop principal do simulador integrado com Pygame."""
        pygame.init()
        screen = pygame.display.set_mode((1200, 560))
        pygame.display.set_caption("Simulador Físico do Túnel (ATR)")
        clock = pygame.time.Clock()
        font = pygame.font.SysFont("arial", 22, bold=True)
        small_font = pygame.font.SysFont("arial", 18)

        running = True
        while running:
            dt = clock.tick(60) / 1000.0  # Delta time em segundos

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            self.preview_angle += max(0.08, abs(self.velocidade) * 0.12) * dt * 20.0

            self._draw_background(screen)
            self._draw_tunnel_profile(screen, 0)
            self._draw_robot(screen)
            self._draw_overlay(screen)

            img = font.render(
                f"POS {self.pos_x:.1f} px | VEL {self.velocidade:.2f} | IMU {self.imu:.1f}° | MODO {self.modo_operacao} | DIR {self.direcao}",
                True,
                (248, 250, 252),
            )
            screen.blit(img, (28, 18))

            sub = small_font.render(
                "Rodas, suspensão e inclinação guiados só pela telemetria MQTT do C++",
                True,
                (226, 232, 240),
            )
            screen.blit(sub, (28, 42))

            speed_img = small_font.render(
                f"Inspeção: {self.yolo_state} | Encoder {self.encoder_count}",
                True,
                (148, 163, 184),
            )
            screen.blit(speed_img, (28, 510))

            pygame.display.flip()

        pygame.quit()
        self.client.loop_stop()
        self.client.disconnect()


if __name__ == "__main__":
    sim = TunelSimulator()
    sim.run()
