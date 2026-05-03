# ─────────────────────────────────────────────────────────────────────────────
# views/components/header.py
#
# Topbar widget: page title, global search bar, online/offline toggle button,
# and offline-queue badge.
# ─────────────────────────────────────────────────────────────────────────────

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton, QLabel
from PyQt6.QtCore import pyqtSignal

from views.styles.theme_manager import make_label
from views.styles.palettes import (
    SUCCESS_BG, SUCCESS_FG,
    DANGER_BG, DANGER_FG,
    WARNING_BG, WARNING_FG,
    BORDER,
)
from data.state import STATE


class Header(QWidget):
    """
    Horizontal topbar that sits above the page stack.

    Signals
    -------
    toggle_online : emitted when the user clicks the sync button.
                    The parent window owns the actual state-toggle logic
                    and calls update_sync_ui() afterwards.
    """

    toggle_online: pyqtSignal = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("topbar")
        self.setFixedHeight(60)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(24, 0, 24, 0)
        lay.setSpacing(12)

        # Page title (updated by MainWindow on navigation)
        self.page_title = make_label("Dashboard", 15, bold=True)
        lay.addWidget(self.page_title)
        lay.addStretch()

        # Global search (cosmetic – pages have their own search bars)
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  Quick search…")
        self.search.setFixedWidth(260)
        lay.addWidget(self.search)

        lay.addSpacing(8)

        # Online / Offline toggle button
        self.sync_btn = QPushButton()
        self.sync_btn.setFixedWidth(120)
        self.sync_btn.clicked.connect(self._on_toggle)
        lay.addWidget(self.sync_btn)

        # Pending-queue badge
        self.queue_lbl = QLabel()
        self.queue_lbl.setObjectName("queueBadge")
        self.queue_lbl.hide()
        lay.addWidget(self.queue_lbl)

        self.update_sync_ui()

    # ── Public API ────────────────────────────────────────────────────────────

    def set_title(self, title: str) -> None:
        """Update the page title shown in the topbar."""
        self.page_title.setText(title)

    def update_sync_ui(self) -> None:
        """Re-render the sync button and queue badge from current STATE."""
        if STATE.is_online:
            self.sync_btn.setText("🟢  Online")
            self.sync_btn.setStyleSheet(
                f"background:{SUCCESS_BG}; color:{SUCCESS_FG}; "
                f"border:1px solid #a7f3d0; border-radius:8px; "
                f"padding:6px 12px; font-weight:600;"
            )
        else:
            self.sync_btn.setText("🔴  Offline")
            self.sync_btn.setStyleSheet(
                f"background:{DANGER_BG}; color:{DANGER_FG}; "
                f"border:1px solid #fecaca; border-radius:8px; "
                f"padding:6px 12px; font-weight:600;"
            )

        pending = len(STATE.offline_queue)
        if pending > 0:
            self.queue_lbl.setText(f"  {pending} queued  ")
            self.queue_lbl.show()
        else:
            self.queue_lbl.hide()

    # ── Private ───────────────────────────────────────────────────────────────

    def _on_toggle(self) -> None:
        """Emit signal; the MainWindow will mutate STATE and call update_sync_ui."""
        self.toggle_online.emit()
