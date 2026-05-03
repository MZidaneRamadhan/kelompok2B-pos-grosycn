# ─────────────────────────────────────────────────────────────────────────────
# views/pages/pos.py
# ─────────────────────────────────────────────────────────────────────────────

import random
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QScrollArea, QGridLayout, QComboBox, QDialog,
    QDialogButtonBox, QFormLayout, QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal

from views.styles.theme_manager import make_label, h_line, stock_badge_style
from views.styles.palettes import PRIMARY, BG_SURFACE, BORDER, BG_APP
from data.store import PRODUCTS
from data.state import STATE


# ─────────────────────────────── Payment Dialog ───────────────────────────────

class PaymentDialog(QDialog):
    """Modal dialog for selecting a payment method and confirming checkout."""

    def __init__(self, subtotal: float, tax: float, total: float, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Complete Payment")
        self.setFixedWidth(420)
        self.setModal(True)
        self.payment_method: str = "card"

        lay = QVBoxLayout(self)
        lay.setSpacing(16)
        lay.setContentsMargins(24, 24, 24, 24)

        lay.addWidget(make_label("Complete Payment", 16, bold=True))
        lay.addWidget(h_line())
        lay.addWidget(make_label("Payment Method", 12, color="#64748b"))

        # Method buttons
        methods_row = QHBoxLayout()
        self._pay_btns: dict[str, QPushButton] = {}
        for method, label in [("card", "💳\nCard"), ("cash", "💵\nCash"), ("mobile", "📱\nMobile")]:
            btn = QPushButton(label)
            btn.setObjectName("payMethodBtn")
            btn.setFixedHeight(70)
            btn.clicked.connect(lambda _, m=method: self._set_method(m))
            self._pay_btns[method] = btn
            methods_row.addWidget(btn)
        lay.addLayout(methods_row)
        self._set_method("card")

        lay.addWidget(h_line())

        form = QFormLayout()
        form.addRow(make_label("Subtotal", 12, color="#64748b"), make_label(f"${subtotal:.2f}", 12))
        form.addRow(make_label("Tax (10%)", 12, color="#64748b"), make_label(f"${tax:.2f}", 12))
        lay.addLayout(form)

        lay.addWidget(h_line())

        total_row = QHBoxLayout()
        total_row.addWidget(make_label("Total", 16, bold=True))
        total_row.addStretch()
        total_row.addWidget(make_label(f"${total:.2f}", 18, bold=True, color=PRIMARY))
        lay.addLayout(total_row)

        btns = QDialogButtonBox()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("btnOutline")
        pay_btn = QPushButton("Complete Payment")
        btns.addButton(cancel_btn, QDialogButtonBox.ButtonRole.RejectRole)
        btns.addButton(pay_btn, QDialogButtonBox.ButtonRole.AcceptRole)
        cancel_btn.clicked.connect(self.reject)
        pay_btn.clicked.connect(self.accept)
        lay.addWidget(btns)

    def _set_method(self, method: str) -> None:
        self.payment_method = method
        for m, btn in self._pay_btns.items():
            if m == method:
                btn.setStyleSheet(
                    f"background:{PRIMARY}; color:#fff; border-radius:10px; "
                    f"padding:12px 8px; font-size:13px; border:1px solid {PRIMARY};"
                )
            else:
                btn.setStyleSheet(
                    f"background:transparent; color:#0f172a; border-radius:10px; "
                    f"padding:12px 8px; font-size:13px; border:1px solid {BORDER};"
                )


# ─────────────────────────────── POS Page ────────────────────────────────────

class POSPage(QWidget):
    """
    Main Point-of-Sale screen.

    Parameters
    ----------
    header_ref : Header
        Reference to the topbar so it can refresh the queue badge after an
        offline transaction is queued.
    """

    status_msg = pyqtSignal(str)

    def __init__(self, header_ref, parent=None) -> None:
        super().__init__(parent)
        self.header_ref = header_ref
        self._unit_selections: dict[str, str] = {}

        root = QHBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(0, 0, 0, 0)

        root.addLayout(self._build_product_panel(), stretch=2)
        root.addWidget(self._build_cart_panel(), stretch=0)

        self._refresh_grid()
        self._refresh_cart()

    # ── Product panel ─────────────────────────────────────────────────────────

    def _build_product_panel(self) -> QVBoxLayout:
        lay = QVBoxLayout()
        lay.setSpacing(12)

        lay.addWidget(make_label("Point of Sale", 18, bold=True))
        lay.addWidget(make_label("Select products and process transactions", 12, color="#64748b"))

        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  Search by name, SKU, brand…")
        self.search.textChanged.connect(self._refresh_grid)
        lay.addWidget(self.search)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(12)
        scroll.setWidget(self.grid_container)
        lay.addWidget(scroll)

        return lay

    # ── Cart panel ────────────────────────────────────────────────────────────

    def _build_cart_panel(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(300)
        panel.setStyleSheet(
            f"background:{BG_SURFACE}; border:1px solid {BORDER}; border-radius:10px;"
        )

        lay = QVBoxLayout(panel)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)

        # Header row
        hdr = QHBoxLayout()
        hdr.addWidget(make_label("Current Order", 14, bold=True))
        hdr.addStretch()
        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("btnOutline")
        clear_btn.clicked.connect(self._clear_cart)
        hdr.addWidget(clear_btn)
        lay.addLayout(hdr)

        # Scrollable cart items
        self.cart_scroll = QScrollArea()
        self.cart_scroll.setWidgetResizable(True)
        self.cart_scroll.setMinimumHeight(300)
        self.cart_inner = QWidget()
        self.cart_lay = QVBoxLayout(self.cart_inner)
        self.cart_lay.setSpacing(8)
        self.cart_lay.addStretch()
        self.cart_scroll.setWidget(self.cart_inner)
        lay.addWidget(self.cart_scroll)

        lay.addWidget(h_line())

        self.subtotal_lbl = make_label("Subtotal: $0.00", 12, color="#64748b")
        self.tax_lbl = make_label("Tax (10%): $0.00", 12, color="#64748b")
        lay.addWidget(self.subtotal_lbl)
        lay.addWidget(self.tax_lbl)
        lay.addWidget(h_line())

        self.total_lbl = make_label("Total: $0.00", 16, bold=True)
        lay.addWidget(self.total_lbl)

        self.checkout_btn = QPushButton("Checkout")
        self.checkout_btn.clicked.connect(self._checkout)
        lay.addWidget(self.checkout_btn)

        return panel

    # ── Grid refresh ─────────────────────────────────────────────────────────

    def _filtered_products(self) -> list[dict]:
        q = self.search.text().lower()
        if not q:
            return PRODUCTS
        return [
            p for p in PRODUCTS
            if q in p["name"].lower()
            or q in p["sku"].lower()
            or q in p["category"].lower()
            or q in (p.get("brand") or "").lower()
        ]

    def _refresh_grid(self) -> None:
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        prods = self._filtered_products()
        if not prods:
            lbl = make_label("No products found", 13, color="#94a3b8")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grid_layout.addWidget(lbl, 0, 0)
            return

        cols = 3
        for i, p in enumerate(prods):
            self.grid_layout.addWidget(self._product_card(p), i // cols, i % cols)

    def _product_card(self, p: dict) -> QWidget:
        w = QWidget()
        w.setStyleSheet(
            f"background:{BG_SURFACE}; border:1px solid {BORDER}; border-radius:10px;"
        )
        v = QVBoxLayout(w)
        v.setContentsMargins(14, 14, 14, 14)
        v.setSpacing(6)

        # Emoji + stock badge
        top = QHBoxLayout()
        top.addWidget(make_label(p["image"], 28))
        top.addStretch()
        is_low = p["stock"] < p["low"]
        stock_lbl = QLabel(str(p["stock"]))
        stock_lbl.setStyleSheet(stock_badge_style(is_low))
        top.addWidget(stock_lbl)
        v.addLayout(top)

        v.addWidget(make_label(p["name"], 12, bold=True))
        v.addWidget(make_label(p.get("brand", ""), 11, color="#64748b"))
        v.addWidget(make_label(p["sku"], 10, color="#94a3b8"))

        # Unit selector
        pid = p["id"]
        unit_combo = QComboBox()
        for pricing in p["pricing"]:
            u, pr, qty = pricing["unit"], pricing["price"], pricing["qty"]
            if u == "piece":
                label = f"Per Piece – ${pr:.2f}"
            elif u == "pack":
                label = f"Per Pack ({qty}) – ${pr:.2f}"
            else:
                label = f"Per Box ({qty}) – ${pr:.2f}"
            unit_combo.addItem(label, userData=u)

        saved = self._unit_selections.get(pid, "piece")
        for idx in range(unit_combo.count()):
            if unit_combo.itemData(idx) == saved:
                unit_combo.setCurrentIndex(idx)
                break

        unit_combo.currentIndexChanged.connect(
            lambda _, pid=pid, cb=unit_combo: self._unit_selections.__setitem__(pid, cb.currentData())
        )
        v.addWidget(unit_combo)

        # Price + Add button
        bottom = QHBoxLayout()
        cur_unit = self._unit_selections.get(pid, "piece")
        pricing = next((pr for pr in p["pricing"] if pr["unit"] == cur_unit), p["pricing"][0])
        bottom.addWidget(make_label(f"${pricing['price']:.2f}", 15, bold=True))
        bottom.addStretch()
        add_btn = QPushButton("+ Add")
        add_btn.setObjectName("btnSmall")
        add_btn.clicked.connect(lambda _, p=p, cb=unit_combo: self._add_to_cart(p, cb))
        bottom.addWidget(add_btn)
        v.addLayout(bottom)

        return w

    # ── Cart refresh ─────────────────────────────────────────────────────────

    def _refresh_cart(self) -> None:
        # Remove all widgets except the trailing stretch
        while self.cart_lay.count() > 1:
            item = self.cart_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for item in STATE.cart:
            self.cart_lay.insertWidget(self.cart_lay.count() - 1, self._cart_row(item))

        subtotal = STATE.cart_total()
        tax = subtotal * 0.1
        self.subtotal_lbl.setText(f"Subtotal: ${subtotal:.2f}")
        self.tax_lbl.setText(f"Tax (10%): ${tax:.2f}")
        self.total_lbl.setText(f"Total: ${subtotal + tax:.2f}")

    def _cart_row(self, item: dict) -> QWidget:
        w = QWidget()
        w.setStyleSheet(
            f"background:{BG_APP}; border:1px solid {BORDER}; border-radius:8px;"
        )
        h = QHBoxLayout(w)
        h.setContentsMargins(10, 8, 10, 8)
        h.setSpacing(8)

        h.addWidget(make_label(item["image"], 18))

        info = QVBoxLayout()
        info.addWidget(make_label(item["productName"], 11, bold=True))
        info.addWidget(make_label(f"${item['price']:.2f} / {item['unit']}", 10, color="#64748b"))
        h.addLayout(info)
        h.addStretch()

        # Qty controls
        ctrl = QVBoxLayout()
        qty_row = QHBoxLayout()
        for sym, delta in [("−", -1), ("+", 1)]:
            btn = QPushButton(sym)
            btn.setFixedSize(24, 24)
            btn.setObjectName("btnOutline" if sym == "−" else "btnIcon")
            btn.clicked.connect(lambda _, i=item, d=delta: self._change_qty(i, d))
            if sym == "−":
                qty_row.addWidget(btn)
            else:
                qty_lbl = QLabel(str(item["qty"]))
                qty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                qty_lbl.setFixedWidth(24)
                qty_row.addWidget(qty_lbl)
                qty_row.addWidget(btn)
        ctrl.addLayout(qty_row)

        line_total = make_label(f"${item['price'] * item['qty']:.2f}", 11, bold=True, color=PRIMARY)
        line_total.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ctrl.addWidget(line_total)
        h.addLayout(ctrl)

        rm = QPushButton("🗑")
        rm.setObjectName("btnGhost")
        rm.setFixedSize(24, 24)
        rm.clicked.connect(lambda _, i=item: self._remove(i))
        h.addWidget(rm)

        return w

    # ── Actions ───────────────────────────────────────────────────────────────

    def _add_to_cart(self, p: dict, unit_combo: QComboBox) -> None:
        unit = unit_combo.currentData()
        pricing = next((pr for pr in p["pricing"] if pr["unit"] == unit), p["pricing"][0])
        STATE.add_to_cart(p["id"], p["name"], pricing["price"], unit, p["image"])
        self._refresh_cart()
        self.status_msg.emit(f"Added {p['name']} ({unit}) to cart")

    def _change_qty(self, item: dict, delta: int) -> None:
        STATE.update_qty(item["productId"], item["unit"], item["qty"] + delta)
        self._refresh_cart()

    def _remove(self, item: dict) -> None:
        STATE.remove_from_cart(item["productId"], item["unit"])
        self._refresh_cart()

    def _clear_cart(self) -> None:
        STATE.clear_cart()
        self._refresh_cart()

    def _checkout(self) -> None:
        if not STATE.cart:
            QMessageBox.information(self, "Empty Cart", "Add products before checking out.")
            return

        subtotal = STATE.cart_total()
        tax = subtotal * 0.1
        total = subtotal + tax

        dlg = PaymentDialog(subtotal, tax, total, self)
        if not dlg.exec():
            return

        txn_id = f"TXN-{datetime.now().strftime('%Y%m%d')}-{random.randint(1, 999):03d}"
        if not STATE.is_online:
            STATE.offline_queue.append({"id": txn_id, "total": total})
            self.header_ref.update_sync_ui()
            self.status_msg.emit(f"Transaction {txn_id} queued offline – will sync when online")
        else:
            self.status_msg.emit(f"Payment successful! Transaction {txn_id} complete")

        STATE.clear_cart()
        self._refresh_cart()
