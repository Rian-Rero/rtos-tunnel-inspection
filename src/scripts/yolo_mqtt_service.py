"""Daemon de inspeção visual com YOLOv8.

Escuta o trigger da câmera, simula a inferência e publica o resultado
no barramento MQTT.
"""

import math
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

        # ── Robô sintético com esteiras, caixa, LiDAR e câmera articulada ──
        cv2 = self.cv2
        np = self.np
        bx_c = 320  # centro horizontal do corpo
        bx_l = bx_c - 118  # borda esquerda do corpo
        bx_r = bx_c + 118  # borda direita do corpo
        body_top = 358
        body_bot = 408

        # Sombra
        cv2.ellipse(frame, (bx_c, 450), (132, 9), 0, 0, 360, (12, 14, 18), -1)

        # Esteiras (caterpillar tracks)
        cv2.rectangle(
            frame, (bx_l - 14, body_bot), (bx_r + 14, body_bot + 30), (22, 27, 33), -1
        )
        cv2.rectangle(
            frame, (bx_l - 14, body_bot), (bx_r + 14, body_bot + 30), (50, 62, 72), 1
        )
        # Marcas de tração
        for ti in range(0, 248, 12):
            tx_t = bx_l - 12 + ti
            cv2.line(
                frame, (tx_t, body_bot + 2), (tx_t, body_bot + 28), (14, 18, 22), 2
            )
        # Estria superior da esteira
        cv2.line(
            frame, (bx_l - 14, body_bot + 2), (bx_r + 14, body_bot + 2), (64, 78, 90), 1
        )
        # Rodas motrizes (sprockets)
        cv2.circle(frame, (bx_l - 12, body_bot + 15), 16, (40, 48, 58), -1)
        cv2.circle(frame, (bx_l - 12, body_bot + 15), 16, (76, 92, 106), 2)
        cv2.circle(frame, (bx_r + 12, body_bot + 15), 16, (40, 48, 58), -1)
        cv2.circle(frame, (bx_r + 12, body_bot + 15), 16, (76, 92, 106), 2)
        # Rodas de apoio (3)
        for rwi in range(1, 4):
            rwx = bx_l + int(236 * rwi / 4)
            cv2.circle(frame, (rwx, body_bot + 15), 10, (32, 38, 46), -1)
            cv2.circle(frame, (rwx, body_bot + 15), 10, (60, 72, 84), 1)

        # Corpo principal
        cv2.rectangle(frame, (bx_l, body_top), (bx_r, body_bot), (60, 78, 92), -1)
        cv2.rectangle(frame, (bx_l, body_top), (bx_r, body_bot), (98, 120, 138), 2)
        cv2.line(
            frame,
            (bx_l + 8, (body_top + body_bot) // 2),
            (bx_r - 8, (body_top + body_bot) // 2),
            (42, 58, 70),
            1,
        )

        # Caixa de equipamentos (topo-esquerdo do corpo)
        eq_x1 = bx_l + 8
        eq_y1 = body_top - 30
        eq_x2 = bx_l + 88
        eq_y2 = body_top
        cv2.rectangle(frame, (eq_x1, eq_y1), (eq_x2, eq_y2), (46, 62, 76), -1)
        cv2.rectangle(frame, (eq_x1, eq_y1), (eq_x2, eq_y2), (80, 100, 116), 1)
        for slot in range(5):
            sx = eq_x1 + 8 + slot * 13
            cv2.line(frame, (sx, eq_y1 + 6), (sx, eq_y1 + 20), (30, 44, 56), 3)

        # Antena
        cv2.line(
            frame, (bx_l + 30, eq_y1), (bx_l + 30, body_top - 78), (158, 178, 198), 2
        )
        cv2.circle(frame, (bx_l + 30, body_top - 80), 5, (188, 208, 228), -1)
        cv2.circle(frame, (bx_l + 30, body_top - 80), 4, (72, 148, 230), -1)

        # Cone de varredura do LiDAR (antes da cúpula para ela cobrir a base)
        lidar_cx = bx_c + 22
        lidar_cy_v = body_top - 18
        lidar_r_v = 20
        overlay_beam = frame.copy()
        cone_pts = np.array(
            [
                [
                    (lidar_cx - 6, lidar_cy_v),
                    (lidar_cx + 6, lidar_cy_v),
                    (lidar_cx + 320, 4),
                    (lidar_cx - 320, 4),
                ]
            ],
            dtype=np.int32,
        )
        cv2.fillPoly(overlay_beam, cone_pts, (34, 140, 215))
        n_scan = 15
        for b in range(n_scan):
            ang = math.radians(-78.0 + b * (156.0 / (n_scan - 1)))
            bl_v = 390
            bx_e = int(lidar_cx + math.sin(ang) * bl_v)
            by_e = max(0, int(lidar_cy_v - math.cos(ang) * bl_v))
            cv2.line(
                overlay_beam, (lidar_cx, lidar_cy_v), (bx_e, by_e), (72, 195, 255), 1
            )
        frame = cv2.addWeighted(overlay_beam, 0.30, frame, 0.70, 0)

        # Cúpula do LiDAR – base de montagem
        cv2.rectangle(
            frame,
            (lidar_cx - 18, body_top - 12),
            (lidar_cx + 18, body_top),
            (44, 58, 72),
            -1,
        )
        cv2.rectangle(
            frame,
            (lidar_cx - 18, body_top - 12),
            (lidar_cx + 18, body_top),
            (80, 98, 114),
            1,
        )
        # Dome externo
        cv2.circle(frame, (lidar_cx, lidar_cy_v), lidar_r_v + 4, (36, 48, 60), -1)
        cv2.circle(frame, (lidar_cx, lidar_cy_v), lidar_r_v + 4, (68, 84, 100), 2)
        # Lente (azul)
        cv2.circle(frame, (lidar_cx, lidar_cy_v), lidar_r_v, (16, 88, 160), -1)
        cv2.circle(frame, (lidar_cx, lidar_cy_v), lidar_r_v, (46, 148, 238), 2)
        # Reflexo na lente
        cv2.circle(frame, (lidar_cx - 6, lidar_cy_v - 6), 6, (138, 198, 250), -1)
        cv2.circle(frame, (lidar_cx - 6, lidar_cy_v - 6), 3, (210, 238, 255), -1)

        # Braço da câmera (direita do corpo)
        cam_bx = bx_r - 26
        cam_by = body_top
        pt_ty = body_top - 36
        cv2.line(frame, (cam_bx, cam_by), (cam_bx, pt_ty), (118, 136, 154), 4)
        cv2.circle(frame, (cam_bx, pt_ty), 6, (70, 86, 102), -1)
        cv2.circle(frame, (cam_bx, pt_ty), 6, (114, 132, 150), 2)
        at_x_v = cam_bx + 38
        at_y_v = pt_ty - 8
        cv2.line(frame, (cam_bx, pt_ty), (at_x_v, at_y_v), (118, 136, 154), 4)
        # Cabeça da câmera
        cv2.rectangle(
            frame,
            (at_x_v - 6, at_y_v - 20),
            (at_x_v + 26, at_y_v + 4),
            (18, 24, 32),
            -1,
        )
        cv2.rectangle(
            frame,
            (at_x_v - 6, at_y_v - 20),
            (at_x_v + 26, at_y_v + 4),
            (94, 112, 130),
            1,
        )
        # Lente da câmera
        cv2.circle(frame, (at_x_v + 9, at_y_v - 8), 9, (24, 94, 168), -1)
        cv2.circle(frame, (at_x_v + 9, at_y_v - 8), 9, (48, 142, 228), 2)
        cv2.circle(frame, (at_x_v + 5, at_y_v - 12), 3, (168, 210, 252), -1)
        # LED de status (verde = operacional)
        cv2.circle(frame, (at_x_v + 22, at_y_v - 18), 4, (52, 211, 114), -1)
        cv2.putText(
            frame,
            f"CAMERA ATR | {simulated_type.upper()}",
            (32, 34),
            cv2.FONT_HERSHEY_SIMPLEX,
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
