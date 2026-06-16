"""Aplicação principal do simulador de túnel.

*TunelSimulator* é um orquestrador enxuto: mantém o estado MQTT, executa
o loop principal do Pygame e delega a renderização para *TunnelScene* e
*PygameRobotRenderer*.
"""

from __future__ import annotations

import json
import logging
import os
import math
import time

import pygame

from config import Topics, Limits, MQTT_BROKER, MQTT_PORT, MQTT_QOS
from models import AnomalyMark, InspectionState, RobotTelemetry
from mqtt import MqttComponent
from rendering import PygameRobotRenderer, RobotRenderState
from .scene import SceneState, TunnelScene
from .terrain import ViewTransform, slope_label

__all__ = ["TunelSimulator"]

## Registrador do simulador Pygame.
logger = logging.getLogger(__name__)

## Ícones usados no HUD para representar a direção atual.
_DIR_ICON: dict[str, str] = {"LEFT": "←", "RIGHT": "→", "STOP": "■"}


class TunelSimulator(MqttComponent):
    """Visualizador 2D de túnel em Pygame guiado só por telemetria MQTT."""

    ## @var _telemetry
    # Última telemetria consolidada do robô.
    ## @var _inspection
    # Estado atual da inspeção visual.
    ## @var _target_pos_x
    # Posição alvo recebida via MQTT.
    ## @var _visual_pos_x
    # Posição suavizada usada na câmera.
    ## @var _reveal_pos_x
    # Posição máxima já revelada no mapa.
    ## @var _robot_history
    # Histórico bruto de telemetria.
    ## @var _anomaly_marks
    # Marcadores visuais de anomalia.
    ## @var _preview_angle
    # Ângulo acumulado de animação do robô.
    ## @var _view
    # Transformação de mundo para tela.
    ## @var _scene
    # Renderizador do ambiente do túnel.
    ## @var _last_camera_shot
    # Último recorte ao vivo da câmera simulada.
    ## @var _perfect_anomaly_shot
    # Melhor recorte capturado da última anomalia.

    def __init__(self, broker: str = MQTT_BROKER, port: int = MQTT_PORT) -> None:
        """Inicializa estado de telemetria, cena e renderizadores do simulador."""
        super().__init__(broker, port, "Python_Simulador")

        # ── Estado do robô ───────────────────────────────────────────────────
        self._telemetry = RobotTelemetry()  ##< Última telemetria consolidada do robô.
        self._inspection = InspectionState()  ##< Estado atual da inspeção visual.
        self._target_pos_x: float = 0.0  ##< Posição alvo recebida via MQTT.
        self._visual_pos_x: float = 0.0  ##< Posição suavizada usada na câmera.
        self._reveal_pos_x: float = 0.0  ##< Posição máxima já revelada no mapa.
        self._robot_history: list[dict] = []  ##< Histórico bruto de telemetria.
        self._anomaly_marks: list[AnomalyMark] = []  ##< Marcadores visuais de anomalia.

        # ── Estado de animação ───────────────────────────────────────────────
        self._preview_angle: float = 0.0  ##< Ângulo acumulado de animação do robô.
        self._view = ViewTransform()  ##< Transformação de mundo para tela.

        # ── Renderizadores ───────────────────────────────────────────────────
        self._scene = TunnelScene()  ##< Renderizador do ambiente do túnel.
        self._robot_renderer = PygameRobotRenderer()  ##< Renderizador do robô.

        self._last_camera_shot = None  ##< Último recorte ao vivo da câmera simulada.
        self._perfect_anomaly_shot = (
            None  ##< Melhor recorte capturado da última anomalia.
        )

    # ── ganchos MQTT ─────────────────────────────────────────────────────────

    def _on_connect(self, client) -> None:
        """Assina telemetria do robô, resultado YOLO e estado de inspeção."""
        client.subscribe(Topics.TELEMETRY_ROBOT, qos=MQTT_QOS)
        client.subscribe(Topics.TELEMETRY_YOLO, qos=MQTT_QOS)
        client.subscribe(Topics.STATE_INSPECTION, qos=MQTT_QOS)

    def _on_message(self, topic: str, payload: str) -> None:
        """Encaminha mensagens MQTT para os tratadores de estado do simulador."""
        if topic == Topics.TELEMETRY_ROBOT:
            self._handle_robot_telemetry(payload)
        elif topic == Topics.TELEMETRY_YOLO:
            self._handle_yolo(payload)
        elif topic == Topics.STATE_INSPECTION:
            self._handle_inspection_state(payload)

    def _handle_robot_telemetry(self, payload: str) -> None:
        """Atualiza telemetria, histórico e marcadores de anomalia do LIDAR."""
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            logger.warning("Telemetria inválida: %s", payload)
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
        """Atualiza o estado visual a partir do resultado de inferência YOLO."""
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

        # Se o YOLO achou algo, cruza a informação com o LIDAR para exibir o tipo geológico.
        if data.get("anomalia_detectada") and self._anomaly_marks:
            self._inspection.last_type = self._anomaly_marks[-1].kind.upper()
        else:
            self._inspection.last_type = str(
                data.get("tipo", data.get("anomalia_visual_simulada", status))
            )

        self._inspection.yolo_state = (
            f"{status} | confiança {self._inspection.last_confidence:.2f}"
            if isinstance(conf, (int, float))
            else status
        )
        self._inspection.result_expires_at = time.monotonic() + Limits.YOLO_RESULT_TTL_S

    def _handle_inspection_state(self, payload: str) -> None:
        """Atualiza a flag de inspeção em andamento publicada pelo núcleo C++."""
        self._inspection.active = payload.strip() == "1"
        if self._inspection.active:
            self._inspection.yolo_state = "Inspeção em andamento..."
            self._inspection.result_expires_at = None
        elif self._inspection.result_expires_at is None:
            self._inspection.yolo_state = "Sistema em regime normal"

    # ── loop principal ───────────────────────────────────────────────────────

    def run(self) -> None:
        """Executa a janela Pygame, consome eventos e renderiza a cena."""
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

                # ── Monta o retrato de estado da cena ───────────────────────
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

                # ── Renderização ────────────────────────────────────────────
                self._scene.draw_background(screen)
                self._scene.draw_tunnel_profile(screen, scene_state, self._view)

                width = screen.get_width()
                height = screen.get_height()
                rx = int(width / 2 - 88)
                fx = rx + 176

                # Vídeo ao vivo: Continua a gravar à frente do robô enquanto inspeciona
                if self._inspection.active:
                    camera_target_x = rx + 40
                    lidar_val = self._telemetry.lidar
                    imu_val = self._telemetry.imu

                    roof_y = 178 - (lidar_val - 2.0) * 82.0
                    roof_y += (
                        math.sin(math.radians(imu_val))
                        * (camera_target_x - width / 2)
                        * 0.045
                    )
                    camera_target_y = max(86, min(height - 230, int(roof_y)))

                    live_rect = pygame.Rect(0, 0, 240, 120)
                    live_rect.center = (camera_target_x, camera_target_y - 15)
                    safe_live = live_rect.clip(screen.get_rect())

                    if safe_live.width > 0 and safe_live.height > 0:
                        self._last_camera_shot = screen.subsurface(safe_live).copy()

                # A "Foto Perfeita": Evolui enquanto o robô constrói a anomalia
                if self._anomaly_marks:
                    last_mark = self._anomaly_marks[-1]
                    # Calcula a distância que o robô já andou após detectar a anomalia
                    dist_passed = self._telemetry.pos_x - last_mark.pos_x

                    # Continua a fotografar a anomalia até o robô passar 1.2 metros por ela.
                    # Isso dá tempo do LIDAR desenhar a anomalia completa na tela
                    if 0.0 <= dist_passed <= 1.2:
                        mark_x = self._view.screen_x(last_mark.pos_x)
                        mark_y = 178 - (last_mark.lidar - 2.0) * 82.0
                        mark_y += (
                            math.sin(math.radians(self._telemetry.imu))
                            * (mark_x - width / 2)
                            * 0.045
                        )

                        anom_rect = pygame.Rect(0, 0, 240, 120)
                        anom_rect.center = (int(mark_x), int(mark_y) - 10)
                        safe_anom = anom_rect.clip(screen.get_rect())

                        if safe_anom.width == 240 and safe_anom.height == 120:
                            self._perfect_anomaly_shot = screen.subsurface(
                                safe_anom
                            ).copy()

                # Aplica a sombra geral do túnel
                self._scene.draw_overlay(screen)

                # Se está inspecionando: Mostra o vídeo ao vivo se mexendo.
                # Se terminou (YOLO deu resultado): Mostra a foto da anomalia já desenhada inteira!
                if self._inspection.active:
                    display_img = self._last_camera_shot
                else:
                    display_img = (
                        self._perfect_anomaly_shot
                        if self._perfect_anomaly_shot
                        else self._last_camera_shot
                    )

                self._scene.draw_camera_monitor(screen, self._inspection, display_img)

                # Desenha o robô por cima de tudo
                robot_state = RobotRenderState(
                    spin_angle=self._preview_angle,
                    inspection_active=self._inspection.active,
                    direction=self._telemetry.direction,
                    encoder_count=self._telemetry.encoder,
                    velocidade=self._telemetry.velocidade,
                )
                self._robot_renderer.render(screen, rx, fx, floor_fn, robot_state)

                # ── HUD ──────────────────────────────────────────────────────
                lbl = slope_label(self._telemetry.imu)
                dir_icon = _DIR_ICON.get(
                    self._telemetry.direction, self._telemetry.direction
                )
                header = (
                    f"POS {self._telemetry.distance_m:.2f} m | VEL {self._telemetry.velocidade:.1f}% | "
                    f"LIDAR {self._telemetry.lidar:.2f} m | IMU {self._telemetry.imu:+.1f}° {lbl} | "
                    f"MODO {self._telemetry.mode} | DIR {dir_icon}"
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
                footer_y = screen.get_height() - 50
                self._blit_fit_text(
                    screen,
                    font_sub,
                    f"Inspeção YOLO: {self._inspection.yolo_state}",
                    (28, footer_y),
                    screen.get_width() - 56,
                    (148, 163, 184),
                )
                self._blit_fit_text(
                    screen,
                    font_sub,
                    f"Encoder {self._telemetry.encoder}",
                    (28, footer_y + 24),
                    screen.get_width() - 56,
                    (148, 163, 184),
                )

                pygame.display.flip()
        finally:
            pygame.quit()
            self.disconnect()

    # ── auxiliares ───────────────────────────────────────────────────────────

    def _tick_animation(self, dt: float) -> None:
        """Atualiza interpolação de posição, revelação de mapa e animações."""
        alpha = min(1.0, max(0.08, dt * 7.0))
        self._visual_pos_x += (self._target_pos_x - self._visual_pos_x) * alpha

        reveal_target = self._visual_pos_x + 0.85
        if reveal_target > self._reveal_pos_x:
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
                self._last_camera_shot = None
                self._perfect_anomaly_shot = None

    def _create_window(self) -> tuple[pygame.Surface, pygame.time.Clock]:
        """Cria a janela Pygame em posição conveniente para depuração."""
        info = pygame.display.Info()
        sw = int(getattr(info, "current_w", 1920) or 1920)
        sh = int(getattr(info, "current_h", 1080) or 1080)
        ww = min(1200, max(920, sw - 80))
        wh = min(680, max(600, sh - 140))
        if "SDL_VIDEO_WINDOW_POS" not in os.environ:
            if sw >= 2200:
                wx, wy = 1240, 40
            elif sh >= 1260:
                wx, wy = 24, 780
            else:
                wx, wy = 160, 130
            os.environ["SDL_VIDEO_WINDOW_POS"] = f"{wx},{wy}"
        screen = pygame.display.set_mode((ww, wh))
        pygame.display.set_caption("Simulador do Túnel (ATR)")
        return screen, pygame.time.Clock()

    @staticmethod
    def _blit_fit_text(
        screen: pygame.Surface,
        font: pygame.font.Font,
        text: str,
        pos: tuple[int, int],
        max_width: int,
        color: tuple[int, int, int],
    ) -> None:
        """Desenha texto reduzindo-o com reticências quando excede a largura."""
        rendered = font.render(text, True, color)
        if rendered.get_width() <= max_width:
            screen.blit(rendered, pos)
            return

        ellipsis = "..."
        lo, hi = 0, len(text)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            candidate = font.render(text[:mid] + ellipsis, True, color)
            if candidate.get_width() <= max_width:
                lo = mid
            else:
                hi = mid - 1
        screen.blit(font.render(text[:lo] + ellipsis, True, color), pos)
