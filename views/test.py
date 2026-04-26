"""
ENTRY POINT APLIKASI POS

👉 Gunakan file ini untuk menjalankan aplikasi
👉 Hindari menjalankan main_window.py langsung (biar struktur tetap modular)
"""

import sys
import os

# ===== FIX IMPORT PATH =====
# 👉 Supaya Python bisa mengenali folder 'views' sebagai module
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from PyQt6.QtWidgets import QApplication
from views.main_window import MainWindow


def main():
    app = QApplication(sys.argv)

    # ===== INIT MAIN WINDOW =====
    window = MainWindow()
    window.show()

    # ===== START EVENT LOOP =====
    sys.exit(app.exec())


if __name__ == "__main__":
    main()