from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel


class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()
        self.setLayout(layout)

        label = QLabel("Dashboard Page")
        layout.addWidget(label)