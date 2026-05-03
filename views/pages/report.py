# ─────────────────────────────────────────────────────────────────────────────
# views/pages/report.py
# ─────────────────────────────────────────────────────────────────────────────

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QComboBox, QGroupBox, QGridLayout, QTableWidget,
    QTableWidgetItem, QHeaderView,
)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QColor

from views.styles.theme_manager import make_label, card_style
from views.styles.palettes import DANGER_FG, WARNING_FG, SUCCESS_FG, BG_SURFACE, BORDER
from data.store import TRANSACTIONS


# Foreground colour per transaction status
_STATUS_FG = {
    "completed": SUCCESS_FG,
    "refunded":  DANGER_FG,
    "pending":   WARNING_FG,
}


class ReportsPage(QWidget):
    """Report builder: filter transactions, view summary KPIs, export."""

    status_msg = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        lay = QVBoxLayout(self)
        lay.setSpacing(16)
        lay.setContentsMargins(0, 0, 0, 0)

        lay.addWidget(make_label("Reports", 18, bold=True))
        lay.addWidget(make_label("Generate and export business reports", 12, color="#64748b"))

        lay.addWidget(self._build_filter_card())

        # Summary stat cards (rebuilt on every filter change)
        self.stats_row = QHBoxLayout()
        lay.addLayout(self.stats_row)

        lay.addWidget(self._build_table())

        self._refresh()

    # ── Builder helpers ───────────────────────────────────────────────────────

    def _build_filter_card(self) -> QGroupBox:
        grp = QGroupBox("Report Builder")
        grp.setStyleSheet(
            f"QGroupBox {{ background:{BG_SURFACE}; border:1px solid {BORDER}; border-radius:10px; }}"
        )
        fl = QGridLayout(grp)

        # Location
        fl.addWidget(make_label("Location", 11, color="#64748b"), 0, 0)
        self.loc_combo = QComboBox()
        self.loc_combo.addItems(["All Locations", "Downtown Store", "Mall Location", "Airport Store"])
        self.loc_combo.currentTextChanged.connect(self._refresh)
        fl.addWidget(self.loc_combo, 1, 0)

        # Payment method
        fl.addWidget(make_label("Payment Method", 11, color="#64748b"), 0, 1)
        self.pay_combo = QComboBox()
        self.pay_combo.addItems(["All Methods", "card", "cash", "mobile"])
        self.pay_combo.currentTextChanged.connect(self._refresh)
        fl.addWidget(self.pay_combo, 1, 1)

        # Status
        fl.addWidget(make_label("Status", 11, color="#64748b"), 0, 2)
        self.status_combo = QComboBox()
        self.status_combo.addItems(["All Statuses", "completed", "refunded", "pending"])
        self.status_combo.currentTextChanged.connect(self._refresh)
        fl.addWidget(self.status_combo, 1, 2)

        # Export buttons
        export_row = QHBoxLayout()
        for fmt in ("PDF", "CSV", "Excel"):
            btn = QPushButton(f"⬇  {fmt}")
            btn.setObjectName("btnOutline")
            btn.clicked.connect(lambda _, f=fmt: self.status_msg.emit(f"Exporting as {f}…"))
            export_row.addWidget(btn)
        export_row.addStretch()
        fl.addLayout(export_row, 2, 0, 1, 3)

        return grp

    def _build_table(self) -> QTableWidget:
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Transaction ID", "Date", "Time", "Total", "Payment", "Status"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        return self.table

    # ── Data ─────────────────────────────────────────────────────────────────

    def _refresh(self) -> None:
        loc = self.loc_combo.currentText()
        pay = self.pay_combo.currentText()
        st  = self.status_combo.currentText()

        rows = [
            t for t in TRANSACTIONS
            if (loc == "All Locations" or t["location"] == loc)
            and (pay == "All Methods"  or t["payment"]  == pay)
            and (st  == "All Statuses" or t["status"]   == st)
        ]

        self._rebuild_stats(rows)
        self._populate_table(rows)

    def _rebuild_stats(self, rows: list[dict]) -> None:
        # Clear previous stat cards
        while self.stats_row.count():
            item = self.stats_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        total_rev = sum(t["total"] for t in rows)
        avg = total_rev / len(rows) if rows else 0.0

        for title, val in [
            ("Total Revenue", f"${total_rev:.2f}"),
            ("Transactions",  str(len(rows))),
            ("Avg Order",     f"${avg:.2f}"),
        ]:
            card = QWidget()
            card.setStyleSheet(card_style() + " min-width:140px;")
            cv = QVBoxLayout(card)
            cv.addWidget(make_label(title, 11, color="#64748b"))
            cv.addWidget(make_label(val, 18, bold=True))
            self.stats_row.addWidget(card)

        self.stats_row.addStretch()

    def _populate_table(self, rows: list[dict]) -> None:
        self.table.setRowCount(len(rows))
        for r, t in enumerate(rows):
            self.table.setItem(r, 0, QTableWidgetItem(t["id"]))
            self.table.setItem(r, 1, QTableWidgetItem(t["date"]))
            self.table.setItem(r, 2, QTableWidgetItem(t["time"]))
            self.table.setItem(r, 3, QTableWidgetItem(f"${t['total']:.2f}"))
            self.table.setItem(r, 4, QTableWidgetItem(t["payment"].capitalize()))

            fg = _STATUS_FG.get(t["status"], "#0f172a")
            status_item = QTableWidgetItem(t["status"].capitalize())
            status_item.setForeground(QColor(fg))
            self.table.setItem(r, 5, status_item)
