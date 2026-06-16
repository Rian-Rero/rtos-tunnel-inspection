"""Painéis da GUI do operador; cada painel controla seus componentes e estado.

Três painéis:
  * *ControlsPanel* — botões de modo/direção, controle de velocidade e câmera.
  * *TelemetryPanel* — cartões de métricas somente leitura (LIDAR, IMU etc.).
  * *PreviewPanel*   — canvas ao vivo renderizando o túnel e o robô.

Todos os painéis enviam comandos pela função ``on_command(topic, payload)``;
eles nunca acessam o cliente MQTT diretamente.
"""

from __future__ import annotations

import math
import tkinter as tk
from tkinter import ttk
from typing import Callable

from config import Topics, Limits
from models import RobotTelemetry
from rendering import TkinterRobotRenderer, TkRobotState
from simulator.terrain import slope_label, slope_color_hex

__all__ = ["ControlsPanel", "TelemetryPanel", "PreviewPanel"]

## Assinatura da função usada pelos painéis para publicar comandos.
_CommandCallback = Callable[[str, str | int | float], None]


class ControlsPanel:
    """Controles de modo, direção, velocidade e câmera."""

    def __init__(self, parent: ttk.Frame, on_command: _CommandCallback) -> None:
        """Cria o painel de comandos e recebe a função de publicação."""
        ## Função usada para enviar comandos MQTT.
        self._cmd = on_command
        ## Texto exibido com o valor atual do seletor de velocidade.
        self._speed_var = tk.StringVar(value="0 %")
        ## Flag que evita publicar enquanto o valor é sincronizado pela GUI.
        self._updating_speed = False
        ## Controle deslizante de velocidade.
        self.speed_slider: ttk.Scale
        self._build(parent)

    def _build(self, parent: ttk.Frame) -> None:
        """Monta botões de modo, direção, velocidade e câmera."""
        ttk.Label(parent, text="Comandos", style="Section.TLabel").pack(anchor="w")
        ttk.Label(
            parent,
            text="Envie comandos de modo, direção, velocidade e gatilho da câmera.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(4, 16))

        modes = ttk.Frame(parent, style="Card.TFrame")
        modes.pack(fill="x", pady=(0, 14))
        ttk.Button(
            modes, text="Modo AUTO", style="Accent.TButton", command=self._set_auto
        ).pack(side="left", expand=True, fill="x", padx=(0, 6))
        ttk.Button(
            modes, text="Modo MANUAL", style="Accent.TButton", command=self._set_manual
        ).pack(side="right", expand=True, fill="x")

        dirs = ttk.Frame(parent, style="Card.TFrame")
        dirs.pack(fill="x", pady=(0, 14))
        ttk.Button(
            dirs,
            text="◀",
            style="Accent.TButton",
            command=lambda: self._set_direction("LEFT"),
        ).pack(side="left", expand=True, fill="x", padx=(0, 4))
        ttk.Button(
            dirs,
            text="⏹ STOP",
            style="Accent.TButton",
            command=lambda: self._set_direction("STOP"),
        ).pack(side="left", expand=True, fill="x", padx=4)
        ttk.Button(
            dirs,
            text="▶",
            style="Accent.TButton",
            command=lambda: self._set_direction("RIGHT"),
        ).pack(side="right", expand=True, fill="x", padx=(4, 0))

        speed_frame = ttk.Frame(parent, style="Card.TFrame")
        speed_frame.pack(fill="x", pady=(0, 14))
        ttk.Label(speed_frame, text="Velocidade", style="MetricLabel.TLabel").pack(
            anchor="w"
        )
        ttk.Label(
            speed_frame, textvariable=self._speed_var, style="MetricValue.TLabel"
        ).pack(anchor="w")
        self.speed_slider = ttk.Scale(
            speed_frame,
            from_=0,
            to=100,
            orient="horizontal",
            command=self._on_speed_change,
        )
        self.speed_slider.pack(fill="x", pady=(6, 0))

        ttk.Button(
            parent,
            text="📷 Disparar Câmera",
            style="Accent.TButton",
            command=self._trigger_camera,
        ).pack(fill="x", pady=(0, 8))

    # ── comandos ─────────────────────────────────────────────────────────────

    def _set_auto(self) -> None:
        """Envia comando para colocar o robô em modo automático."""
        self._cmd(Topics.CMD_MODE, "AUTO")

    def _set_manual(self) -> None:
        """Envia comando para modo manual e zera o movimento."""
        self._cmd(Topics.CMD_MODE, "MANUAL")
        self._cmd(Topics.CMD_DIRECTION, "STOP")
        self.set_speed(0)

    def _set_direction(self, direction: str) -> None:
        """Envia direção manual e aplica velocidade padrão quando necessário."""
        self._cmd(Topics.CMD_MODE, "MANUAL")
        if direction == "STOP":
            self._cmd(Topics.CMD_DIRECTION, "STOP")
            self.set_speed(0)
            return
        if int(float(self.speed_slider.get())) == 0:
            self.set_speed(Limits.SPEED_DEFAULT_MANUAL)
        self._cmd(Topics.CMD_DIRECTION, direction)

    def _on_speed_change(self, value) -> None:
        """Publica novo setpoint quando o controle de velocidade muda."""
        speed = int(float(value))
        self._speed_var.set(f"{speed} %")
        if not self._updating_speed:
            self._cmd(Topics.CMD_SPEED, speed)

    def _trigger_camera(self) -> None:
        """Solicita uma captura de câmera ao serviço de inspeção."""
        self._cmd(Topics.CMD_CAMERA, 1)

    def set_speed(self, speed: int) -> None:
        """Sincroniza o controle visual de velocidade e publica o valor limitado."""
        speed = max(Limits.SPEED_MIN, min(Limits.SPEED_MAX, speed))
        self._updating_speed = True
        try:
            self.speed_slider.set(speed)
        finally:
            self._updating_speed = False
        self._speed_var.set(f"{speed} %")
        self._cmd(Topics.CMD_SPEED, speed)


class TelemetryPanel:
    """Cartões de exibição de métricas somente leitura."""

    def __init__(self, parent: ttk.Frame) -> None:
        """Cria variáveis de texto e monta os cartões de métricas."""
        ## Variáveis Tkinter indexadas pelo nome da métrica.
        self._vars: dict[str, tk.StringVar] = {}
        ## Labels de valores que precisam acompanhar a largura do painel.
        self._value_labels: list[ttk.Label] = []
        self._build(parent)
        parent.bind("<Configure>", self._update_value_wraplength, add="+")

    def _build(self, parent: ttk.Frame) -> None:
        """Monta a lista de cartões de telemetria."""
        ttk.Label(parent, text="Telemetria", style="Section.TLabel").pack(anchor="w")
        ttk.Label(
            parent,
            text="Dados em tempo real recebidos via MQTT do núcleo C++.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(4, 16))

        metrics = [
            ("lidar", "LIDAR (m)"),
            ("imu", "IMU (°)"),
            ("encoder", "Encoder"),
            ("position", "Posição"),
            ("conf", "Confiança YOLO"),
            ("mode", "Modo"),
            ("yolo", "Inspeção"),
        ]
        for key, title in metrics:
            self._vars[key] = tk.StringVar(value="---")
            self._metric_card(parent, title, self._vars[key])

    def _metric_card(self, parent, title: str, var: tk.StringVar) -> None:
        """Cria um cartão individual para uma métrica textual."""
        card = ttk.Frame(parent, style="Card.TFrame")
        card.pack(fill="x", pady=(0, 10))
        ttk.Label(card, text=title, style="MetricLabel.TLabel").pack(anchor="w")
        value = ttk.Label(
            card,
            textvariable=var,
            style="MetricValue.TLabel",
            justify="left",
        )
        value.pack(anchor="w", fill="x", pady=(2, 0))
        self._value_labels.append(value)

    def _update_value_wraplength(self, event: tk.Event) -> None:
        """Mantém textos longos dentro dos cartões de telemetria."""
        wraplength = max(180, event.width - 42)
        for label in self._value_labels:
            label.configure(wraplength=wraplength)

    def update(self, telemetry: RobotTelemetry, yolo_state: str) -> None:
        """Atualiza todos os cartões com a última telemetria recebida."""
        lbl = slope_label(telemetry.imu)
        self._vars["lidar"].set(f"{telemetry.lidar:.0f}")
        self._vars["imu"].set(f"{telemetry.imu:+.1f}° | {lbl}")
        self._vars["encoder"].set(str(telemetry.encoder))
        self._vars["position"].set(f"{telemetry.distance_m:.2f} m")
        self._vars["conf"].set(f"{telemetry.confidence_level:.2f}")
        self._vars["mode"].set(telemetry.mode)
        self._vars["yolo"].set(yolo_state)


class PreviewPanel:
    """Canvas que renderiza o perfil do túnel e o robô em tempo real."""

    ## Intervalo entre redesenhos da pré-visualização, em milissegundos.
    _ANIMATION_INTERVAL_MS = 40

    def __init__(self, parent: ttk.Frame) -> None:
        """Cria o canvas de pré-visualização e inicia a animação."""
        ## Renderizador Tkinter compartilhado para o robô.
        self._renderer = TkinterRobotRenderer()
        ## Última telemetria recebida.
        self._telemetry = RobotTelemetry()
        ## Histórico usado para desenhar o perfil do túnel.
        self._history: list[RobotTelemetry] = []
        ## Ângulo acumulado usado para animar esteiras e rodas.
        self._preview_angle: float = 0.0
        ## Sinal de direção usado para animar o movimento.
        self._direction_sign: int = 1
        ## Texto de estado do túnel exibido acima do canvas.
        self._tunnel_var = tk.StringVar(value="Túnel ativo")
        ## Canvas onde túnel e robô são desenhados.
        self._canvas: tk.Canvas
        self._build(parent)
        self._animate()

    def _build(self, parent: ttk.Frame) -> None:
        """Monta rótulos e canvas da pré-visualização."""
        ttk.Label(parent, text="Vista do carrinho", style="Section.TLabel").pack(
            anchor="w"
        )
        ttk.Label(
            parent,
            text="Pré-visualização do robô sincronizada com a telemetria MQTT.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(4, 12))
        ttk.Label(parent, textvariable=self._tunnel_var, style="Status.TLabel").pack(
            anchor="w", pady=(0, 10)
        )
        self._canvas = tk.Canvas(
            parent, width=380, height=460, bg="#09111f", highlightthickness=0
        )
        self._canvas.pack(fill="both", expand=True)

    def update(
        self, telemetry: RobotTelemetry, history: list[RobotTelemetry], yolo_state: str
    ) -> None:
        """Recebe a última telemetria e agenda o próximo desenho."""
        self._telemetry = telemetry
        self._history = history
        self._direction_sign = -1 if telemetry.direction == "LEFT" else 1
        self._tunnel_var.set(
            f"Túnel ativo | modo {telemetry.mode} | direção {telemetry.direction} | velocidade {telemetry.velocidade:.2f}"
        )

    def _animate(self) -> None:
        """Atualiza o ângulo visual e agenda o próximo quadro."""
        if abs(self._telemetry.velocidade) > 0.05:
            self._preview_angle += (
                abs(self._telemetry.velocidade) * 0.12 * self._direction_sign
            )
        self._draw()
        self._canvas.after(self._ANIMATION_INTERVAL_MS, lambda: self._animate())

    def _draw(self) -> None:
        """Redesenha o túnel, o robô e os indicadores de telemetria."""
        canvas = self._canvas
        canvas.delete("all")

        w = int(canvas.winfo_width() or 360)
        h = int(canvas.winfo_height() or 460)

        canvas.create_rectangle(0, 0, w, h, fill="#09111f", outline="")
        canvas.create_rectangle(
            26, 26, w - 26, h - 68, fill="#0f172a", outline="#1f2937", width=2
        )
        canvas.create_rectangle(34, 34, w - 34, h - 76, fill="#111827", outline="")
        canvas.create_rectangle(34, h - 120, w - 34, h - 76, fill="#0b1220", outline="")

        lane_y = h // 2 + 34
        lbl = slope_label(self._telemetry.imu)
        color_hex = slope_color_hex(self._telemetry.imu)
        terrain_delta = max(-30, min(30, int(self._telemetry.imu * 5.0)))
        imu_tilt = math.sin(math.radians(self._telemetry.imu))

        canvas.create_line(
            52,
            lane_y + terrain_delta,
            w - 52,
            lane_y - terrain_delta,
            fill=color_hex,
            width=5,
            arrow=tk.LAST,
        )
        canvas.create_text(
            56,
            lane_y - 34,
            anchor="w",
            fill=color_hex,
            font=("Helvetica", 10, "bold"),
            text=f"TERRENO: {lbl}",
        )
        canvas.create_line(
            52, lane_y + 38, w - 52, lane_y + 38, fill="#334155", width=2
        )

        slope_x, slope_y = w - 166, 74
        slope_d = max(-24, min(24, int(self._telemetry.imu * 4.0)))
        canvas.create_line(
            slope_x,
            slope_y,
            slope_x + 112,
            slope_y - slope_d,
            fill=color_hex,
            width=5,
            arrow=tk.LAST,
        )
        canvas.create_text(
            slope_x,
            slope_y - 18,
            anchor="w",
            fill=color_hex,
            font=("Helvetica", 9, "bold"),
            text=f"{lbl} {self._telemetry.imu:+.1f}°",
        )
        for x in range(52, w - 52, 42):
            canvas.create_line(
                x, lane_y - 10, x + 16, lane_y - 10, fill="#475569", width=1
            )

        canvas.create_text(
            70,
            55,
            anchor="w",
            fill="#e2e8f0",
            font=("Helvetica", 12, "bold"),
            text="Túnel principal",
        )
        canvas.create_text(
            70,
            78,
            anchor="w",
            fill="#94a3b8",
            font=("Helvetica", 10),
            text=f"Posição {self._telemetry.pos_x:.1f} m",
        )

        cart_x, cart_y = self._compute_cart_position(w, h, lane_y, imu_tilt)
        self._draw_tunnel_path(canvas, w, h, imu_tilt, cart_x, cart_y)

        state = TkRobotState(
            preview_angle=self._preview_angle,
            velocidade=self._telemetry.velocidade,
            direction=self._telemetry.direction,
        )
        self._renderer.render(canvas, cart_x, cart_y, state)

        canvas.create_text(
            60,
            h - 46,
            anchor="w",
            fill="#cbd5e1",
            font=("Helvetica", 10),
            text=(
                f"LIDAR {self._telemetry.lidar:.0f} | "
                f"IMU {self._telemetry.imu:+.1f}° {lbl}"
            ),
            width=max(160, w - 120),
        )
        canvas.create_text(
            60,
            h - 24,
            anchor="w",
            fill="#cbd5e1",
            font=("Helvetica", 10),
            text=(
                f"Encoder {self._telemetry.encoder} | "
                f"Velocidade {self._telemetry.velocidade:.2f}"
            ),
            width=max(160, w - 120),
        )

    def _path_transform(self, w: int, h: int, imu_tilt: float):
        """Calcula pontos do caminho ordenados espacialmente a partir do histórico.

        Ordenar por pos_x (não por tempo) garante que o perfil do túnel seja
        desenhado corretamente independente da direção de navegação.
        Retorna (path_pts, min_x, scale_x); lista vazia quando não há histórico.
        """
        samples = self._history
        if not samples:
            return [], 0.0, 1.0

        min_x = min(s.pos_x for s in samples)
        max_x = max(s.pos_x for s in samples)
        span = max(1.0, max_x - min_x)
        scale_x = (w - 140) / span
        track_top, track_bot = 118, h - 118
        lane_shift = imu_tilt * 34.0

        path_pts = []
        for s in sorted(samples, key=lambda s: s.pos_x):
            x = 70.0 + (s.pos_x - min_x) * scale_x
            y = (
                track_top
                + (s.lidar - 1.2) * 72.0
                + lane_shift
                + math.sin(s.pos_x / 8.0) * 4.0
            )
            path_pts.append((x, max(track_top - 30, min(track_bot, y))))

        return path_pts, min_x, scale_x

    def _compute_cart_position(self, w, h, lane_y, imu_tilt):
        """Calcula a posição do carrinho no canvas com base no histórico."""
        samples = self._history
        if not samples:
            cart_x = 100 + int((self._telemetry.pos_x * 10) % max(1, w - 220))
            cart_y = lane_y - 30 - int(imu_tilt * 18)
            return cart_x, cart_y

        _, min_x, scale_x = self._path_transform(w, h, imu_tilt)
        latest_px = 70.0 + (samples[-1].pos_x - min_x) * scale_x
        floor_wave = math.sin(self._telemetry.pos_x / 5.4) * 14.0
        return int(latest_px) - 70, int(lane_y - 76 - imu_tilt * 18 - floor_wave)

    def _draw_tunnel_path(self, canvas, w, h, imu_tilt, cart_x, cart_y):
        """Desenha o perfil de teto e os marcadores recentes de anomalia."""
        samples = self._history
        if not samples:
            canvas.create_text(
                70,
                112,
                anchor="w",
                text="Aguardando telemetria do C++ via MQTT",
                fill="#94a3b8",
                font=("Helvetica", 10, "bold"),
            )
            return

        path_pts, min_x, scale_x = self._path_transform(w, h, imu_tilt)

        outline = (
            [(40, 34)] + [(x, y - 18) for x, y in path_pts] + [(w - 40, 34), (40, 34)]
        )
        canvas.create_polygon(outline, fill="#475569", outline="#94a3b8", width=2)
        if len(path_pts) > 1:
            canvas.create_line(*sum(path_pts, ()), fill="#22c55e", width=4, smooth=True)

        track_top, track_bot = 118, h - 118
        lane_shift = imu_tilt * 34.0
        for s in samples[-8:]:
            dev = s.lidar - 2.0
            if abs(dev) < 0.35:
                continue
            x = int(70.0 + (s.pos_x - min_x) * scale_x)
            y_raw = (
                track_top
                + (s.lidar - 1.2) * 72.0
                + lane_shift
                + math.sin(s.pos_x / 8.0) * 4.0
            )
            y = int(max(track_top - 30, min(track_bot, y_raw)))
            fill = "#60a5fa" if dev > 0 else "#fb7185"
            label = "Buraco" if dev > 0 else "Saliência"
            canvas.create_oval(x - 6, y - 6, x + 6, y + 6, fill=fill, outline="")
            canvas.create_text(
                x, y - 18, text=label, fill=fill, font=("Helvetica", 8, "bold")
            )
