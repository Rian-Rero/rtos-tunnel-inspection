"""Ponto de entrada do simulador de túnel em Pygame."""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

from simulator import TunelSimulator  # noqa: E402

if __name__ == "__main__":
    TunelSimulator().run()
