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

        # Variáveis Físicas do Robô
        self.pos_x = 0.0
        self.velocidade = 0.0
        self.motor_command = 0.0
        self.inclinacao_tunel = 5.0  # Graus (simulando declive - Ponto Extra)
        self.gravidade = 9.81
        self.metros_percorridos = 0
        self.encoder_state = False
        self.modo_operacao = "MANUAL"
        self.direcao = "STOP"

        # Perfil do teto (Mock para simular anomalias)
        self.perfil_teto = self._gerar_perfil_teto()

        self._setup_mqtt()

    def _gerar_perfil_teto(self) -> list:
        """Gera um perfil de teto estático com anomalias (buracos e saliências)."""
        perfil = [200] * 1000  # Altura normal 200
        # Injetar falha 1 (Buraco)
        for i in range(200, 250):
            perfil[i] = 300
        # Injetar falha 2 (Saliência)
        for i in range(600, 650):
            perfil[i] = 100
        return perfil

    def _setup_mqtt(self):
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(self.broker, self.port, 60)
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        logging.info("Simulador conectado ao MQTT Broker.")
        client.subscribe("actuator/motor")
        client.subscribe("cmd/speed_sp")
        client.subscribe("cmd/mode")
        client.subscribe("cmd/direction")

    def on_message(self, client, userdata, msg):
        payload = msg.payload.decode(errors="replace")

        if msg.topic in {"actuator/motor", "cmd/speed_sp"}:
            try:
                self.motor_command = float(payload)
            except ValueError:
                logging.warning("Comando de motor inválido recebido: %s", payload)
            return

        if msg.topic == "cmd/mode":
            self.modo_operacao = payload.strip().upper() or self.modo_operacao
            return

        if msg.topic == "cmd/direction":
            self.direcao = payload.strip().upper() or self.direcao

    def calc_physics(self, dt: float):
        """Atualiza a física do robô aplicando as Leis de Newton."""
        # Fator de declive: a gravidade ajuda ou atrapalha dependendo da inclinação
        forca_peso_x = self.gravidade * math.sin(math.radians(self.inclinacao_tunel))
        comando = max(-100.0, min(100.0, self.motor_command)) / 10.0
        if self.direcao == "LEFT":
            comando -= 0.35
        elif self.direcao == "RIGHT":
            comando += 0.35
        elif self.direcao == "STOP":
            comando *= 0.4

        aceleracao_real = comando - (forca_peso_x if self.velocidade > 0 else 0)

        # Atrito viscoso simples
        aceleracao_real -= self.velocidade * 0.12

        self.velocidade += aceleracao_real * dt
        self.pos_x += self.velocidade * dt
        self.velocidade = max(-4.0, min(14.0, self.velocidade))
        self.pos_x = max(0.0, self.pos_x)

        # Atualizar Encoder
        novo_metro = int(self.pos_x / 10.0)  # Cada 10 pixels = 1 metro
        if novo_metro > self.metros_percorridos:
            self.metros_percorridos = novo_metro
            self.encoder_state = not self.encoder_state
            self.client.publish("sensor/encoder", int(self.encoder_state))

    def _publish_telemetry(self, leitura_lidar: int):
        self.client.publish("sensor/lidar", leitura_lidar)
        self.client.publish("sensor/imu", f"{self.inclinacao_tunel:.1f}")
        payload = {
            "pos_x": round(self.pos_x, 2),
            "distance_m": round(self.pos_x / 10.0, 2),
            "velocidade": round(self.velocidade, 2),
            "lidar": int(leitura_lidar),
            "imu": round(self.inclinacao_tunel, 1),
            "encoder": int(self.encoder_state),
            "mode": self.modo_operacao,
            "direction": self.direcao,
        }
        self.client.publish("telemetry/robot", json.dumps(payload))

    def _draw_background(self, screen):
        screen.fill((11, 18, 32))
        pygame.draw.rect(screen, (20, 28, 46), (0, 60, 1200, 420))
        pygame.draw.rect(screen, (34, 197, 94), (0, 476, 1200, 24))
        pygame.draw.line(screen, (148, 163, 184), (0, 288), (1200, 288), 2)
        for x in range(0, 1200, 80):
            pygame.draw.line(screen, (31, 41, 55), (x, 90), (x, 460), 1)

    def _draw_tunnel_profile(self, screen, leitura_lidar: int):
        ceiling_y = max(80, min(320, leitura_lidar))
        pygame.draw.rect(screen, (71, 85, 105), (0, 0, 1200, ceiling_y))
        pygame.draw.rect(screen, (100, 116, 139), (0, ceiling_y - 12, 1200, 12))

    def _draw_robot(self, screen):
        robot_x = 520
        robot_y = 360
        body_rect = pygame.Rect(robot_x, robot_y, 160, 64)
        pygame.draw.rect(screen, (34, 197, 94), body_rect, border_radius=12)
        pygame.draw.rect(screen, (187, 247, 208), body_rect, 3, border_radius=12)
        pygame.draw.rect(
            screen, (15, 23, 42), (robot_x + 18, robot_y + 14, 42, 24), border_radius=6
        )
        pygame.draw.rect(
            screen, (15, 23, 42), (robot_x + 66, robot_y + 14, 40, 24), border_radius=6
        )
        pygame.draw.rect(
            screen, (15, 23, 42), (robot_x + 112, robot_y + 14, 30, 24), border_radius=6
        )
        pygame.draw.circle(screen, (148, 163, 184), (robot_x + 28, robot_y + 68), 12)
        pygame.draw.circle(screen, (148, 163, 184), (robot_x + 132, robot_y + 68), 12)
        pygame.draw.line(
            screen,
            (225, 29, 72),
            (robot_x + 20, robot_y - 10),
            (robot_x + 20, robot_y + 14),
            4,
        )
        pygame.draw.circle(screen, (225, 29, 72), (robot_x + 20, robot_y - 16), 6)

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

            self.calc_physics(dt)

            # Leitura do LIDAR baseada na posição X
            idx_teto = int(self.pos_x) % len(self.perfil_teto)
            leitura_lidar = self.perfil_teto[idx_teto]

            self._publish_telemetry(leitura_lidar)
            self._draw_background(screen)
            self._draw_tunnel_profile(screen, leitura_lidar)
            self._draw_robot(screen)

            img = font.render(
                f"LIDAR {leitura_lidar} | POS {self.pos_x:.1f} px | VEL {self.velocidade:.2f} | MODO {self.modo_operacao} | DIR {self.direcao}",
                True,
                (248, 250, 252),
            )
            screen.blit(img, (28, 18))

            speed_img = small_font.render(
                "MQTT: actuator/motor, cmd/speed_sp, cmd/mode, cmd/direction -> sensor/#, telemetry/robot",
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
