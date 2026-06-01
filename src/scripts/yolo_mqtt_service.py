"""Daemon de inspeção visual com YOLOv8.

Escuta o trigger da câmera, simula a inferência e publica o resultado
no barramento MQTT.
"""

import time
import json
import logging
import os
from pathlib import Path

import paho.mqtt.client as mqtt

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


class YoloInspectionService:
    """
    Serviço que acopla o modelo YOLOv8 ao ecossistema MQTT.
    """

    def __init__(
        self, model_path: str = "models/yolov8n.pt", broker: str = "localhost"
    ):
        logging.info("Carregando pesos do modelo YOLOv8...")
        os.environ.setdefault("YOLO_CONFIG_DIR", "/tmp")
        import cv2
        import numpy as np
        from ultralytics import YOLO

        self.cv2 = cv2
        self.np = np
        self.model = YOLO(model_path)
        self.frame_path = Path("data/capturas/frame_atual.jpg")
        self.camera_index = int(os.getenv("ATR_CAMERA_INDEX", "0"))
        self.processing = False

        try:
            self.client = mqtt.Client(
                client_id="Python_YOLO_Service",
                callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
            )
        except TypeError:
            self.client = mqtt.Client(client_id="Python_YOLO_Service")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(broker, 1883, 60)

    def on_connect(self, client, userdata, flags, rc):
        logging.info("Serviço YOLO conectado ao MQTT Broker.")
        self.client.subscribe("cmd/camera")

    def on_message(self, client, userdata, msg):
        if msg.topic == "cmd/camera":
            try:
                comando = int(msg.payload.decode().strip())
            except ValueError:
                logging.warning("Comando de câmera inválido: %r", msg.payload)
                return
            if comando == 1:
                if self.processing:
                    logging.info("Inferência já em andamento; trigger ignorado.")
                    return
                logging.info("Trigger de câmera recebido. Iniciando inferência...")
                self._realizar_inspecao()

    def _capture_webcam_frame(self):
        capture = self.cv2.VideoCapture(self.camera_index)
        if not capture.isOpened():
            capture.release()
            return None

        frame = None
        for _ in range(5):
            ok, candidate = capture.read()
            if ok and candidate is not None:
                frame = candidate
        capture.release()

        if frame is None:
            return None

        self.frame_path.parent.mkdir(parents=True, exist_ok=True)
        self.cv2.imwrite(str(self.frame_path), frame)
        return frame

    def _load_frame(self):
        webcam_frame = self._capture_webcam_frame()
        if webcam_frame is not None:
            return webcam_frame, "webcam"

        if self.frame_path.exists():
            frame = self.cv2.imread(str(self.frame_path))
            if frame is not None:
                return frame, str(self.frame_path)

        frame = self.np.full((480, 640, 3), 35, dtype=self.np.uint8)
        self.cv2.rectangle(frame, (0, 0), (640, 120), (70, 70, 70), -1)
        self.cv2.line(frame, (170, 70), (460, 92), (20, 20, 20), 8)
        self.cv2.circle(frame, (480, 78), 24, (95, 95, 95), -1)
        self.cv2.putText(
            frame,
            "ATR tunnel ceiling inspection",
            (35, 430),
            self.cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (230, 230, 230),
            2,
        )
        return frame, "frame_sintetico"

    def _realizar_inspecao(self):
        """Executa a predição da rede neural sobre a imagem atual."""
        self.processing = True
        self.client.publish("state/inspection", 1)

        try:
            frame, frame_source = self._load_frame()
            results = self.model(frame, verbose=False, device="cpu")
            boxes = results[0].boxes if results else []

            detections = []
            max_confidence = 0.0
            for box in boxes:
                confidence = float(box.conf[0])
                class_id = int(box.cls[0])
                label = self.model.names.get(class_id, str(class_id))
                max_confidence = max(max_confidence, confidence)
                detections.append({"classe": label, "confianca": confidence})

            payload = {
                "timestamp": time.time(),
                "anomalia_detectada": bool(detections),
                "confianca": max_confidence,
                "tipo": detections[0]["classe"] if detections else "Sem objeto",
                "deteccoes": detections,
                "origem": frame_source,
            }
        except Exception as exc:
            logging.exception("Falha durante inferência YOLO.")
            payload = {
                "timestamp": time.time(),
                "anomalia_detectada": False,
                "confianca": 0.0,
                "tipo": "Erro na inferência",
                "erro": str(exc),
            }
        finally:
            self.processing = False

        self.client.publish("telemetry/yolo", json.dumps(payload))
        self.client.publish("state/inspection", 0)
        logging.info("Resultado publicado: %s", payload)

    def run(self):
        """Mantém o daemon rodando e escutando requisições indefinidamente."""
        self.client.loop_forever()


if __name__ == "__main__":
    service = YoloInspectionService()
    service.run()
