import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QHBoxLayout, QVBoxLayout, QStackedWidget
)

# ===== IMPORT COMPONENT =====
from views.components.sidebar import Sidebar
from views.components.header import Header

# ===== IMPORT PAGES =====
from views.pages.dashboard import DashboardPage
from views.pages.pos import POSPage
from views.pages.storage import StoragePage
from views.pages.report import ReportPage
from views.pages.loyalty import LoyaltyPage


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("POS Modular App")
        self.setGeometry(100, 100, 1200, 700)

        # ===== ROOT =====
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout()
        central.setLayout(main_layout)

        # ===== SIDEBAR =====
        self.sidebar = Sidebar()

        # ===== RIGHT SIDE =====
        right_layout = QVBoxLayout()

        self.header = Header()

        # ===== STACKED WIDGET (MULTI PAGE) =====
        self.stack = QStackedWidget()

        # 👉 Tambahkan semua halaman di sini
        self.pages = {
            "Dashboard": DashboardPage(),
            "POS": POSPage(),
            "Storage": StoragePage(),
            "Report": ReportPage(),
            "Loyalty": LoyaltyPage(),
        }

        for page in self.pages.values():
            self.stack.addWidget(page)

        # ===== LAYOUT =====
        right_layout.addWidget(self.header)
        right_layout.addWidget(self.stack)

        main_layout.addWidget(self.sidebar)
        main_layout.addLayout(right_layout)

        main_layout.setStretch(0, 2)
        main_layout.setStretch(1, 8)

        # ===== CONNECT SIDEBAR KE PAGE =====
        self.connect_navigation()


    def connect_navigation(self):
        # 👉 Loop semua tombol sidebar
        for name, button in self.sidebar.buttons.items():
            button.clicked.connect(lambda _, n=name: self.switch_page(n))


    def switch_page(self, page_name):
        # 👉 Ganti halaman berdasarkan nama
        page = self.pages[page_name]
        self.stack.setCurrentWidget(page)

        # update title di header
        self.header.set_title(page_name)


# ===== ENTRY POINT =====
if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())