# ─────────────────────────────────────────────────────────────────────────────
# views/main_window.py
# ─────────────────────────────────────────────────────────────────────────────

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStackedWidget, QScrollArea, QStatusBar,
)

from views.components.header import Header
from views.components.sidebar import Sidebar
import config
from views.pages.dashboard import DashboardPage
from views.pages.pos import POSPage
from views.pages.storage import StoragePage
from views.pages.productcategory import CategoryProductPage
from views.pages.suppliers import SuppliersPage
from views.pages.loyalty import LoyaltyPage
from views.pages.report import ReportsPage
from views.pages.user_management import UserManagementPage
from data.state import STATE


_PAGE_TITLES = [
    "Dashboard",
    "Point of Sale",
    "Inventory Management",
    "Product Category Management",
    "Supplier Management",
    "Loyalty Program",
    "Reports",
    "Kelola User",
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

    def __init__(self, auth_token: str = "", username: str = "") -> None:
        super().__init__()
        self._auth_token = auth_token
        self._username   = username
        self.setWindowTitle(f"{config.APP_NAME} — Sistem POS")
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
        self.sidebar.logout_requested.connect(self._on_logout)
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
        self.pos_page = POSPage(self.header, auth_token=self._auth_token)
        self.storage_page = StoragePage()
        self.category_page = CategoryProductPage()
        self.suppliers_page = SuppliersPage()
        self.loyalty_page = LoyaltyPage(auth_token=self._auth_token)
        self.reports_page = ReportsPage()
        self.user_mgmt_page = UserManagementPage()

        self._pages = [
            self.dashboard_page,
            self.pos_page,
            self.storage_page,
            self.category_page,
            self.suppliers_page,
            self.loyalty_page,
            self.reports_page,
            self.user_mgmt_page,
        ]
        for page in self._pages:
            self.stack.addWidget(page)
            if hasattr(page, "status_msg"):
                page.status_msg.connect(self._show_status)

        self.storage_page.data_changed.connect(self.pos_page.refresh_products)
        self.category_page.data_changed.connect(self.pos_page.refresh_products)
        self.pos_page.transaction_completed.connect(self.reports_page.refresh_data)
        self.pos_page.transaction_completed.connect(self.loyalty_page.refresh_data)

        # ── Status bar ────────────────────────────────────────────────────────
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._show_status("RetailPOS ready")

        # Populate sidebar user info and apply RBAC restrictions
        if self._username:
            self._refresh_user_display()
        self._apply_permissions()

    def _refresh_user_display(self) -> None:
        """Update sidebar with current user name and role label."""
        try:
            from models import user_model
            user_id = user_model.get_user_id_by_token(self._auth_token)
            user    = user_model.get_user(user_id) if user_id else {}
            role_map = {1: "Admin", 2: "Kasir", 3: "Stok Manager"}
            role_label = role_map.get(int(user.get("role_id", 0)), "—")
            display_name = user.get("name", self._username) or self._username
        except Exception:
            display_name = self._username
            role_label   = ""
        self.sidebar.set_user(display_name, role_label)

    def _apply_permissions(self) -> None:
        """Fetch the user's allowed features and restrict sidebar navigation."""
        try:
            from controllers import user_controller
            allowed = user_controller.get_allowed_features(self._auth_token)
        except Exception:
            allowed = []   # deny all on error (fail-safe)
        self.sidebar.apply_permissions(allowed)
        # Give user_mgmt_page the token so it can make authenticated calls
        self.user_mgmt_page.set_auth_token(self._auth_token)
        self.pos_page.set_auth_token(self._auth_token)

    def _on_logout(self) -> None:
        """Invalidate session, close window, re-open LoginDialog."""
        try:
            from controllers import user_controller
            user_controller.logout(self._auth_token)
        except Exception:
            pass  # always proceed even if token was already gone

        self.close()

        from views.pages.login import LoginDialog
        dlg = LoginDialog()
        if dlg.exec():
            win = MainWindow(
                auth_token=dlg.auth_token or "",
                username=dlg.username or "",
            )
            win.show()
            # Keep a reference so the GC doesn't destroy it
            import sys
            # Attach to the QApplication instance to stay alive
            from PyQt6.QtWidgets import QApplication
            QApplication.instance()._main_win = win  # type: ignore[attr-defined]

    def _on_page_changed(self, idx: int) -> None:
        self.header.set_title(_PAGE_TITLES[idx])
        self.stack.setCurrentIndex(idx)

        # Halaman dengan scroll internal sendiri → matikan scroll global
        # agar tidak ada double scroll bar
        SELF_SCROLLING_PAGES = {4}  # index 4 = SuppliersPage
        from PyQt6.QtCore import Qt as _Qt
        if idx in SELF_SCROLLING_PAGES:
            self.content_scroll.setVerticalScrollBarPolicy(
                _Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
        else:
            self.content_scroll.setVerticalScrollBarPolicy(
                _Qt.ScrollBarPolicy.ScrollBarAsNeeded
            )

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