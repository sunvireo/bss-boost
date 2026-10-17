"""Entry point for Bss Booster. Run with: python main.py"""
from __future__ import annotations
import sys
from pathlib import Path
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from bss_booster.config import Store
from bss_booster.ui import BoosterWindow


def resource(path: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / path


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Bss Booster")
    app.setOrganizationName("BssBooster")
    app.setStyle("Fusion")
    icon = resource("assets/bss_booster_icon.png")
    if icon.exists():
        app.setWindowIcon(QIcon(str(icon)))
    win = BoosterWindow(Store(), icon)
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
