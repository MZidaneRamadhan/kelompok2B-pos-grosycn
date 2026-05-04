# ─────────────────────────────────────────────────────────────────────────────
# views/pages/storage.py
# ─────────────────────────────────────────────────────────────────────────────

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView,
)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QColor

from views.styles.theme_manager import make_label, alert_style, card_style
from views.styles.palettes import DANGER_FG, SUCCESS_FG, BG_SURFACE, BORDER
from data.store import PRODUCTS


class StoragePage(QWidget):
    """Inventory management: searchable product table with low-stock alerts."""

    status_msg = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        lay = QVBoxLayout(self)
        lay.setSpacing(16)
        lay.setContentsMargins(0, 0, 0, 0)

        lay.addLayout(self._build_header())

        self._low_products = [p for p in PRODUCTS if p["stock"] < p["low"]]
        if self._low_products:
            alert = QLabel(
                f"⚠️  {len(self._low_products)} products are running low – consider reordering"
            )
            alert.setStyleSheet(alert_style("warning"))
            lay.addWidget(alert)

        lay.addLayout(self._build_stats())
        lay.addLayout(self._build_controls())
        lay.addWidget(self._build_table())

        self._refresh()

    # ── Sections ──────────────────────────────────────────────────────────────

    def _build_header(self) -> QHBoxLayout:
        hdr = QHBoxLayout()

        info = QVBoxLayout()
        info.addWidget(make_label("Inventory Management", 18, bold=True))
        info.addWidget(make_label("Manage stock levels and supplier relationships", 12, color="#64748b"))
        hdr.addLayout(info)
        hdr.addStretch()

        add_btn = QPushButton("+ Add Product")
        add_btn.clicked.connect(lambda: self.status_msg.emit("Add Product feature coming soon"))
        hdr.addWidget(add_btn)

        return hdr

    def _build_stats(self) -> QHBoxLayout:
        total_val = sum(p["pricing"][0]["price"] * p["stock"] for p in PRODUCTS)
        row = QHBoxLayout()
        for title, val in [
            ("Total Products",   str(len(PRODUCTS))),
            ("Low Stock",        str(len(self._low_products))),
            ("Total Stock Value", f"${total_val:,.0f}"),
        ]:
            card = QWidget()
            card.setStyleSheet(card_style())
            cv = QVBoxLayout(card)
            cv.addWidget(make_label(title, 11, color="#64748b"))
            cv.addWidget(make_label(val, 18, bold=True))
            row.addWidget(card)
        row.addStretch()
        return row

    def _build_controls(self) -> QHBoxLayout:
        ctrl = QHBoxLayout()

        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  Search by name, SKU, brand…")
        self.search.textChanged.connect(self._refresh)
        ctrl.addWidget(self.search)

        self.low_cb = QCheckBox("Low stock only")
        self.low_cb.toggled.connect(self._refresh)
        ctrl.addWidget(self.low_cb)

        return ctrl

    def _build_table(self) -> QTableWidget:
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["Product", "SKU", "Category", "Brand", "Stock", "Status", "Base Price"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        return self.table

    # ── Data ─────────────────────────────────────────────────────────────────

    def _refresh(self) -> None:
        q = self.search.text().lower()
        low_only = self.low_cb.isChecked()

        rows = [
            p for p in PRODUCTS
            if (
                q in p["name"].lower()
                or q in p["sku"].lower()
                or q in (p.get("brand") or "").lower()
            )
            and (not low_only or p["stock"] < p["low"])
        ]

        self.table.setRowCount(len(rows))
        for r, p in enumerate(rows):
            self.table.setItem(r, 0, QTableWidgetItem(f"{p['image']}  {p['name']}"))
            self.table.setItem(r, 1, QTableWidgetItem(p["sku"]))
            self.table.setItem(r, 2, QTableWidgetItem(p["category"]))
            self.table.setItem(r, 3, QTableWidgetItem(p.get("brand", "")))
            self.table.setItem(r, 4, QTableWidgetItem(str(p["stock"])))

            is_low = p["stock"] < p["low"]
            status_item = QTableWidgetItem("⚠ Low Stock" if is_low else "✓ In Stock")
            status_item.setForeground(QColor(DANGER_FG if is_low else SUCCESS_FG))
            self.table.setItem(r, 5, status_item)

            self.table.setItem(r, 6, QTableWidgetItem(f"${p['pricing'][0]['price']:.2f}"))
