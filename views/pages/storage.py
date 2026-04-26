from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel

class StoragePage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Storage Page"))
        self.setLayout(layout)