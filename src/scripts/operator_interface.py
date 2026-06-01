"""
Interface Gráfica do Operador (GUI).

Painel principal para comando remoto, telemetria MQTT e visualização do carrinho.
"""

from __future__ import annotations

import json
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

        self.client = self._create_client()
        self._setup_styles()
        self._build_ui()
        self._setup_mqtt()
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

        self.preview_canvas = tk.Canvas(
            self.preview_card,
            width=360,
            height=420,
            bg="#0b1220",
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
        self.publish_cmd("actuator/motor", speed)
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
        velocidade = float(data.get("velocidade", self.telemetry.velocidade))
        lidar = float(data.get("lidar", self.telemetry.lidar))
        imu = float(data.get("imu", self.telemetry.imu))
        encoder = int(data.get("encoder", self.telemetry.encoder))
        mode = str(data.get("mode", self.telemetry.mode))
        direction = str(data.get("direction", self.telemetry.direction))
        distance_m = float(data.get("distance_m", pos_x / 10.0))

        self.telemetry = RobotTelemetry(
            pos_x, velocidade, lidar, imu, encoder, mode, direction
        )
        self.position_state.set(f"{distance_m:.2f} m")
        self.mode_state.set(mode)
        self.direction_state.set(direction)
        self.lidar_state.set(f"{lidar:.0f}")
        self.imu_state.set(f"{imu:.1f}°")
        self.encoder_state.set(str(encoder))
        self._draw_robot_preview()

    def _draw_robot_preview(self):
        canvas = self.preview_canvas
        canvas.delete("all")

        width = int(canvas.winfo_width() or 360)
        height = int(canvas.winfo_height() or 420)

        canvas.create_rectangle(0, 0, width, height, fill="#0b1220", outline="")
        canvas.create_rectangle(
            30, 30, width - 30, height - 60, fill="#111827", outline="#1f2937", width=2
        )

        lane_y = height // 2 + 30
        canvas.create_line(60, lane_y, width - 60, lane_y, fill="#22c55e", width=3)
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

        cart_x = 120 + int((self.telemetry.pos_x * 12) % max(1, width - 240))
        cart_y = lane_y - 28
        canvas.create_rectangle(
            cart_x,
            cart_y,
            cart_x + 120,
            cart_y + 40,
            fill="#22c55e",
            outline="#86efac",
            width=2,
        )
        canvas.create_rectangle(
            cart_x + 14,
            cart_y + 10,
            cart_x + 42,
            cart_y + 28,
            fill="#0f172a",
            outline="",
        )
        canvas.create_rectangle(
            cart_x + 46,
            cart_y + 10,
            cart_x + 74,
            cart_y + 28,
            fill="#0f172a",
            outline="",
        )
        canvas.create_rectangle(
            cart_x + 78,
            cart_y + 10,
            cart_x + 106,
            cart_y + 28,
            fill="#0f172a",
            outline="",
        )
        canvas.create_oval(
            cart_x + 10,
            cart_y + 32,
            cart_x + 28,
            cart_y + 50,
            fill="#94a3b8",
            outline="",
        )
        canvas.create_oval(
            cart_x + 92,
            cart_y + 32,
            cart_x + 110,
            cart_y + 50,
            fill="#94a3b8",
            outline="",
        )
        canvas.create_text(
            cart_x + 60,
            cart_y + 20,
            fill="#0f172a",
            font=("Helvetica", 11, "bold"),
            text="ATR",
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
