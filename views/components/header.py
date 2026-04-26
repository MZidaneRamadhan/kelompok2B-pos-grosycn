from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton


class Header(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setStyleSheet("background-color: #ecf0f1;")

        self.layout = QHBoxLayout()
        self.setLayout(self.layout)

        # ===== TITLE HALAMAN =====
        self.title = QLabel("Dashboard")
        self.title.setStyleSheet("font-size: 16px; font-weight: bold;")

        # ===== USER INFO =====
        self.user_label = QLabel("Admin")

        self.logout_btn = QPushButton("Logout")

        self.layout.addWidget(self.title)
        self.layout.addStretch()
        self.layout.addWidget(self.user_label)
        self.layout.addWidget(self.logout_btn)

    def set_title(self, text):
        # 👉 Dipanggil dari main_window saat pindah page
        self.title.setText(text)