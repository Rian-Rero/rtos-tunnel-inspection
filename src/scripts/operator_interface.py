"""
Interface Gráfica do Operador (GUI).

Permite a visualização da telemetria do robô e o envio de comandos
remotos utilizando a biblioteca Tkinter.
"""

import tkinter as tk
from tkinter import ttk
import paho.mqtt.client as mqtt


class OperatorGUI:
    """
    Janela de Operação Remota.
    """

    def __init__(self, root: tk.Tk, broker="localhost"):
        self.root = root
        self.root.title("SGLA - Operação Remota do Robô")
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION1, client_id="Python_GUI"
        )
        self._setup_mqtt(broker)
        self._build_ui()

    def _setup_mqtt(self, broker):
        self.client = mqtt.Client()
        self.client.on_message = self.on_message
        self.client.connect(broker, 1883, 60)
        self.client.subscribe("telemetry/#")
        self.client.subscribe("state/inspection")
        self.client.loop_start()

    def _build_ui(self):
        # Frame de Comandos
        cmd_frame = ttk.LabelFrame(self.root, text="Comandos de Navegação")
        cmd_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        ttk.Button(
            cmd_frame,
            text="Modo AUTO",
            command=lambda: self.publish_cmd("cmd/mode", "AUTO"),
        ).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(
            cmd_frame,
            text="Modo MANUAL",
            command=lambda: self.publish_cmd("cmd/mode", "MANUAL"),
        ).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(cmd_frame, text="Setpoint Velocidade:").grid(row=1, column=0, pady=5)
        self.speed_slider = tk.Scale(cmd_frame, from_=0, to=100, orient=tk.HORIZONTAL)
        self.speed_slider.grid(row=1, column=1)
        self.speed_slider.bind("<ButtonRelease-1>", self._update_speed)

        ttk.Button(
            cmd_frame,
            text="⬅️ Esquerda",
            command=lambda: self.publish_cmd("cmd/direction", "LEFT"),
        ).grid(row=2, column=0, pady=5)
        ttk.Button(
            cmd_frame,
            text="Parar 🛑",
            command=lambda: self.publish_cmd("cmd/direction", "STOP"),
        ).grid(row=2, column=1, pady=5)
        ttk.Button(
            cmd_frame,
            text="Direita ➡️",
            command=lambda: self.publish_cmd("cmd/direction", "RIGHT"),
        ).grid(row=2, column=2, pady=5)

        # Frame de Telemetria
        tel_frame = ttk.LabelFrame(self.root, text="Telemetria")
        tel_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        self.lbl_lidar = ttk.Label(tel_frame, text="LIDAR: ---")
        self.lbl_lidar.grid(row=0, column=0, sticky="w", pady=2)

        self.lbl_yolo = ttk.Label(
            tel_frame, text="YOLO Vision: Aguardando...", foreground="blue"
        )
        self.lbl_yolo.grid(row=1, column=0, sticky="w", pady=2)

    def publish_cmd(self, topic: str, payload: str):
        self.client.publish(topic, payload)

    def _update_speed(self, event):
        self.client.publish("cmd/speed_sp", self.speed_slider.get())

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode()

        # Atualização da UI precisa acontecer em thread-safe
        if topic == "telemetry/yolo":
            self.root.after(
                0, lambda: self.lbl_yolo.config(text=f"YOLO Vision: {payload}")
            )
        elif topic == "state/inspection":
            estado = "Inspecionando Falha!" if int(payload) == 1 else "Normal"
            color = "red" if int(payload) == 1 else "green"
            self.root.after(
                0, lambda: self.lbl_yolo.config(text=estado, foreground=color)
            )


if __name__ == "__main__":
    root = tk.Tk()
    app = OperatorGUI(root)
    root.mainloop()
