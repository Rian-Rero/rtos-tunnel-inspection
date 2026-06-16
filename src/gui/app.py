"""Aplicação GUI do operador.

*OperatorGUI* é um orquestrador enxuto: mantém a conexão MQTT, constrói
três painéis e conecta suas interações. Toda renderização e estado de
componentes ficam nas classes de painel correspondentes.
"""

from __future__ import annotations

import json
import logging
import tkinter as tk
from tkinter import ttk

from config import Topics, Limits, MQTT_BROKER, MQTT_PORT, MQTT_QOS
from models import RobotTelemetry
from mqtt import MqttComponent
from .panels import ControlsPanel, TelemetryPanel, PreviewPanel

__all__ = ["OperatorGUI"]

## Registrador da aplicação gráfica do operador.
logger = logging.getLogger(__name__)


class OperatorGUI(MqttComponent):
    """GUI de operação remota baseada em janela Tkinter e telemetria MQTT."""

    def __init__(
        self,
        root: tk.Tk,
        broker: str = MQTT_BROKER,
        port: int = MQTT_PORT,
    ) -> None:
        """Inicializa a janela, os painéis e a conexão MQTT assíncrona."""
        super().__init__(broker, port, "Python_GUI")
        ## Janela raiz do Tkinter.
        self._root = root
        ## Indica se a rotina de fechamento já foi executada.
        self._closed = False
        ## Última telemetria consolidada recebida.
        self._telemetry = RobotTelemetry()
        ## Histórico recente usado pelo painel de pré-visualização.
        self._history: list[RobotTelemetry] = []
        ## Texto de estado exibido para o resultado YOLO.
        self._yolo_state = "Aguardando inspeção..."
        ## Variável textual que mostra o estado da conexão MQTT.
        self._connection_var = tk.StringVar(value="Conectando ao broker MQTT...")

        self._configure_window()
        self._setup_styles()
        self._build_ui()
        self._root.protocol("WM_DELETE_WINDOW", lambda: self.close())

        try:
            self.connect_async()
        except OSError as exc:
            self._connection_var.set(f"Falha na conexão: {exc}")

    # ── configuração da janela ───────────────────────────────────────────────

    def _configure_window(self) -> None:
        """Define título, tamanho e restrições da janela principal."""
        sw, sh = self._root.winfo_screenwidth(), self._root.winfo_screenheight()
        ww = min(1180, max(980, sw - 80))
        wh = min(720, max(620, sh - 120))
        self._root.title("ATR - Operação Remota do Carrinho")
        self._root.geometry(f"{ww}x{wh}+24+40")
        self._root.minsize(980, 620)
        self._root.configure(bg="#0f172a")

    def _setup_styles(self) -> None:
        """Registra os estilos visuais usados pelos componentes ttk."""
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
            "Accent.TButton", font=("Helvetica", 11, "bold"), padding=(16, 10)
        )
        style.map(
            "Accent.TButton", relief=[("pressed", "sunken"), ("!pressed", "raised")]
        )

    def _build_ui(self) -> None:
        """Monta cabeçalho, painéis principais e rodapé da GUI."""
        container = ttk.Frame(self._root, style="Root.TFrame")
        container.pack(fill="both", expand=True)

        # ── Cabeçalho ────────────────────────────────────────────────────────
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
            status_box, textvariable=self._connection_var, style="Status.TLabel"
        ).pack(anchor="e")

        # ── Corpo: leiaute em três colunas ───────────────────────────────────
        body = ttk.Frame(container, style="Root.TFrame", padding=(20, 20, 20, 16))
        body.pack(fill="both", expand=True)
        for col in range(3):
            body.columnconfigure(col, weight=1, uniform="main")
        body.rowconfigure(0, weight=1)

        ctrl_card = ttk.Frame(body, style="Card.TFrame", padding=20)
        ctrl_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        tele_card = ttk.Frame(body, style="Card.TFrame", padding=20)
        tele_card.grid(row=0, column=1, sticky="nsew", padx=12)
        prev_card = ttk.Frame(body, style="Card.TFrame", padding=20)
        prev_card.grid(row=0, column=2, sticky="nsew", padx=(12, 0))

        ## Painel responsável por publicar comandos do operador.
        self._controls = ControlsPanel(ctrl_card, self.publish)
        ## Painel que exibe as métricas de telemetria.
        self._telemetry_panel = TelemetryPanel(tele_card)
        ## Painel que desenha a pré-visualização do túnel e do robô.
        self._preview = PreviewPanel(prev_card)

        # ── Rodapé ───────────────────────────────────────────────────────────
        footer = ttk.Frame(container, style="Panel.TFrame", padding=(20, 0, 20, 18))
        footer.pack(fill="x")
        ttk.Label(
            footer,
            text="MQTT: cmd/mode, cmd/direction, cmd/speed_sp, cmd/camera, telemetry/robot, telemetry/yolo, sensor/#",
            style="Subtitle.TLabel",
        ).pack(anchor="w")

    # ── ganchos MQTT ─────────────────────────────────────────────────────────

    def _on_connect(self, client) -> None:
        """Assina os tópicos de telemetria quando a conexão MQTT abre."""
        self._root.after(
            0, lambda: self._connection_var.set("Conectado ao broker MQTT")
        )
        client.subscribe("telemetry/#", qos=MQTT_QOS)
        client.subscribe("sensor/#", qos=MQTT_QOS)
        client.subscribe(Topics.STATE_INSPECTION, qos=MQTT_QOS)

    def _on_message(self, topic: str, payload: str) -> None:
        """Despacha mensagens MQTT recebidas para o tratador apropriado da GUI."""
        dispatch = {
            Topics.TELEMETRY_YOLO: self._handle_yolo,
            Topics.TELEMETRY_ROBOT: self._handle_robot,
            Topics.SENSOR_LIDAR: lambda p: None,  # tratado via telemetry/robot
            Topics.STATE_INSPECTION: self._handle_inspection,
        }
        handler = dispatch.get(topic)
        if handler:
            self._root.after(0, lambda h=handler, p=payload: h(p))

    def _handle_robot(self, payload: str) -> None:
        """Atualiza telemetria e histórico a partir do JSON do robô."""
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return
        self._telemetry = RobotTelemetry.from_payload(data, self._telemetry)
        self._history.append(self._telemetry)
        self._history = self._history[-Limits.OPERATOR_HISTORY_MAX :]
        self._telemetry_panel.update(self._telemetry, self._yolo_state)
        self._preview.update(self._telemetry, self._history, self._yolo_state)

    def _handle_yolo(self, payload: str) -> None:
        """Atualiza o estado textual da inspeção visual."""
        try:
            data = json.loads(payload)
            status = (
                "Anomalia detectada"
                if data.get("anomalia_detectada")
                else "Sem anomalia"
            )
            conf = data.get("confianca")
            self._yolo_state = (
                f"{status} | confiança {conf:.2f}"
                if isinstance(conf, (int, float))
                else status
            )
        except json.JSONDecodeError:
            self._yolo_state = payload
        self._telemetry_panel.update(self._telemetry, self._yolo_state)

    def _handle_inspection(self, payload: str) -> None:
        """Atualiza a interface quando o núcleo informa inspeção em andamento."""
        active = payload.strip() == "1"
        self._yolo_state = (
            "Inspeção em andamento" if active else "Sistema em regime normal"
        )
        self._telemetry_panel.update(self._telemetry, self._yolo_state)

    # ── ciclo de vida ────────────────────────────────────────────────────────

    def close(self) -> None:
        """Fecha a conexão MQTT e destrói a janela principal."""
        if self._closed:
            return
        self._closed = True
        try:
            self.disconnect()
        finally:
            self._root.destroy()
