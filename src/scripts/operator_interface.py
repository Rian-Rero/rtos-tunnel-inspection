"""Ponto de entrada da GUI Tkinter do operador."""

import logging
import signal
import sys
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

## Configuração de log usada pelo ponto de entrada da GUI.
LOGGING_CONFIG = {"level": logging.INFO, "format": "%(levelname)s: %(message)s"}
logging.basicConfig(**LOGGING_CONFIG)

from gui import OperatorGUI  # noqa: E402

if __name__ == "__main__":
    ## Janela raiz da interface do operador.
    root = tk.Tk()
    ## Aplicação principal associada à janela Tkinter.
    app = OperatorGUI(root)

    def request_shutdown(_signum, _frame):
        """Agenda o fechamento limpo da GUI ao receber sinal do sistema."""
        root.after(0, app.close)

    signal.signal(signal.SIGINT, request_shutdown)
    signal.signal(signal.SIGTERM, request_shutdown)
    root.mainloop()
