from PyQt6.QtWidgets import QFrame, QVBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt


class Sidebar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)

        # ===== STYLE DASAR SIDEBAR =====
        self.setStyleSheet("background-color: #2c3e50; color: white;")

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # ===== TITLE / LOGO =====
        self.title = QLabel("POS SYSTEM")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title.setStyleSheet("font-size: 18px; font-weight: bold;")

        self.layout.addWidget(self.title)

        # ===== MENU BUTTONS =====
        # 👉 Gunakan dictionary supaya scalable
        self.buttons = {}

        menus = ["Dashboard", "POS", "Storage", "Report", "Loyalty"]

        for menu in menus:
            btn = QPushButton(menu)
            btn.setStyleSheet(self.button_style())

            # simpan reference tombol
            self.buttons[menu] = btn

            self.layout.addWidget(btn)

        self.layout.addStretch()


    def button_style(self):
        return """
            QPushButton {
                background-color: #34495e;
                padding: 10px;
                border: none;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #1abc9c;
            }
        """