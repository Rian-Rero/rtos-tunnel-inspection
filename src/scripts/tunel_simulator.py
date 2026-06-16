"""Ponto de entrada do simulador de túnel em Pygame."""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

## Configuração de log usada pelo ponto de entrada do simulador.
LOGGING_CONFIG = {"level": logging.INFO, "format": "%(levelname)s: %(message)s"}
logging.basicConfig(**LOGGING_CONFIG)

from simulator import TunelSimulator  # noqa: E402

if __name__ == "__main__":
    TunelSimulator().run()
