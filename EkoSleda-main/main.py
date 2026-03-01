# ═══════════════════════════════════════════════
#  main.py  —  Точка на влизане в ЕкоСледа
# ═══════════════════════════════════════════════

import tkinter as tk
import sys
import os

# Уверяваме се, че папката на проекта е в Python пътя
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Стартиране на map сървъра преди GUI
from map_server import start_map_server
start_map_server()

from database import init_db
from auth import AuthWindow
from app import CarbonFootprintApp


def start_app():
    """Стартира ЕкоСледа: показва Login → след успех отваря главното приложение."""
    def on_login(uid, name):
        root = tk.Tk()
        CarbonFootprintApp(root, uid, name)
        root.mainloop()

    init_db()
    AuthWindow(on_login)


if __name__ == "__main__":
    start_app()
