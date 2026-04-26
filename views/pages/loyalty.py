from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel

class LoyaltyPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Loyalty Page"))
        self.setLayout(layout)