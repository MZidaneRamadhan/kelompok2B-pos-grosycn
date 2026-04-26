from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel

class ReportPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Report Page"))
        self.setLayout(layout)