from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QHBoxLayout


class POSPage(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()
        self.setLayout(layout)

        # ===== TABLE TRANSAKSI =====
        self.table = QTableWidget(5, 3)
        self.table.setHorizontalHeaderLabels(["Item", "Qty", "Price"])

        # dummy data
        self.table.setItem(0, 0, QTableWidgetItem("Product A"))

        layout.addWidget(self.table)

        # ===== BUTTON ACTION =====
        btn_layout = QHBoxLayout()

        self.btn_add = QPushButton("Add Item")
        self.btn_checkout = QPushButton("Checkout")

        btn_layout.addWidget(self.btn_add)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_checkout)

        layout.addLayout(btn_layout)