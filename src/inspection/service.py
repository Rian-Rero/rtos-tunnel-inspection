"""Daemon de inspeção YOLOv8.

*YoloInspectionService* é um orquestrador enxuto: mantém a conexão MQTT
e delega a geração de quadros para *SyntheticFrameGenerator* e a
inferência para o modelo YOLO.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

from config import Topics, MQTT_BROKER, MQTT_PORT, MQTT_QOS
from models import YoloResult
from mqtt import MqttComponent

__all__ = ["YoloInspectionService"]

## Registrador do serviço de inspeção YOLO.
logger = logging.getLogger(__name__)


class YoloInspectionService(MqttComponent):
    """Daemon de inspeção YOLOv8 via MQTT com captura de quadro sintético."""

    def __init__(
        self,
        model_path: str = "models/yolov8n.pt",
        broker: str = MQTT_BROKER,
        port: int = MQTT_PORT,
    ) -> None:
        """Carrega dependências pesadas, modelo YOLO e gerador de quadros."""
        super().__init__(broker, port, "Python_YOLO_Service")

        logger.info("Carregando pesos do modelo YOLOv8...")
        os.environ.setdefault("YOLO_CONFIG_DIR", "/tmp")
        os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

        import cv2
        import numpy as np
        from ultralytics import YOLO

        from .frame import SyntheticFrameGenerator

        ## Modelo YOLOv8 usado para inferência local.
        self._model = YOLO(model_path)
        ## Caminho onde o último quadro sintético é salvo.
        self._frame_path = Path("data/capturas/frame_atual.jpg")
        ## Gerador de imagens sintéticas da câmera embarcada.
        self._generator = SyntheticFrameGenerator(cv2, np)
        ## Módulo OpenCV usado para persistir quadros.
        self._cv2 = cv2
        ## Indica se uma inferência já está em andamento.
        self._processing = False

    # ── ganchos MQTT ─────────────────────────────────────────────────────────

    def _on_connect(self, client) -> None:
        """Assina o tópico de comando da câmera após conectar ao broker."""
        client.subscribe(Topics.CMD_CAMERA, qos=MQTT_QOS)

    def _on_message(self, topic: str, payload: str) -> None:
        """Inicia inspeção visual quando recebe comando de câmera."""
        if topic != Topics.CMD_CAMERA:
            return
        try:
            command = int(payload.strip())
        except ValueError:
            logger.warning("Comando de câmera inválido: %r", payload)
            return
        if command == 1:
            if self._processing:
                logger.info("Inferência já em andamento; gatilho ignorado.")
            else:
                logger.info("Gatilho recebido. Iniciando inferência...")
                self._run_inspection()

    # ── pipeline de inspeção ─────────────────────────────────────────────────

    def _run_inspection(self) -> None:
        """Executa uma inspeção completa e publica o resultado via MQTT."""
        self._processing = True
        try:
            result = self._inspect()
        except Exception as exc:
            logger.exception("Falha durante inferência YOLO.")
            result = YoloResult(
                timestamp=time.time(),
                anomalia_detectada=False,
                confianca=0.0,
                tipo="Erro na inferência",
                origem="erro",
            )
            result.deteccoes = [{"erro": str(exc)}]
        finally:
            self._processing = False

        self.publish(Topics.TELEMETRY_YOLO, json.dumps(result.to_payload()))
        logger.info("Resultado publicado: %s", result.to_payload())

    def _inspect(self) -> YoloResult:
        """Gera o quadro, executa YOLO e monta o resultado de domínio."""
        frame, anomaly_type = self._generator.generate()
        self._save_frame(frame)

        boxes = self._model(frame, verbose=False, device="cpu")[0].boxes or []
        detections = []
        max_conf = 0.0
        for box in boxes:
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            label = self._model.names.get(cls_id, str(cls_id))
            max_conf = max(max_conf, conf)
            detections.append({"classe": label, "confianca": conf})

        return YoloResult(
            timestamp=time.time(),
            anomalia_detectada=bool(detections) or anomaly_type != "normal",
            confianca=max_conf if detections else 0.88,
            tipo=detections[0]["classe"] if detections else anomaly_type,
            deteccoes=detections,
            anomalia_visual_simulada=anomaly_type,
            origem="camera_simulada_robo",
        )

    def _save_frame(self, frame) -> None:
        """Salva o último quadro usado na inferência para auditoria visual."""
        self._frame_path.parent.mkdir(parents=True, exist_ok=True)
        self._cv2.imwrite(str(self._frame_path), frame)

    # ── ponto de entrada ─────────────────────────────────────────────────────

    def run(self) -> None:
        """Bloqueia continuamente, processando disparos de inspeção."""
        try:
            self.connect_blocking()
        except KeyboardInterrupt:
            pass
        finally:
            self.disconnect()
