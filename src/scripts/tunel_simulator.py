"""
Módulo de Simulação Física do Túnel (Pygame).

Este módulo atua como o ambiente (planta) para o robô. Ele lê o esforço
do motor do controlador C++ via MQTT, calcula a cinemática considerando
a inclinação do túnel (IMU) e publica as leituras dos sensores (Lidar e Encoder).
"""

import pygame
import paho.mqtt.client as mqtt
import math
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


class TunelSimulator:
    """
    Classe principal do Simulador 2D do Túnel.
    """

    def __init__(self, broker: str = "localhost", port: int = 1883):
        self.broker = broker
        self.port = port
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION1, client_id="Python_Simulador"
        )

        # Variáveis Físicas do Robô
        self.pos_x = 0.0
        self.velocidade = 0.0
        self.aceleracao_motor = 0.0
        self.inclinacao_tunel = 5.0  # Graus (simulando declive - Ponto Extra)
        self.gravidade = 9.81
        self.metros_percorridos = 0
        self.encoder_state = False

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
        self.client.subscribe("actuator/motor")

    def on_message(self, client, userdata, msg):
        if msg.topic == "actuator/motor":
            # Recebe o valor do PID em C++ (-100 a 100)
            esforco = float(msg.payload.decode())
            self.aceleracao_motor = esforco / 10.0  # Fator de conversão arbitrário

    def calc_physics(self, dt: float):
        """Atualiza a física do robô aplicando as Leis de Newton."""
        # Fator de declive: a gravidade ajuda ou atrapalha dependendo da inclinação
        forca_peso_x = self.gravidade * math.sin(math.radians(self.inclinacao_tunel))
        aceleracao_real = self.aceleracao_motor - (
            forca_peso_x if self.velocidade > 0 else 0
        )

        # Atrito viscoso simples
        aceleracao_real -= self.velocidade * 0.1

        self.velocidade += aceleracao_real * dt
        self.pos_x += self.velocidade * dt

        # Atualizar Encoder
        novo_metro = int(self.pos_x / 10.0)  # Cada 10 pixels = 1 metro
        if novo_metro > self.metros_percorridos:
            self.metros_percorridos = novo_metro
            self.encoder_state = not self.encoder_state
            self.client.publish("sensor/encoder", int(self.encoder_state))

    def run(self):
        """Loop principal do simulador integrado com Pygame."""
        pygame.init()
        screen = pygame.display.set_mode((800, 400))
        pygame.display.set_caption("Simulador Físico do Túnel (ATR)")
        clock = pygame.time.Clock()

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

            # Publicar telemetria
            self.client.publish("sensor/lidar", leitura_lidar)
            self.client.publish("sensor/imu", self.inclinacao_tunel)

            # Renderização Básica
            screen.fill((50, 50, 50))
            # Desenhar o teto
            pygame.draw.rect(screen, (100, 100, 100), (0, 0, 800, leitura_lidar))
            # Desenhar Robô
            pygame.draw.rect(
                screen, (0, 255, 0), (400, 350, 40, 20)
            )  # Robô fixo no centro visual

            # Textos de Debug
            font = pygame.font.SysFont(None, 24)
            img = font.render(
                f"LIDAR: {leitura_lidar} | POS: {self.metros_percorridos}m | IMU: {self.inclinacao_tunel}°",
                True,
                (255, 255, 255),
            )
            screen.blit(img, (20, 20))

            pygame.display.flip()

        pygame.quit()
        self.client.loop_stop()


if __name__ == "__main__":
    sim = TunelSimulator()
    sim.run()
