# ─────────────────────────────────────────────────────────────────────────────
# views/pages/pos.py
# ─────────────────────────────────────────────────────────────────────────────

import random
import re
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QScrollArea, QGridLayout, QComboBox, QDialog,
    QDialogButtonBox, QFormLayout, QMessageBox, QSizePolicy, QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from views.styles.theme_manager import make_label, h_line, stock_badge_style
from views.styles.palettes import (
    PRIMARY, PRIMARY_LIGHT, PRIMARY_HOVER, PRIMARY_ACTIVE,
    BG_SURFACE, BG_APP, BG_MUTED,
    BORDER, TEXT_PRIMARY, TEXT_SECONDARY,
    SUCCESS_BG, SUCCESS_FG, DANGER_FG, WARNING_BG, WARNING_FG,
)
from models import kasir as backend
from database import ProductRepository


# ─────────────────────────── Payment Dialog ───────────────────────────────────

class PaymentDialog(QDialog):
    """
    Modal for selecting payment method, optionally linking a member,
    and confirming checkout.

    After exec() == Accepted:
        .payment_method  – "card" | "cash" | "mobile"
        .member_id       – str member ID or "" for walk-in
        .member_name     – display name or "Pelanggan Umum"
        .member_points   – points to be awarded (informational)
    """

    def __init__(self, subtotal: float, tax: float, total: float,
                 auth_token: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Complete Payment")
        self.setFixedWidth(460)
        self.setModal(True)
        self._auth_token = auth_token
        self._subtotal   = subtotal

        # resolved member state
        self.payment_method: str = "card"
        self.member_id:      str = ""
        self.member_name:    str = "Pelanggan Umum"
        self.member_points:  int = 0

        lay = QVBoxLayout(self)
        lay.setSpacing(14)
        lay.setContentsMargins(24, 24, 24, 24)

        lay.addWidget(make_label("Selesaikan Pembayaran", 16, bold=True))
        lay.addWidget(h_line())

        # ── Payment method ────────────────────────────────────────────────────
        lay.addWidget(make_label("Methode Pembayaran", 12, color=TEXT_SECONDARY))

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

        # ── Member lookup ─────────────────────────────────────────────────────
        lay.addWidget(make_label("Member (opsional)", 12, color=TEXT_SECONDARY))

        member_row = QHBoxLayout()
        self._member_input = QLineEdit()
        self._member_input.setPlaceholderText("Cari dengan nomor HP atau email…")
        self._member_input.returnPressed.connect(self._lookup_member)
        member_row.addWidget(self._member_input)

        lookup_btn = QPushButton("Cari")
        lookup_btn.setFixedWidth(60)
        lookup_btn.setStyleSheet(
            f"QPushButton {{ background:{PRIMARY}; color:#fff; border:none;"
            f" border-radius:8px; padding:7px 12px; font-size:12px; font-weight:600;}}"
            f"QPushButton:hover {{ background:{PRIMARY_HOVER}; }}"
        )
        lookup_btn.clicked.connect(self._lookup_member)
        member_row.addWidget(lookup_btn)

        clear_btn = QPushButton("✕")
        clear_btn.setFixedWidth(34)
        clear_btn.setToolTip("Walk-in / bukan member")
        clear_btn.setStyleSheet(
            "QPushButton { background:#f1f5f9; color:#64748b;"
            " border:1px solid #e2e8f0; border-radius:8px; font-size:13px; font-weight:700;}"
            "QPushButton:hover { background:#e2e8f0; color:#0f172a; }"
        )
        clear_btn.clicked.connect(self._clear_member)
        member_row.addWidget(clear_btn)
        lay.addLayout(member_row)

        # Member info banner (hidden until found)
        self._member_banner = QWidget()
        self._member_banner.setStyleSheet(
            f"background:{SUCCESS_BG}; border-radius:8px; padding:8px;"
        )
        banner_lay = QHBoxLayout(self._member_banner)
        banner_lay.setContentsMargins(10, 6, 10, 6)
        self._banner_name  = make_label("", 12, bold=True,   color=SUCCESS_FG)
        self._banner_tier  = make_label("", 11, color=SUCCESS_FG)
        self._banner_pts   = make_label("", 11, color=SUCCESS_FG)
        banner_lay.addWidget(QLabel("⭐"))
        banner_lay.addWidget(self._banner_name)
        banner_lay.addWidget(self._banner_tier)
        banner_lay.addStretch()
        banner_lay.addWidget(self._banner_pts)
        self._member_banner.hide()
        lay.addWidget(self._member_banner)

        # Error / feedback label
        self._member_err = make_label("", 11, color=DANGER_FG)
        self._member_err.hide()
        lay.addWidget(self._member_err)

        lay.addWidget(h_line())

        # ── Totals ────────────────────────────────────────────────────────────
        form = QFormLayout()
        form.addRow(make_label("Subtotal",  12, color=TEXT_SECONDARY), make_label(f"Rp{subtotal:.0f}", 12))
        form.addRow(make_label("Tax (10%)", 12, color=TEXT_SECONDARY), make_label(f"Rp{tax:.0f}", 12))
        lay.addLayout(form)

        lay.addWidget(h_line())

        total_row = QHBoxLayout()
        total_row.addWidget(make_label("Total", 16, bold=True))
        total_row.addStretch()
        total_row.addWidget(make_label(f"Rp{total:.0f}", 18, bold=True, color=PRIMARY))
        lay.addLayout(total_row)

        # ── Points preview ────────────────────────────────────────────────────
        self._pts_preview = make_label("", 11, color=TEXT_SECONDARY)
        self._pts_preview.hide()
        lay.addWidget(self._pts_preview)

        # ── Buttons ───────────────────────────────────────────────────────────
        btns = QDialogButtonBox()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("btnOutline")
        pay_btn = QPushButton("Complete Payment")
        pay_btn.setStyleSheet(
            f"QPushButton {{ background:{PRIMARY}; color:#fff; border:none;"
            f" border-radius:8px; padding:9px 20px; font-size:13px; font-weight:600;}}"
            f"QPushButton:hover {{ background:{PRIMARY_HOVER}; }}"
            f"QPushButton:pressed {{ background:{PRIMARY_ACTIVE}; }}"
        )
        btns.addButton(cancel_btn, QDialogButtonBox.ButtonRole.RejectRole)
        btns.addButton(pay_btn,    QDialogButtonBox.ButtonRole.AcceptRole)
        cancel_btn.clicked.connect(self.reject)
        pay_btn.clicked.connect(self.accept)
        lay.addWidget(btns)

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _set_method(self, method: str) -> None:
        self.payment_method = method
        for m, btn in self._pay_btns.items():
            if m == method:
                btn.setStyleSheet(
                    f"background:{PRIMARY}; color:#fff; border-radius:10px;"
                    f" padding:12px 8px; font-size:13px; border:1px solid {PRIMARY};"
                )
            else:
                btn.setStyleSheet(
                    f"background:transparent; color:{TEXT_PRIMARY}; border-radius:10px;"
                    f" padding:12px 8px; font-size:13px; border:1px solid {BORDER};"
                )

    def _lookup_member(self) -> None:
        identifier = self._member_input.text().strip()
        if not identifier:
            return
        self._member_err.hide()
        self._member_banner.hide()
        try:
            from controllers import loyalty_controller
            member = loyalty_controller.verify_member(self._auth_token, identifier)
            self.member_id   = member["id"]
            self.member_name = member["name"]
            # Points: 1 per Rp1.000
            self.member_points = int(self._subtotal // 1000)

            self._banner_name.setText(member["name"])
            self._banner_tier.setText(f"  •  {member.get('tier', 'Bronze')}")
            self._banner_pts.setText(f"{member.get('points', 0):,} pts")
            self._member_banner.show()

            self._pts_preview.setText(
                f"+{self.member_points} poin akan ditambahkan setelah transaksi ini"
            )
            self._pts_preview.show()
        except ValueError as e:
            self._member_err.setText(str(e))
            self._member_err.show()

    def _clear_member(self) -> None:
        self.member_id     = ""
        self.member_name   = "Pelanggan Umum"
        self.member_points = 0
        self._member_input.clear()
        self._member_banner.hide()
        self._member_err.hide()
        self._pts_preview.hide()


# ─────────────────────────────── POS Page ────────────────────────────────────

class POSPage(QWidget):
    """
    Main Point-of-Sale screen.

    Parameters
    ----------
    header_ref : Header
        Reference to the topbar so it can refresh the queue badge after an
        offline transaction is queued.
    auth_token : str
        Passed to PaymentDialog and loyalty controller for member lookup.
    """

    status_msg = pyqtSignal(str)
    transaction_completed = pyqtSignal()

    def __init__(self, header_ref, auth_token: str = "", parent=None) -> None:
        super().__init__(parent)
        self.header_ref  = header_ref
        self._auth_token = auth_token
        self._unit_selections: dict[str, str] = {}

        # Keranjang belanja in-memory
        self._cart: list[dict] = []
        self.user_id: int = 1  # default; diperbarui via set_auth_token

        root = QHBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(0, 0, 0, 0)

        root.addLayout(self._build_product_panel(), stretch=2)
        root.addWidget(self._build_cart_panel(), stretch=0)

        self._refresh_grid()
        self._refresh_cart()

    def set_auth_token(self, token: str) -> None:
        self._auth_token = token
        try:
            from models import user_model
            uid = user_model.get_user_id_by_token(token)
            if uid:
                self.user_id = uid
        except Exception:
            pass

    def refresh_products(self) -> None:
        self._refresh_grid()

    # ── Product panel ─────────────────────────────────────────────────────────

    def _build_product_panel(self) -> QVBoxLayout:
        lay = QVBoxLayout()
        lay.setSpacing(12)

        lay.addWidget(make_label("Point of Sale", 18, bold=True))
        lay.addWidget(make_label("Select products and process transactions", 12, color=TEXT_SECONDARY))

        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  Search by name, SKU, brand…")
        self.search.textChanged.connect(self._refresh_grid)
        lay.addWidget(self.search)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.grid_container = QWidget()
        self.grid_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(14)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        scroll.setWidget(self.grid_container)
        lay.addWidget(scroll)

        return lay

    # ── Cart panel ────────────────────────────────────────────────────────────

    def _build_cart_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("cartPanel")
        panel.setFixedWidth(300)
        panel.setStyleSheet(
            f"QWidget#cartPanel {{ background:{BG_SURFACE}; border:1px solid {BORDER}; border-radius:10px; }}"
        )

        lay = QVBoxLayout(panel)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)

        # Header
        hdr = QHBoxLayout()
        hdr.addWidget(make_label("Current Order", 14, bold=True))
        hdr.addStretch()
        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("btnOutline")
        clear_btn.clicked.connect(self._clear_cart)
        hdr.addWidget(clear_btn)
        lay.addLayout(hdr)

        # Cart items
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

        self.subtotal_lbl = make_label("Subtotal: Rp0", 12, color=TEXT_SECONDARY)
        self.tax_lbl      = make_label("Tax (10%): Rp0", 12, color=TEXT_SECONDARY)
        lay.addWidget(self.subtotal_lbl)
        lay.addWidget(self.tax_lbl)

        lay.addWidget(h_line())

        self.total_lbl = make_label("Total: Rp0", 16, bold=True)
        lay.addWidget(self.total_lbl)

        # ── Checkout button with explicit style so it's never invisible ───────
        self.checkout_btn = QPushButton("🛒  Checkout")
        self.checkout_btn.setFixedHeight(44)
        self.checkout_btn.setStyleSheet(
            f"QPushButton {{ background:{PRIMARY}; color:#ffffff; border:none;"
            f" border-radius:8px; padding:10px 16px; font-size:14px; font-weight:700;}}"
            f"QPushButton:hover   {{ background:{PRIMARY_HOVER}; }}"
            f"QPushButton:pressed {{ background:{PRIMARY_ACTIVE}; }}"
        )
        self.checkout_btn.clicked.connect(self._checkout)
        lay.addWidget(self.checkout_btn)

        return panel

    # ── Grid refresh ──────────────────────────────────────────────────────────

    def _filtered_products(self) -> list[dict]:
        q = self.search.text().lower()

        # ambil produk dari SQLite
        rows = backend.ProductRepository.get_all()

        prods = []

        for row in rows:
            p = dict(row)

            # mapping field database -> field UI
            p["id"] = str(p["id"])
            p["name"] = p.get("product_name", "")
            p.setdefault("image", "📦")
            p.setdefault("low", 5)
            p.setdefault("sku", p["id"])
            p.setdefault("category", "General")

            if "pricing" not in p:
                p["pricing"] = [{
                    "unit": "piece",
                    "price": p.get("sell_price", 0),
                    "qty": 1
                }]

            prods.append(p)

        if not q:
            return prods

        return [
            p for p in prods
            if q in p["name"].lower()
            or q in p["sku"].lower()
            or q in p["category"].lower()
            or q in p.get("brand", "").lower()
        ]

    # TODO Rename this here and in `_filtered_products`
    def _extracted_from__filtered_products_7(self, prod_id, p, prods):
        p["id"] = prod_id
        p.setdefault("image", "📦")
        p.setdefault("low", 5)
        p.setdefault("sku", prod_id)
        p.setdefault("category", "General")
        if "pricing" not in p:
            p["pricing"] = [{"unit": "piece", "price": p.get("sell_price", 0), "qty": 1}]
        prods.append(p)

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

        for col in range(cols):
            self.grid_layout.setColumnStretch(col, 1)

    def _product_card(self, p: dict) -> QWidget:
        w = QWidget()
        w.setObjectName("productCard")
        w.setStyleSheet(
            "QWidget#productCard { "
            f"background:{BG_SURFACE}; border:1px solid {BORDER}; border-radius:10px; }}"
        )
        w.setMaximumHeight(280)
        w.setMaximumWidth(260)
        w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        v = QVBoxLayout(w)
        v.setContentsMargins(14, 14, 14, 14)
        v.setSpacing(6)

        # Icon + stock badge
        top = QHBoxLayout()
        image_text = str(p.get("image", "")).strip()
        if not image_text or all(ord(ch) < 128 for ch in image_text) or len(image_text) > 2:
            image_text = p["name"][:1].upper()

        icon_label = QLabel(image_text)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setFixedSize(36, 36)
        icon_label.setStyleSheet(
            "background:#e2e8f0; color:#0f172a; border-radius:18px;"
            " font-size:16px; font-weight:700;"
        )
        top.addWidget(icon_label)
        top.addStretch()
        is_low = p["stock"] < p["low"]
        stock_lbl = QLabel(str(p["stock"]))
        stock_lbl.setStyleSheet(stock_badge_style(is_low))
        top.addWidget(stock_lbl)
        v.addLayout(top)

        v.addWidget(make_label(p["name"], 12, bold=True))
        meta_text = p.get("brand") or p.get("category", "")
        if meta_text:
            v.addWidget(make_label(meta_text, 11, color=TEXT_SECONDARY))
        v.addWidget(make_label(p["sku"], 10, color="#94a3b8"))

        # Unit selector
        pid = p["id"]
        unit_combo = QComboBox()
        for pricing in p["pricing"]:
            u, pr, qty = pricing["unit"], pricing["price"], pricing["qty"]
            if u == "piece":
                label = f"Per Piece – Rp{pr:.0f}"
            elif u == "pack":
                label = f"Per Pack ({qty}) – Rp{pr:.0f}"
            else:
                label = f"Per Box ({qty}) – Rp{pr:.0f}"
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
        pricing  = next((pr for pr in p["pricing"] if pr["unit"] == cur_unit), p["pricing"][0])
        bottom.addWidget(make_label(f"Rp{pricing['price']:.0f}", 15, bold=True))
        bottom.addStretch()

        add_btn = QPushButton("+ Add")
        add_btn.setStyleSheet(
            f"QPushButton {{ background:{PRIMARY}; color:#ffffff; border:none;"
            f" border-radius:6px; padding:4px 12px; font-size:12px; font-weight:600;}}"
            f"QPushButton:hover   {{ background:{PRIMARY_HOVER}; }}"
            f"QPushButton:pressed {{ background:{PRIMARY_ACTIVE}; }}"
        )
        add_btn.clicked.connect(lambda _, p=p, cb=unit_combo: self._add_to_cart(p, cb))
        bottom.addWidget(add_btn)
        v.addLayout(bottom)

        return w

    # ── Cart refresh ──────────────────────────────────────────────────────────

    def _refresh_cart(self) -> None:
        while self.cart_lay.count() > 1:
            item = self.cart_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for item in self._cart:
            item.setdefault("image", item.get("product_name", "?")[:1].upper())
            item.setdefault("productName", item.get("product_name", item.get("name", "Unknown")))
            item.setdefault("unit", "piece")
            item.setdefault("productId", item.get("product_id"))
            self.cart_lay.insertWidget(self.cart_lay.count() - 1, self._cart_row(item))

        subtotal = sum(i["subtotal"] for i in self._cart)
        tax      = subtotal * 0.1
        total    = subtotal + tax

        self.subtotal_lbl.setText(f"Subtotal: Rp{subtotal:,.0f}")
        self.tax_lbl.setText(f"Tax (10%): Rp{tax:,.0f}")
        self.total_lbl.setText(f"Total: Rp{total:,.0f}")

        # Gray out checkout when empty
        has_items = bool(self._cart)
        self.checkout_btn.setEnabled(has_items)
        self.checkout_btn.setStyleSheet(
            f"QPushButton {{ background:{ PRIMARY if has_items else '#c7d2fe'};"
            f" color:#ffffff; border:none; border-radius:8px;"
            f" padding:10px 16px; font-size:14px; font-weight:700;}}"
            f"QPushButton:hover   {{ background:{ PRIMARY_HOVER if has_items else '#c7d2fe'}; }}"
            f"QPushButton:pressed {{ background:{PRIMARY_ACTIVE}; }}"
        )

    def _cart_row(self, item: dict) -> QWidget:
        w = QWidget()
        w.setObjectName("cartRow")
        w.setStyleSheet(
            f"QWidget#cartRow {{ background:{BG_APP}; border:1px solid {BORDER}; border-radius:8px; }}"
        )
        h = QHBoxLayout(w)
        h.setContentsMargins(10, 8, 10, 8)
        h.setSpacing(8)

        h.addWidget(make_label(item["image"], 18))

        info = QVBoxLayout()
        info.addWidget(make_label(item["productName"], 11, bold=True))
        info.addWidget(make_label(f"Rp{item['price']:.0f} / {item['unit']}", 10, color=TEXT_SECONDARY))
        h.addLayout(info)
        h.addStretch()

        # Qty controls
        ctrl = QVBoxLayout()
        qty_row = QHBoxLayout()

        minus_btn = QPushButton("−")
        minus_btn.setFixedSize(24, 24)
        minus_btn.setStyleSheet(
            "QPushButton { background:#f1f5f9; border:1px solid #e2e8f0;"
            " border-radius:6px; color:#0f172a; font-size:14px; font-weight:700;}"
            "QPushButton:hover { background:#e2e8f0; }"
        )
        minus_btn.clicked.connect(lambda _, i=item: self._change_qty(i, -1))
        qty_row.addWidget(minus_btn)

        qty_lbl = QLabel(str(item["qty"]))
        qty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qty_lbl.setFixedWidth(24)
        qty_lbl.setStyleSheet(f"color:{TEXT_PRIMARY}; font-weight:600;")
        qty_row.addWidget(qty_lbl)

        plus_btn = QPushButton("+")
        plus_btn.setFixedSize(24, 24)
        plus_btn.setStyleSheet(
            "QPushButton { background:#4f46e5; border:none;"
            " border-radius:6px; color:#ffffff; font-size:14px; font-weight:700;}"
            "QPushButton:hover { background:#4338ca; }"
        )
        plus_btn.clicked.connect(lambda _, i=item: self._change_qty(i, +1))
        qty_row.addWidget(plus_btn)

        ctrl.addLayout(qty_row)

        line_total = make_label(f"Rp{item['price'] * item['qty']:.0f}", 11, bold=True, color=PRIMARY)
        line_total.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ctrl.addWidget(line_total)
        h.addLayout(ctrl)

        rm = QPushButton("🗑")
        rm.setFixedSize(24, 24)
        rm.setStyleSheet(
            "QPushButton { background:transparent; border:none;"
            " color:#64748b; font-size:14px;}"
            "QPushButton:hover { color:#ef4444; background:transparent; }"
        )
        rm.clicked.connect(lambda _, i=item: self._remove(i))
        h.addWidget(rm)

        return w

    # ── Actions ───────────────────────────────────────────────────────────────

    def _add_to_cart(self, p: dict, unit_combo: QComboBox) -> None:
        unit    = unit_combo.currentData()
        pricing = next((pr for pr in p["pricing"] if pr["unit"] == unit), p["pricing"][0])
        price   = pricing["price"]
        qty     = pricing["qty"]

        # Cek stok dari SQLite
        db_row = ProductRepository.get_by_id(p["id"])
        if not db_row or dict(db_row)["stock"] < qty:
            self.status_msg.emit(f"⚠ Stok {p['name']} tidak cukup!")
            return

        # Update qty jika sudah ada di cart
        for c in self._cart:
            if c["product_id"] == p["id"] and c["unit"] == unit:
                new_qty = c["qty"] + qty
                if dict(db_row)["stock"] < new_qty:
                    self.status_msg.emit(f"⚠ Stok {p['name']} tidak cukup!")
                    return
                c["qty"]     = new_qty
                c["subtotal"] = price * new_qty
                self._refresh_cart()
                self.status_msg.emit(f"{p['name']} ({unit}) diperbarui")
                return

        # Item baru
        self._cart.append({
            "product_id":   p["id"],
            "product_name": p["name"],
            "name":         p["name"],
            "price":        price,
            "qty":          qty,
            "unit":         unit,
            "subtotal":     price * qty,
            "image":        p.get("image", p["name"][:1].upper()),
        })
        self._refresh_cart()
        self.status_msg.emit(f"{p['name']} ({unit}) ditambahkan ke keranjang")

    def _change_qty(self, item: dict, delta: int) -> None:
        for c in self._cart:
            if c["product_id"] == item["productId"]:
                new_qty = c["qty"] + delta
                if new_qty > 0:
                    c["qty"]     = new_qty
                    c["subtotal"] = c["price"] * new_qty
                else:
                    self._remove(item)
                    break
                # Validasi stok: cek ketersediaan sebelum menaikkan qty
                if delta > 0:
                    db_products = backend.load_json(backend.FILE_BARANG)
                    prod = db_products.get(c_item["product_id"], {})
                    stok_tersedia = prod.get("stock", 0)
                    if new_qty > stok_tersedia:
                        self.status_msg.emit(
                            f"Stok {c_item['name']} tidak cukup! (Tersedia: {stok_tersedia})"
                        )
                        break
                c_item["qty"] = new_qty
                c_item["subtotal"] = c_item["price"] * new_qty
                break
        self._refresh_cart()

    def _remove(self, item: dict) -> None:
        self._cart = [c for c in self._cart if c["product_id"] != item["product_id"]]
        self._refresh_cart()

    def _clear_cart(self) -> None:
        self._cart.clear()
        self._refresh_cart()

    def _checkout(self) -> None:
        if not self._cart:
            QMessageBox.information(self, "Keranjang Kosong", "Tambahkan produk sebelum checkout.")
            return

        subtotal = sum(i["subtotal"] for i in self._cart)
        tax      = subtotal * 0.1
        total    = subtotal + tax

        dlg = PaymentDialog(subtotal, tax, total, auth_token=self._auth_token, parent=self)
        if not dlg.exec():
            return

        is_member = bool(dlg.member_id)

        # ── Simpan transaksi ke SQLite via kasir.create_transaction ──────────
        trx_id = backend.create_transaction(
            customer_name  = dlg.member_name,
            payment_method = dlg.payment_method,
            is_member      = is_member,
            user_id        = getattr(self, 'user_id', 1),
            items          = self._cart,
            amount_paid    = total,
        )

        # ── Award loyalty points if member ────────────────────────────────────
        if is_member and dlg.member_id:
            try:
                from controllers import loyalty_controller
                result = loyalty_controller.add_points_from_transaction(
                    auth_token   = self._auth_token,
                    member_id    = dlg.member_id,
                    total_belanja = subtotal,
                )
                pts  = result.get("poin_tambahan", 0)
                tier = result.get("tier_terkini", "")
                self.status_msg.emit(
                    f"✅ Transaksi #{trx_id} selesai — {dlg.member_name} mendapat +{pts} poin! Tier: {tier}"
                )
            except Exception as e:
                self.status_msg.emit(
                    f"✅ Transaksi #{trx_id} selesai (gagal tambah poin: {e})"
                )
        else:
            self.status_msg.emit(f"✅ Transaksi #{trx_id} selesai")

        self.transaction_completed.emit()
        self._clear_cart()
        self._refresh_grid()