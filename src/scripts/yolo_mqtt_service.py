"""Ponto de entrada do serviço de inspeção YOLOv8."""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

## Configuração de log usada pelo ponto de entrada do serviço YOLO.
LOGGING_CONFIG = {"level": logging.INFO, "format": "%(levelname)s: %(message)s"}
logging.basicConfig(**LOGGING_CONFIG)

from inspection import YoloInspectionService  # noqa: E402

if __name__ == "__main__":
    YoloInspectionService().run()
