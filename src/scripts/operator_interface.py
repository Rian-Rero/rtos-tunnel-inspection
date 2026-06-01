"""
Interface Gráfica do Operador (GUI).

Painel principal para comando remoto, telemetria MQTT e visualização do carrinho.
"""

from __future__ import annotations

import json
import math
import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk

import paho.mqtt.client as mqtt


@dataclass
class RobotTelemetry:
    pos_x: float = 0.0
    velocidade: float = 0.0
    lidar: float = 0.0
    imu: float = 0.0
    encoder: int = 0
    mode: str = "MANUAL"
    direction: str = "STOP"


class OperatorGUI:
    """Janela de operação remota com visual mais rico e telemetria ao vivo."""

    def __init__(self, root: tk.Tk, broker: str = "localhost", port: int = 1883):
        self.root = root
        self.broker = broker
        self.port = port
        self.root.title("ATR - Operação Remota do Carrinho")
        self.root.geometry("1280x760")
        self.root.minsize(1100, 680)
        self.root.configure(bg="#0f172a")

        self.telemetry = RobotTelemetry()
        self.connection_state = tk.StringVar(value="Conectando ao broker MQTT...")
        self.mode_state = tk.StringVar(value="MANUAL")
        self.direction_state = tk.StringVar(value="STOP")
        self.yolo_state = tk.StringVar(value="Aguardando inspeção...")
        self.lidar_state = tk.StringVar(value="---")
        self.imu_state = tk.StringVar(value="---")
        self.encoder_state = tk.StringVar(value="---")
        self.speed_state = tk.StringVar(value="0")
        self.position_state = tk.StringVar(value="0.0 m")
        self.confidence_state = tk.StringVar(value="0.00")
        self.tunnel_state = tk.StringVar(value="Túnel ativo")
        self.preview_angle = 0.0
        self.preview_direction = 1
        self.preview_phase = 0.0
        self.robot_history: list[RobotTelemetry] = []

        self.client = self._create_client()
        self._setup_styles()
        self._build_ui()
        self._setup_mqtt()
        self._start_preview_animation()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_client(self):
        try:
            return mqtt.Client(
                client_id="Python_GUI",
                callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
            )
        except TypeError:
            return mqtt.Client(client_id="Python_GUI")

    def _setup_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("Root.TFrame", background="#0f172a")
        style.configure("Header.TFrame", background="#111827")
        style.configure("Card.TFrame", background="#111827", relief="flat")
        style.configure("Panel.TFrame", background="#0f172a")
        style.configure(
            "Title.TLabel",
            background="#111827",
            foreground="#f8fafc",
            font=("Helvetica", 20, "bold"),
        )
        style.configure(
            "Subtitle.TLabel",
            background="#111827",
            foreground="#94a3b8",
            font=("Helvetica", 10),
        )
        style.configure(
            "Section.TLabel",
            background="#0f172a",
            foreground="#e2e8f0",
            font=("Helvetica", 11, "bold"),
        )
        style.configure(
            "MetricValue.TLabel",
            background="#111827",
            foreground="#f8fafc",
            font=("Helvetica", 22, "bold"),
        )
        style.configure(
            "MetricLabel.TLabel",
            background="#111827",
            foreground="#94a3b8",
            font=("Helvetica", 10),
        )
        style.configure(
            "Status.TLabel",
            background="#111827",
            foreground="#cbd5e1",
            font=("Helvetica", 11, "bold"),
        )
        style.configure(
            "Accent.TButton",
            font=("Helvetica", 11, "bold"),
            padding=(16, 10),
        )
        style.map(
            "Accent.TButton", relief=[("pressed", "sunken"), ("!pressed", "raised")]
        )

    def _build_ui(self):
        container = ttk.Frame(self.root, style="Root.TFrame")
        container.pack(fill="both", expand=True)

        header = ttk.Frame(container, style="Header.TFrame", padding=(24, 20))
        header.pack(fill="x")
        header.columnconfigure(0, weight=1)
        header.columnconfigure(1, weight=0)

        title_box = ttk.Frame(header, style="Header.TFrame")
        title_box.grid(row=0, column=0, sticky="w")
        ttk.Label(
            title_box, text="ATR - Operação Remota do Carrinho", style="Title.TLabel"
        ).pack(anchor="w")
        ttk.Label(
            title_box,
            text="Controle de navegação, telemetria MQTT e inspeção visual em tempo real.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(4, 0))

        status_box = ttk.Frame(header, style="Header.TFrame")
        status_box.grid(row=0, column=1, sticky="e")
        ttk.Label(status_box, text="Conexão", style="Subtitle.TLabel").pack(anchor="e")
        ttk.Label(
            status_box, textvariable=self.connection_state, style="Status.TLabel"
        ).pack(anchor="e")

        body = ttk.Frame(container, style="Root.TFrame", padding=(20, 20, 20, 16))
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1, uniform="main")
        body.columnconfigure(1, weight=1, uniform="main")
        body.columnconfigure(2, weight=1, uniform="main")
        body.rowconfigure(0, weight=1)

        self.controls_card = ttk.Frame(body, style="Card.TFrame", padding=20)
        self.controls_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self.telemetry_card = ttk.Frame(body, style="Card.TFrame", padding=20)
        self.telemetry_card.grid(row=0, column=1, sticky="nsew", padx=12)
        self.preview_card = ttk.Frame(body, style="Card.TFrame", padding=20)
        self.preview_card.grid(row=0, column=2, sticky="nsew", padx=(12, 0))

        self._build_controls_panel()
        self._build_telemetry_panel()
        self._build_preview_panel()

        footer = ttk.Frame(container, style="Panel.TFrame", padding=(20, 0, 20, 18))
        footer.pack(fill="x")
        ttk.Label(
            footer,
            text="MQTT: cmd/mode, cmd/direction, cmd/speed_sp, cmd/camera, telemetry/robot, telemetry/yolo, sensor/#",
            style="Subtitle.TLabel",
        ).pack(anchor="w")

    def _build_controls_panel(self):
        ttk.Label(self.controls_card, text="Comandos", style="Section.TLabel").pack(
            anchor="w"
        )
        ttk.Label(
            self.controls_card,
            text="Envie comandos de modo, direção, velocidade e trigger da câmera.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(4, 16))

        modes = ttk.Frame(self.controls_card, style="Card.TFrame")
        modes.pack(fill="x", pady=(0, 14))
        ttk.Button(
            modes,
            text="Modo AUTO",
            style="Accent.TButton",
            command=lambda: self.publish_cmd("cmd/mode", "AUTO"),
        ).pack(side="left", expand=True, fill="x", padx=(0, 6))
        ttk.Button(
            modes,
            text="Modo MANUAL",
            style="Accent.TButton",
            command=lambda: self.publish_cmd("cmd/mode", "MANUAL"),
        ).pack(side="left", expand=True, fill="x", padx=(6, 0))

        direction = ttk.Frame(self.controls_card, style="Card.TFrame")
        direction.pack(fill="x", pady=(0, 14))
        ttk.Button(
            direction,
            text="Esquerda",
            style="Accent.TButton",
            command=lambda: self.publish_cmd("cmd/direction", "LEFT"),
        ).pack(side="left", expand=True, fill="x", padx=(0, 6))
        ttk.Button(
            direction,
            text="Parar",
            style="Accent.TButton",
            command=lambda: self.publish_cmd("cmd/direction", "STOP"),
        ).pack(side="left", expand=True, fill="x", padx=6)
        ttk.Button(
            direction,
            text="Direita",
            style="Accent.TButton",
            command=lambda: self.publish_cmd("cmd/direction", "RIGHT"),
        ).pack(side="left", expand=True, fill="x", padx=(6, 0))

        slider_box = ttk.Frame(self.controls_card, style="Card.TFrame")
        slider_box.pack(fill="x", pady=(0, 14))
        ttk.Label(
            slider_box, text="Setpoint de velocidade", style="MetricLabel.TLabel"
        ).pack(anchor="w")
        self.speed_slider = tk.Scale(
            slider_box,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            resolution=1,
            length=320,
            showvalue=False,
            troughcolor="#1f2937",
            bg="#111827",
            fg="#e2e8f0",
            highlightthickness=0,
            activebackground="#22c55e",
            command=self._update_speed,
        )
        self.speed_slider.pack(fill="x", pady=(6, 0))
        ttk.Label(
            slider_box, textvariable=self.speed_state, style="MetricValue.TLabel"
        ).pack(anchor="w", pady=(6, 0))

        camera_box = ttk.Frame(self.controls_card, style="Card.TFrame")
        camera_box.pack(fill="x", pady=(0, 14))
        ttk.Button(
            camera_box,
            text="Disparar inspeção visual",
            style="Accent.TButton",
            command=self._trigger_camera,
        ).pack(fill="x")

        inspection_box = ttk.Frame(self.controls_card, style="Card.TFrame")
        inspection_box.pack(fill="x")
        ttk.Label(
            inspection_box, text="Estado da inspeção", style="MetricLabel.TLabel"
        ).pack(anchor="w")
        ttk.Label(
            inspection_box,
            textvariable=self.yolo_state,
            style="Status.TLabel",
            wraplength=300,
        ).pack(anchor="w", pady=(6, 0))

    def _build_telemetry_panel(self):
        ttk.Label(self.telemetry_card, text="Telemetria", style="Section.TLabel").pack(
            anchor="w"
        )
        ttk.Label(
            self.telemetry_card,
            text="Leituras do simulador e resultado da inspeção visual.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(4, 16))

        self._metric_card(self.telemetry_card, "LIDAR", self.lidar_state)
        self._metric_card(self.telemetry_card, "IMU", self.imu_state)
        self._metric_card(self.telemetry_card, "Encoder", self.encoder_state)
        self._metric_card(self.telemetry_card, "Posição", self.position_state)
        self._metric_card(self.telemetry_card, "Confiança", self.confidence_state)

        mode_row = ttk.Frame(self.telemetry_card, style="Card.TFrame")
        mode_row.pack(fill="x", pady=(10, 0))
        ttk.Label(mode_row, text="Modo atual", style="MetricLabel.TLabel").pack(
            anchor="w"
        )
        ttk.Label(
            mode_row, textvariable=self.mode_state, style="MetricValue.TLabel"
        ).pack(anchor="w")
        ttk.Label(mode_row, text="Direção atual", style="MetricLabel.TLabel").pack(
            anchor="w", pady=(10, 0)
        )
        ttk.Label(
            mode_row, textvariable=self.direction_state, style="MetricValue.TLabel"
        ).pack(anchor="w")

    def _build_preview_panel(self):
        ttk.Label(
            self.preview_card, text="Vista do carrinho", style="Section.TLabel"
        ).pack(anchor="w")
        ttk.Label(
            self.preview_card,
            text="Pré-visualização do robô sincronizada com a telemetria MQTT.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(4, 12))

        tunnel_info = ttk.Frame(self.preview_card, style="Card.TFrame")
        tunnel_info.pack(fill="x", pady=(0, 10))
        ttk.Label(
            tunnel_info, textvariable=self.tunnel_state, style="Status.TLabel"
        ).pack(anchor="w")

        self.preview_canvas = tk.Canvas(
            self.preview_card,
            width=380,
            height=460,
            bg="#09111f",
            highlightthickness=0,
        )
        self.preview_canvas.pack(fill="both", expand=True)
        self._draw_robot_preview()

    def _metric_card(self, parent, title: str, variable: tk.StringVar):
        card = ttk.Frame(parent, style="Card.TFrame")
        card.pack(fill="x", pady=(0, 10))
        ttk.Label(card, text=title, style="MetricLabel.TLabel").pack(anchor="w")
        ttk.Label(card, textvariable=variable, style="MetricValue.TLabel").pack(
            anchor="w", pady=(2, 0)
        )

    def publish_cmd(self, topic: str, payload: str | float | int):
        self.client.publish(topic, str(payload))

    def _update_speed(self, value):
        speed = int(float(value))
        self.speed_state.set(str(speed))
        self.publish_cmd("cmd/speed_sp", speed)
        self.preview_direction = 1 if speed >= 0 else -1
        self._draw_robot_preview()

    def _trigger_camera(self):
        self.publish_cmd("cmd/camera", 1)
        self.root.after(150, lambda: self.publish_cmd("cmd/camera", 0))

    def _setup_mqtt(self):
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        try:
            self.client.connect(self.broker, self.port, 60)
        except OSError as exc:
            self.connection_state.set(f"Falha na conexão: {exc}")
            return
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        self.connection_state.set("Conectado ao broker MQTT")
        client.subscribe("telemetry/#")
        client.subscribe("sensor/#")
        client.subscribe("state/inspection")

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode(errors="replace")

        if topic == "telemetry/yolo":
            self.root.after(0, lambda: self._update_yolo_state(payload))
            return

        if topic == "telemetry/robot":
            self.root.after(0, lambda: self._update_robot(payload))
            return

        if topic == "sensor/lidar":
            self.root.after(0, lambda: self.lidar_state.set(payload))
        elif topic == "sensor/imu":
            self.root.after(0, lambda: self.imu_state.set(f"{payload}°"))
        elif topic == "sensor/encoder":
            self.root.after(0, lambda: self.encoder_state.set(payload))
        elif topic == "state/inspection":
            self.root.after(0, lambda: self._update_inspection_state(payload))

    def _update_inspection_state(self, payload: str):
        active = str(payload).strip() == "1"
        self.yolo_state.set(
            "Inspeção em andamento" if active else "Sistema em regime normal"
        )
        self._draw_robot_preview()

    def _update_yolo_state(self, payload: str):
        try:
            data = json.loads(payload)
            status = (
                "Anomalia detectada"
                if data.get("anomalia_detectada")
                else "Sem anomalia"
            )
            confidence = data.get("confianca")
            if isinstance(confidence, (int, float)):
                self.yolo_state.set(f"{status} | confiança {confidence:.2f}")
            else:
                self.yolo_state.set(status)
        except json.JSONDecodeError:
            self.yolo_state.set(payload)

    def _update_robot(self, payload: str):
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return

        pos_x = float(data.get("pos_x", self.telemetry.pos_x))
        velocidade = float(
            data.get("current_speed", data.get("velocidade", self.telemetry.velocidade))
        )
        lidar = float(
            data.get("lidar_distance_y", data.get("lidar", self.telemetry.lidar))
        )
        imu = float(data.get("imu", self.telemetry.imu))
        encoder = int(data.get("encoder", self.telemetry.encoder))
        mode = str(data.get("mode", self.telemetry.mode))
        raw_direction = data.get("direction", self.telemetry.direction)
        if isinstance(raw_direction, (int, float)):
            direction = {-1: "LEFT", 0: "STOP", 1: "RIGHT"}.get(
                int(raw_direction), "STOP"
            )
        else:
            direction = (
                str(data.get("direction_label", raw_direction)).upper()
                or self.telemetry.direction
            )
        distance_m = float(data.get("distance_m", pos_x / 10.0))

        self.telemetry = RobotTelemetry(
            pos_x, velocidade, lidar, imu, encoder, mode, direction
        )
        self.robot_history.append(self.telemetry)
        self.robot_history = self.robot_history[-240:]
        self.position_state.set(f"{distance_m:.2f} m")
        self.tunnel_state.set(
            f"Túnel ativo | modo {mode} | direção {direction} | velocidade {velocidade:.2f}"
        )
        self.mode_state.set(mode)
        self.direction_state.set(direction)
        self.lidar_state.set(f"{lidar:.0f}")
        self.imu_state.set(f"{imu:.1f}°")
        self.encoder_state.set(str(encoder))
        self.confidence_state.set(f"{float(data.get('confidence_level', 0.0)):.2f}")
        if direction == "LEFT":
            self.preview_direction = -1
        elif direction == "RIGHT":
            self.preview_direction = 1
        self._draw_robot_preview()

    def _start_preview_animation(self):
        self.preview_phase += max(0.04, abs(self.telemetry.velocidade) * 0.06)
        self.preview_angle += (
            max(0.08, abs(self.telemetry.velocidade) * 0.12) * self.preview_direction
        )
        self._draw_robot_preview()
        self.root.after(40, self._start_preview_animation)

    def _draw_robot_preview(self):
        canvas = self.preview_canvas
        canvas.delete("all")

        width = int(canvas.winfo_width() or 360)
        height = int(canvas.winfo_height() or 460)

        canvas.create_rectangle(0, 0, width, height, fill="#09111f", outline="")
        canvas.create_rectangle(
            26, 26, width - 26, height - 68, fill="#0f172a", outline="#1f2937", width=2
        )
        canvas.create_rectangle(
            34, 34, width - 34, height - 76, fill="#111827", outline=""
        )
        canvas.create_rectangle(
            34, height - 120, width - 34, height - 76, fill="#0b1220", outline=""
        )

        lane_y = height // 2 + 34
        canvas.create_line(52, lane_y, width - 52, lane_y, fill="#22c55e", width=3)
        canvas.create_line(
            52, lane_y + 38, width - 52, lane_y + 38, fill="#334155", width=2
        )
        for x in range(52, width - 52, 42):
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
            text=f"Posição {self.telemetry.pos_x:.1f} m",
        )

        samples = self.robot_history
        track_top = 118
        track_bottom = height - 118
        imu_tilt = math.sin(math.radians(self.telemetry.imu))
        lane_shift = imu_tilt * 34

        if samples:
            start_x = samples[0].pos_x
            max_x = max(sample.pos_x for sample in samples)
            span = max(1.0, max_x - start_x)
            scale_x = (width - 140) / span
            path_points = []
            for sample in samples:
                x = 70 + (sample.pos_x - start_x) * scale_x
                terrain_wave = math.sin((sample.pos_x / 14.0) + self.preview_phase) * 10
                y = track_top + (sample.lidar - 1.2) * 72 + lane_shift + terrain_wave
                y = max(track_top - 30, min(track_bottom, y))
                path_points.append((x, y))

            tunnel_outline = (
                [(40, 34)]
                + [(x, y - 18) for x, y in path_points]
                + [(width - 40, 34), (40, 34)]
            )
            canvas.create_polygon(
                tunnel_outline, fill="#475569", outline="#94a3b8", width=2
            )
            if len(path_points) > 1:
                canvas.create_line(
                    *sum(path_points, ()), fill="#22c55e", width=4, smooth=True
                )

            for sample, (x, y) in zip(samples[-8:], path_points[-8:]):
                if sample.lidar > 2.0:
                    fill = "#60a5fa"
                    label = "Buraco"
                elif sample.lidar < 2.0:
                    fill = "#fb7185"
                    label = "Saliencia"
                else:
                    fill = "#94a3b8"
                    label = "Normal"
                canvas.create_oval(x - 6, y - 6, x + 6, y + 6, fill=fill, outline="")
                canvas.create_text(
                    x, y - 18, text=label, fill=fill, font=("Helvetica", 8, "bold")
                )

            latest_x, latest_y = path_points[-1]
            cart_x = int(latest_x - 66)
            cart_y = int(latest_y - 78 - imu_tilt * 18)
        else:
            canvas.create_text(
                70,
                112,
                anchor="w",
                text="Aguardando telemetria do C++ via MQTT",
                fill="#94a3b8",
                font=("Helvetica", 10, "bold"),
            )
            cart_x = 100 + int((self.telemetry.pos_x * 10) % max(1, width - 220))
            cart_y = lane_y - 30 - int(imu_tilt * 18)

        canvas.create_rectangle(
            cart_x,
            cart_y,
            cart_x + 132,
            cart_y + 44,
            fill="#22c55e",
            outline="#86efac",
            width=2,
        )
        canvas.create_rectangle(
            cart_x + 20,
            cart_y + 8,
            cart_x + 112,
            cart_y + 26,
            fill="#0f172a",
            outline="",
        )
        canvas.create_rectangle(
            cart_x + 28,
            cart_y + 8,
            cart_x + 50,
            cart_y + 26,
            fill="#1e293b",
            outline="",
        )
        canvas.create_rectangle(
            cart_x + 58,
            cart_y + 8,
            cart_x + 80,
            cart_y + 26,
            fill="#1e293b",
            outline="",
        )
        canvas.create_rectangle(
            cart_x + 88,
            cart_y + 8,
            cart_x + 104,
            cart_y + 26,
            fill="#1e293b",
            outline="",
        )
        canvas.create_text(
            cart_x + 66,
            cart_y + 20,
            fill="#0f172a",
            font=("Helvetica", 11, "bold"),
            text="ATR",
        )

        wheel_radius = 17
        wheel_centers = [(cart_x + 28, cart_y + 48), (cart_x + 104, cart_y + 48)]
        for center in wheel_centers:
            canvas.create_oval(
                center[0] - wheel_radius,
                center[1] - wheel_radius,
                center[0] + wheel_radius,
                center[1] + wheel_radius,
                fill="#0f172a",
                outline="#cbd5e1",
                width=2,
            )
            for spoke in range(4):
                angle = self.preview_angle + spoke * (math.pi / 2)
                spoke_x = center[0] + math.cos(angle) * (wheel_radius - 2)
                spoke_y = center[1] + math.sin(angle) * (wheel_radius - 2)
                canvas.create_line(
                    center[0], center[1], spoke_x, spoke_y, fill="#e2e8f0", width=2
                )
            canvas.create_oval(
                center[0] - 3,
                center[1] - 3,
                center[0] + 3,
                center[1] + 3,
                fill="#e2e8f0",
                outline="",
            )

        direction_arrow = 1 if self.preview_direction >= 0 else -1
        arrow_color = "#fbbf24" if direction_arrow > 0 else "#60a5fa"
        arrow_end = cart_x + 160 if direction_arrow > 0 else cart_x - 28
        canvas.create_line(
            cart_x + 68,
            cart_y - 12,
            arrow_end,
            cart_y - 12,
            fill=arrow_color,
            width=4,
            arrow=tk.LAST,
        )

        info = (
            f"LIDAR {self.telemetry.lidar:.0f} | IMU {self.telemetry.imu:.1f}° | "
            f"Encoder {self.telemetry.encoder} | Velocidade {self.telemetry.velocidade:.2f}"
        )
        canvas.create_text(
            60,
            height - 28,
            anchor="w",
            fill="#cbd5e1",
            font=("Helvetica", 10),
            text=info,
        )

    def _on_close(self):
        try:
            self.client.loop_stop()
            self.client.disconnect()
        finally:
            self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = OperatorGUI(root)
    root.mainloop()
