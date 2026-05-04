"""
RetailPOS – Semi-Online Point of Sale System
============================================

Run:
    pip install PyQt6
    python main.py
"""

import sys

from PyQt6.QtWidgets import QApplication

from views.styles.theme_manager import apply_theme
from views.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("RetailPOS")
    apply_theme(app)

    win = MainWindow()
    win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
