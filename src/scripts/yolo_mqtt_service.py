"""
Daemon de Inspeção Visual com YOLOv8.

Inscrito no tópico de trigger da câmera. Quando ativado, simula
a captura de uma imagem, processa através da rede neural YOLOv8
e publica o JSON do resultado no barramento MQTT.
"""

import time
import json
import logging
import paho.mqtt.client as mqtt
from ultralytics import YOLO

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


class YoloInspectionService:
    """
    Serviço que acopla o modelo YOLOv8 ao ecossistema MQTT.
    """

    def __init__(
        self, model_path: str = "models/yolov8n.pt", broker: str = "localhost"
    ):
        logging.info("Carregando pesos do modelo YOLOv8...")
        self.model = YOLO(model_path)

        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION1, client_id="Python_YOLO_Service"
        )
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(broker, 1883, 60)

    def on_connect(self, client, userdata, flags, rc):
        logging.info("Serviço YOLO conectado ao MQTT Broker.")
        self.client.subscribe("cmd/camera")

    def on_message(self, client, userdata, msg):
        if msg.topic == "cmd/camera":
            comando = int(msg.payload.decode())
            if comando == 1:
                logging.info("Trigger de câmera recebido. Iniciando inferência...")
                self._realizar_inspecao()

    def _realizar_inspecao(self):
        """Executa a predição da rede neural sobre a imagem atual."""
        # Mock de captura de imagem. Em um cenário real, você leria do OpenCV (cv2.VideoCapture)
        # result = self.model("data/capturas/frame_atual.jpg")

        # Simulação de latência de processamento
        time.sleep(0.5)

        payload = {
            "timestamp": time.time(),
            "anomalia_detectada": True,
            "confianca": 0.92,
            "tipo": "Fissura",
        }

        self.client.publish("telemetry/yolo", json.dumps(payload))
        logging.info(f"Resultado publicado: {payload}")

    def run(self):
        """Mantém o daemon rodando e escutando requisições indefinidamente."""
        self.client.loop_forever()


if __name__ == "__main__":
    service = YoloInspectionService()
    service.run()
