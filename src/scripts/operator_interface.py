"""Ponto de entrada da GUI Tkinter do operador."""

import logging
import signal
import sys
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

from gui import OperatorGUI  # noqa: E402

if __name__ == "__main__":
    root = tk.Tk()
    app = OperatorGUI(root)

    def request_shutdown(_signum, _frame):
        root.after(0, app.close)

    signal.signal(signal.SIGINT, request_shutdown)
    signal.signal(signal.SIGTERM, request_shutdown)
    root.mainloop()
