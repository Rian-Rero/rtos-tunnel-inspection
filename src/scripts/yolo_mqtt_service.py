"""Ponto de entrada do daemon de inspeção YOLOv8."""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

from inspection import YoloInspectionService  # noqa: E402

if __name__ == "__main__":
    YoloInspectionService().run()
