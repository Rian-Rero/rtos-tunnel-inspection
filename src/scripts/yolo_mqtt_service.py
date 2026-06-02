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
        os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
        import cv2
        import numpy as np
        from ultralytics import YOLO

        self.cv2 = cv2
        self.np = np
        self.model = YOLO(model_path)
        self.frame_path = Path("data/capturas/frame_atual.jpg")
        self.capture_index = 0
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

    def _capture_robot_camera_frame(self):
        self.capture_index += 1
        frame = self.np.full((480, 640, 3), (24, 28, 34), dtype=self.np.uint8)

        # Teto do túnel visto pela câmera embarcada simulada.
        for y in range(0, 180, 18):
            tone = 42 + (y % 36)
            self.cv2.line(frame, (0, y), (640, y + 28), (tone, tone, tone + 8), 3)
        self.cv2.rectangle(frame, (0, 0), (640, 138), (76, 78, 82), -1)
        self.cv2.line(frame, (0, 138), (640, 168), (36, 39, 44), 10)

        phase = self.capture_index % 3
        if phase == 0:
            self.cv2.line(frame, (150, 74), (505, 108), (10, 10, 10), 9)
            self.cv2.line(frame, (155, 74), (500, 108), (92, 92, 96), 2)
            simulated_type = "fissura"
        elif phase == 1:
            self.cv2.ellipse(frame, (410, 82), (78, 28), 4, 0, 360, (28, 28, 30), -1)
            self.cv2.ellipse(frame, (410, 82), (78, 28), 4, 0, 360, (118, 118, 120), 3)
            simulated_type = "buraco"
        else:
            self.cv2.circle(frame, (320, 78), 42, (128, 128, 126), -1)
            self.cv2.circle(frame, (320, 78), 44, (44, 44, 48), 4)
            simulated_type = "saliencia"

        # Robô e cone de iluminação/câmera, tudo sintético.
        overlay = frame.copy()
        triangle = self.np.array(
            [[(320, 445), (110, 150), (530, 150)]], dtype=self.np.int32
        )
        self.cv2.fillPoly(overlay, triangle, (84, 130, 190))
        frame = self.cv2.addWeighted(overlay, 0.28, frame, 0.72, 0)
        self.cv2.rectangle(frame, (210, 385), (430, 460), (40, 170, 92), -1)
        self.cv2.rectangle(frame, (238, 400), (402, 430), (14, 22, 36), -1)
        self.cv2.circle(frame, (262, 462), 24, (18, 22, 30), -1)
        self.cv2.circle(frame, (378, 462), 24, (18, 22, 30), -1)
        self.cv2.circle(frame, (320, 376), 18, (42, 120, 190), -1)
        self.cv2.circle(frame, (320, 376), 8, (215, 235, 255), -1)
        self.cv2.putText(
            frame,
            f"CAMERA SIMULADA DO ROBO | {simulated_type}",
            (32, 34),
            self.cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (235, 238, 244),
            2,
        )

        self.frame_path.parent.mkdir(parents=True, exist_ok=True)
        self.cv2.imwrite(str(self.frame_path), frame)
        return frame, "camera_simulada_robo", simulated_type

    def _realizar_inspecao(self):
        """Executa a predição da rede neural sobre a imagem atual."""
        self.processing = True

        try:
            frame, frame_source, simulated_type = self._capture_robot_camera_frame()
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
                "anomalia_detectada": bool(detections) or simulated_type != "normal",
                "confianca": max_confidence if detections else 0.88,
                "tipo": detections[0]["classe"] if detections else simulated_type,
                "deteccoes": detections,
                "anomalia_visual_simulada": simulated_type,
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
        logging.info("Resultado publicado: %s", payload)

    def run(self):
        """Mantém o daemon rodando e escutando requisições indefinidamente."""
        self.client.loop_forever()


if __name__ == "__main__":
    service = YoloInspectionService()
    service.run()
