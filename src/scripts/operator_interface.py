"""Entry point for the Tkinter operator GUI."""

import logging
import sys
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

from gui import OperatorGUI  # noqa: E402

if __name__ == "__main__":
    root = tk.Tk()
    OperatorGUI(root)
    root.mainloop()
