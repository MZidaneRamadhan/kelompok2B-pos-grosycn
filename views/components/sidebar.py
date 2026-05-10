# ─────────────────────────────────────────────────────────────────────────────
# views/components/sidebar.py
#
# Collapsible left-hand navigation sidebar.
# ─────────────────────────────────────────────────────────────────────────────

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal

from views.styles.theme_manager import make_label, h_line
from views.styles.palettes import TEXT_INVERSE, SIDEBAR_TEXT


class Sidebar(QWidget):
    """
    Fixed-width sidebar with nav buttons.

    Signals
    -------
    page_changed(int) : index of the newly selected page.
    """

    page_changed: pyqtSignal = pyqtSignal(int)

    # (emoji, display label) – order must match QStackedWidget page order
    PAGES: list[tuple[str, str]] = [
        ("📊", "Dashboard"),
        ("🛒", "Point of Sale"),
        ("📦", "Inventory"),
        ("🏷️",  "Category Product"),  # ← baru, index 3
        ("🚚", "Suppliers"),
        ("⭐", "Loyalty"),
        ("📈", "Reports"),
    ]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(220)

        self._buttons: list[QPushButton] = []
        self._active: int = -1          # start at -1 so first _select always fires

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

        # Nav buttons
        for i, (icon, label) in enumerate(self.PAGES):
            btn = QPushButton(f"  {icon}  {label}")
            btn.setObjectName("navBtn")
            btn.setProperty("active", "false")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, idx=i: self._select(idx))
            self._buttons.append(btn)
            lay.addWidget(btn)

        lay.addStretch()

        # Version footer
        ver = make_label("v1.0.0 · RetailPOS", 10, color="#475569")
        ver.setContentsMargins(16, 0, 16, 16)
        lay.addWidget(ver)

        # Select the first page by default
        self._select(0)

    # ── Public API ────────────────────────────────────────────────────────────

    def select(self, idx: int) -> None:
        """Programmatically activate a page by index."""
        self._select(idx)

    # ── Private ───────────────────────────────────────────────────────────────

    def _select(self, idx: int) -> None:
        if self._active == idx:
            return
        self._active = idx
        for i, btn in enumerate(self._buttons):
            btn.setProperty("active", "true" if i == idx else "false")
            # Force Qt to re-evaluate the property-based style rule
            btn.setStyle(btn.style())
        self.page_changed.emit(idx)