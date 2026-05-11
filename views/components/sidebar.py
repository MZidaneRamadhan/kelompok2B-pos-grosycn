# ─────────────────────────────────────────────────────────────────────────────
# views/components/sidebar.py
#
# Collapsible left-hand navigation sidebar.
# ─────────────────────────────────────────────────────────────────────────────

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt, pyqtSignal

from views.styles.theme_manager import make_label, h_line
from views.styles.palettes import TEXT_INVERSE, SIDEBAR_TEXT, DANGER_FG, DANGER_BG, DANGER_BORDER


class Sidebar(QWidget):
    """
    Fixed-width sidebar with nav buttons.

    Signals
    -------
    page_changed(int)   : index of the newly selected page.
    logout_requested()  : emitted after the user confirms logout.
    """

    page_changed: pyqtSignal = pyqtSignal(int)
    logout_requested: pyqtSignal = pyqtSignal()

    # (emoji, display label, required_permission | None)
    # None  -> always visible (no permission gate)
    # str   -> key must appear in user_controller.get_allowed_features()
    PAGES: list[tuple[str, str, str | None]] = [
        ("📊", "Dashboard",        None),
        ("🛒", "Point of Sale",    "transaksi"),
        ("📦", "Inventory",        "storage"),
        ("🏷️",  "Category Product", "storage"),
        ("🚚", "Suppliers",        "supplier"),
        ("⭐", "Loyalty",          "royalti"),
        ("📈", "Reports",          "laporan"),
        ("👥", "Manage User",      "manajemen_user"),
    ]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(220)

        self._buttons: list[QPushButton] = []
        self._active: int = -1          # start at -1 so first _select always fires
        self._allowed_features: set[str] | None = None  # None = not yet applied

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Brand logo block
        logo = make_label("RetailPOS", 15, bold=True, color=TEXT_INVERSE)
        logo.setObjectName("logo")
        logo.setContentsMargins(16, 20, 16, 4)
        lay.addWidget(logo)

        tagline = make_label("Semi-Online POS", 10, color=SIDEBAR_TEXT)
        tagline.setContentsMargins(16, 0, 16, 16)
        lay.addWidget(tagline)

        lay.addWidget(h_line())
        lay.addSpacing(8)

        # Nav buttons - one per PAGES entry
        for i, (icon, label, _perm) in enumerate(self.PAGES):
            btn = QPushButton(f"  {icon}  {label}")
            btn.setObjectName("navBtn")
            btn.setProperty("active", "false")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, idx=i: self._select(idx))
            self._buttons.append(btn)
            lay.addWidget(btn)

        lay.addStretch()

        lay.addWidget(h_line())

        # Logged-in user info
        self._user_lbl = make_label("", 12, bold=True, color=TEXT_INVERSE)
        self._user_lbl.setContentsMargins(16, 10, 16, 0)
        self._user_lbl.setWordWrap(True)
        lay.addWidget(self._user_lbl)

        self._role_lbl = make_label("", 10, color=SIDEBAR_TEXT)
        self._role_lbl.setContentsMargins(16, 2, 16, 8)
        lay.addWidget(self._role_lbl)

        # Logout button
        self.logout_btn = QPushButton("  🚪  Logout")
        self.logout_btn.setObjectName("logoutBtn")
        self.logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.logout_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background: transparent;"
            f"  color: {DANGER_FG};"
            f"  border: 1px solid {DANGER_BORDER};"
            f"  border-radius: 8px;"
            f"  padding: 8px 0;"
            f"  margin: 0 12px 12px 12px;"
            f"  font-size: 13px; font-weight: 600;"
            f"  text-align: left; padding-left: 16px;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: {DANGER_BG};"
            f"}}"
            f"QPushButton:pressed {{"
            f"  background: #fecaca;"
            f"}}"
        )
        self.logout_btn.clicked.connect(self._on_logout)
        lay.addWidget(self.logout_btn)

        # Version footer
        ver = make_label("v1.0.0 · RetailPOS", 10, color="#475569")
        ver.setContentsMargins(16, 0, 16, 12)
        lay.addWidget(ver)

        # Select the first page by default (no permission filter yet)
        self._select(0)

    # Public API

    def select(self, idx: int) -> None:
        """Programmatically activate a page by index."""
        self._select(idx)

    def set_user(self, name: str, role: str) -> None:
        """Display the logged-in user's name and role at the bottom of the sidebar."""
        self._user_lbl.setText(name)
        self._role_lbl.setText(role)

    def apply_permissions(self, allowed: list[str]) -> None:
        """
        Show/hide nav buttons based on the user's allowed feature list.
        Automatically navigates to the first accessible page if the current
        one becomes locked.
        """
        self._allowed_features = set(allowed)
        first_allowed: int | None = None

        for i, (_icon, _label, perm) in enumerate(self.PAGES):
            accessible = (perm is None) or (perm in self._allowed_features)
            self._buttons[i].setVisible(accessible)
            if accessible and first_allowed is None:
                first_allowed = i

        # If the currently shown page is now inaccessible, jump to first allowed
        current_perm = self.PAGES[self._active][2] if self._active >= 0 else None
        current_ok = (current_perm is None) or (
            self._allowed_features is not None and current_perm in self._allowed_features
        )
        if not current_ok and first_allowed is not None:
            self._active = -1   # reset so _select fires the signal
            self._select(first_allowed)

    # Private

    def _on_logout(self) -> None:
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "Konfirmasi Logout",
            "Apakah kamu yakin ingin keluar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.logout_requested.emit()

    def _select(self, idx: int) -> None:
        # _allowed_features is None before apply_permissions() is called,
        # meaning no restriction yet - safe for the initial _select(0) in __init__.
        if self._allowed_features is not None:
            perm = self.PAGES[idx][2]
            if perm is not None and perm not in self._allowed_features:
                return

        if self._active == idx:
            return
        self._active = idx
        for i, btn in enumerate(self._buttons):
            btn.setProperty("active", "true" if i == idx else "false")
            btn.setStyle(btn.style())  # force Qt to re-evaluate property-based style
        self.page_changed.emit(idx)