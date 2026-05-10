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
from database import TransactionRepository


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

    def refresh_data(self) -> None:
        """Refresh report contents from SQLite."""
        self._refresh()

    # ── Builder helpers ───────────────────────────────────────────────────────

    def _build_filter_card(self) -> QGroupBox:
        grp = QGroupBox("Report Builder")
        grp.setStyleSheet(
            f"QGroupBox {{ background:{BG_SURFACE}; border:1px solid {BORDER}; border-radius:10px; }}"
        )
        fl = QGridLayout(grp)

        # Payment method
        fl.addWidget(make_label("Payment Method", 11, color="#64748b"), 0, 0)
        self.pay_combo = QComboBox()
        self.pay_combo.addItems(["All Methods", "card", "cash", "mobile", "qris", "transfer"])
        self.pay_combo.currentTextChanged.connect(self._refresh)
        fl.addWidget(self.pay_combo, 1, 0)

        # Member filter
        fl.addWidget(make_label("Customer Type", 11, color="#64748b"), 0, 1)
        self.member_combo = QComboBox()
        self.member_combo.addItems(["All", "Member", "Non-Member"])
        self.member_combo.currentTextChanged.connect(self._refresh)
        fl.addWidget(self.member_combo, 1, 1)

        # Export buttons
        export_row = QHBoxLayout()
        for fmt in ("PDF", "CSV", "Excel"):
            btn = QPushButton(f"⬇  {fmt}")
            btn.setObjectName("btnOutline")
            btn.clicked.connect(lambda _, f=fmt: self.status_msg.emit(f"Exporting as {f}…"))
            export_row.addWidget(btn)
        export_row.addStretch()
        fl.addLayout(export_row, 2, 0, 1, 2)

        return grp

    def _build_table(self) -> QTableWidget:
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["Order ID", "Date", "Time", "Customer", "Total", "Payment", "Member"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        return self.table

    # ── Data ─────────────────────────────────────────────────────────────────

    def _refresh(self) -> None:
        pay    = self.pay_combo.currentText()
        member = self.member_combo.currentText()

        # Ambil semua transaksi dari SQLite via TransactionRepository
        db_rows = TransactionRepository.get_all()

        rows = []
        for row in db_rows:
            txn = dict(row)

            txn_payment = str(txn.get("payment_method", "")).lower()
            txn_is_member = bool(txn.get("is_member", 0))

            # Filter payment method
            if pay != "All Methods" and txn_payment != pay.lower():
                continue

            # Filter member/non-member
            if member == "Member" and not txn_is_member:
                continue
            if member == "Non-Member" and txn_is_member:
                continue

            # Pisah tanggal dan waktu dari order_date
            order_date = str(txn.get("order_date", ""))
            date_part = order_date.split(" ")[0] if " " in order_date else order_date
            time_part = order_date.split(" ")[1] if " " in order_date else ""

            rows.append({
                "order_id":      txn.get("order_id", ""),
                "date":          date_part,
                "time":          time_part,
                "customer_name": txn.get("customer_name") or "-",
                "total":         float(txn.get("total", 0)),
                "payment":       txn_payment,
                "is_member":     txn_is_member,
                "cashier":       txn.get("cashier", ""),
            })

        self._rebuild_stats(rows)
        self._populate_table(rows)

    def _rebuild_stats(self, rows: list[dict]) -> None:
        # Bersihkan stat cards sebelumnya
        while self.stats_row.count():
            item = self.stats_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        total_rev = sum(t["total"] for t in rows)
        avg       = total_rev / len(rows) if rows else 0.0
        members   = sum(bool(t["is_member"])
                    for t in rows)

        for title, val in [
            ("Total Revenue",  f"Rp{total_rev:,.0f}"),
            ("Transactions",   str(len(rows))),
            ("Avg Order",      f"Rp{avg:,.0f}"),
            ("Member Trx",     str(members)),
        ]:
            card = QWidget()
            card.setStyleSheet(f"{card_style()} min-width:140px;")
            cv = QVBoxLayout(card)
            cv.addWidget(make_label(title, 11, color="#64748b"))
            cv.addWidget(make_label(val, 18, bold=True))
            self.stats_row.addWidget(card)

        self.stats_row.addStretch()

    def _populate_table(self, rows: list[dict]) -> None:
        self.table.setRowCount(len(rows))
        for r, t in enumerate(rows):
            self.table.setItem(r, 0, QTableWidgetItem(t["order_id"]))
            self.table.setItem(r, 1, QTableWidgetItem(t["date"]))
            self.table.setItem(r, 2, QTableWidgetItem(t["time"]))
            self.table.setItem(r, 3, QTableWidgetItem(t["customer_name"]))
            self.table.setItem(r, 4, QTableWidgetItem(f"Rp{t['total']:,.0f}"))
            self.table.setItem(r, 5, QTableWidgetItem(t["payment"].capitalize()))

            member_label = "✅ Member" if t["is_member"] else "—"
            member_item  = QTableWidgetItem(member_label)
            member_item.setForeground(QColor(SUCCESS_FG if t["is_member"] else "#94a3b8"))
            self.table.setItem(r, 6, member_item)