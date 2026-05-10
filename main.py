"""
RetailPOS – Semi-Online Point of Sale System
============================================

Run:
    pip install PyQt6
    python main.py
"""

import sys

from PyQt6.QtWidgets import QApplication

from controllers.barang_controller import sync_json_from_db
from database import init_db
from views.styles.theme_manager import apply_theme
from views.main_window import MainWindow
from views.pages.login import LoginDialog


def main() -> None:
    # Initialize database at app startup
    init_db()
    sync_json_from_db()

    app = QApplication(sys.argv)
    app.setApplicationName("RetailPOS")
    apply_theme(app)

    dlg = LoginDialog()
    if not dlg.exec():
        return

    win = MainWindow(
        auth_token=dlg.auth_token or "",
        username=dlg.username or "",
    )
    win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()