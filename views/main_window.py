# ─────────────────────────────────────────────────────────────────────────────
# views/main_window.py
# ─────────────────────────────────────────────────────────────────────────────

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStackedWidget, QScrollArea, QStatusBar,
)

from views.components.header import Header
from views.components.sidebar import Sidebar
from views.pages.dashboard import DashboardPage
from views.pages.pos import POSPage
from views.pages.storage import StoragePage
from views.pages.productcategory import CategoryProductPage
from views.pages.suppliers import SuppliersPage
from views.pages.loyalty import LoyaltyPage
from views.pages.report import ReportsPage
from data.state import STATE


_PAGE_TITLES = [
    "Dashboard",
    "Point of Sale",
    "Inventory Management",
    "Product Category Management",
    "Supplier Management",
    "Loyalty Program",
    "Reports",
]


class MainWindow(QMainWindow):
    """
    Root application window.

    Layout
    ──────
    ┌─────────────┬──────────────────────────────┐
    │  Sidebar    │  Header (topbar)              │
    │  (nav)      ├──────────────────────────────┤
    │             │  QScrollArea                  │
    │             │   └─ QStackedWidget (pages)   │
    └─────────────┴──────────────────────────────┘
    StatusBar
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RetailPOS – Semi-Online POS System")
        self.resize(1280, 780)
        self.setMinimumSize(1000, 640)

        # ── Root layout ───────────────────────────────────────────────────────
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar
        self.sidebar = Sidebar()
        self.sidebar.page_changed.connect(self._on_page_changed)
        root.addWidget(self.sidebar)

        # Right column
        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(0)

        self.header = Header()
        self.header.toggle_online.connect(self._toggle_online)
        right_lay.addWidget(self.header)

        # Scrollable content area
        self.content_scroll = QScrollArea()
        self.content_scroll.setWidgetResizable(True)
        self.content_scroll.setObjectName("content")

        self.stack = QStackedWidget()
        self.content_scroll.setWidget(self.stack)
        right_lay.addWidget(self.content_scroll)

        root.addWidget(right)

        # ── Pages ─────────────────────────────────────────────────────────────
        self.dashboard_page = DashboardPage()
        self.pos_page = POSPage(self.header)
        self.storage_page = StoragePage()
        self.category_page = CategoryProductPage()
        self.suppliers_page = SuppliersPage()
        self.loyalty_page = LoyaltyPage()
        self.reports_page = ReportsPage()

        self._pages = [
            self.dashboard_page,
            self.pos_page,
            self.storage_page,
            self.category_page,
            self.suppliers_page,
            self.loyalty_page,
            self.reports_page,
        ]
        for page in self._pages:
            self.stack.addWidget(page)
            if hasattr(page, "status_msg"):
                page.status_msg.connect(self._show_status)

        self.storage_page.data_changed.connect(self.pos_page.refresh_products)
        self.category_page.data_changed.connect(self.pos_page.refresh_products)
        self.pos_page.transaction_completed.connect(self.reports_page.refresh_data)

        # ── Status bar ────────────────────────────────────────────────────────
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._show_status("RetailPOS ready")

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_page_changed(self, idx: int) -> None:
        self.header.set_title(_PAGE_TITLES[idx])
        self.stack.setCurrentIndex(idx)
        current_page = self._pages[idx]
        if hasattr(current_page, "refresh_data"):
            current_page.refresh_data()

    def _toggle_online(self) -> None:
        sync_msg = STATE.toggle_online()
        self.header.update_sync_ui()
        if sync_msg:
            self._show_status(sync_msg)
        else:
            self._show_status("Switched to offline mode – transactions will be queued locally")

    def _show_status(self, msg: str) -> None:
        self.status_bar.showMessage(f"  {msg}", 5000)
