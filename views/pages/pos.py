# ─────────────────────────────────────────────────────────────────────────────
# views/pages/pos.py
# ─────────────────────────────────────────────────────────────────────────────

import random
import re
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QScrollArea, QGridLayout, QComboBox, QDialog,
    QDialogButtonBox, QFormLayout, QMessageBox, QSizePolicy, QSpinBox,
)
from PyQt6.QtCore import Qt, pyqtSignal

from views.styles.theme_manager import make_label, h_line, stock_badge_style
from views.styles.palettes import PRIMARY, BG_SURFACE, BORDER, BG_APP
from database import (
    ProductRepository, TransactionRepository,
    TransactionItemRepository, MemberRepository,
)
from models import loyalty_model


# ─────────────────────────────── Member Check Dialog ────────────────────────────

class MemberCheckDialog(QDialog):
    """
    Dialog pertama sebelum payment — cek apakah pembeli adalah member.
    Jika member ditemukan, tampilkan info tier & poin, dan opsi redeem poin.
    """

    def __init__(self, subtotal: float, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Cek Member")
        self.setFixedWidth(440)
        self.setModal(True)

        self.subtotal       = subtotal
        self.member_data    : dict  = {}      # Diisi jika member ditemukan
        self.points_to_use  : int   = 0       # Poin yang ingin ditukar
        self.discount_amount: float = 0.0     # Nilai diskon dalam Rp

        lay = QVBoxLayout(self)
        lay.setSpacing(14)
        lay.setContentsMargins(24, 24, 24, 24)

        # ── Header ──
        lay.addWidget(make_label("Cek Keanggotaan", 16, bold=True))
        lay.addWidget(make_label("Masukkan No. HP atau Email pelanggan", 12, color="#64748b"))
        lay.addWidget(h_line())

        # ── Search row ──
        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("No. HP / Email member…")
        self.search_input.returnPressed.connect(self._lookup)
        search_row.addWidget(self.search_input)

        search_btn = QPushButton("Cari")
        search_btn.setFixedWidth(70)
        search_btn.setStyleSheet(
            f"QPushButton {{ background:{PRIMARY}; color:#fff; border:none;"
            f" border-radius:6px; padding:6px 12px; font-weight:600; }}"
            f"QPushButton:hover {{ background:#4338ca; }}"
        )
        search_btn.clicked.connect(self._lookup)
        search_row.addWidget(search_btn)
        lay.addLayout(search_row)

        # ── Member info card (hidden until found) ──
        self.info_card = QWidget()
        self.info_card.setObjectName("memberCard")
        self.info_card.setStyleSheet(
            "QWidget#memberCard { background:#f0fdf4; border:1px solid #86efac;"
            " border-radius:10px; }"
        )
        self.info_card.hide()
        card_lay = QVBoxLayout(self.info_card)
        card_lay.setContentsMargins(14, 12, 14, 12)
        card_lay.setSpacing(8)

        # Name + tier badge row
        name_row = QHBoxLayout()
        self.lbl_name  = make_label("", 13, bold=True)
        self.lbl_tier  = QLabel("")
        self.lbl_tier.setFixedHeight(22)
        self.lbl_tier.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_row.addWidget(self.lbl_name)
        name_row.addStretch()
        name_row.addWidget(self.lbl_tier)
        card_lay.addLayout(name_row)

        # Stats row
        stats_row = QHBoxLayout()
        self.lbl_points = make_label("", 12, color="#15803d")
        self.lbl_spent  = make_label("", 11, color="#64748b")
        stats_row.addWidget(self.lbl_points)
        stats_row.addStretch()
        stats_row.addWidget(self.lbl_spent)
        card_lay.addLayout(stats_row)

        card_lay.addWidget(h_line())

        # Redeem section
        redeem_hdr = QHBoxLayout()
        redeem_hdr.addWidget(make_label("Tukar Poin untuk Diskon", 12, bold=True))
        self.lbl_max_redeem = make_label("", 11, color="#64748b")
        redeem_hdr.addStretch()
        redeem_hdr.addWidget(self.lbl_max_redeem)
        card_lay.addLayout(redeem_hdr)

        redeem_row = QHBoxLayout()
        self.spin_points = QSpinBox()
        self.spin_points.setMinimum(0)
        self.spin_points.setMaximum(0)
        self.spin_points.setSuffix(" poin")
        self.spin_points.setFixedWidth(130)
        self.spin_points.valueChanged.connect(self._on_points_changed)
        redeem_row.addWidget(self.spin_points)
        redeem_row.addStretch()
        self.lbl_discount_val = make_label("Diskon: Rp0", 12, bold=True, color="#15803d")
        redeem_row.addWidget(self.lbl_discount_val)
        card_lay.addLayout(redeem_row)

        lay.addWidget(self.info_card)

        # ── Error label ──
        self.lbl_error = make_label("", 11, color="#ef4444")
        self.lbl_error.hide()
        lay.addWidget(self.lbl_error)

        lay.addWidget(h_line())

        # ── Buttons ──
        btn_row = QHBoxLayout()
        self.skip_btn = QPushButton("Lewati (Bukan Member)")
        self.skip_btn.setStyleSheet(
            f"QPushButton {{ background:transparent; color:#64748b;"
            f" border:1px solid {BORDER}; border-radius:6px; padding:8px 16px; }}"
            f"QPushButton:hover {{ background:#f1f5f9; }}"
        )
        self.skip_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.skip_btn)

        btn_row.addStretch()

        self.confirm_btn = QPushButton("Lanjut ke Pembayaran →")
        self.confirm_btn.setStyleSheet(
            f"QPushButton {{ background:{PRIMARY}; color:#fff; border:none;"
            f" border-radius:6px; padding:8px 20px; font-weight:600; }}"
            f"QPushButton:hover {{ background:#4338ca; }}"
        )
        self.confirm_btn.clicked.connect(self.accept)
        btn_row.addWidget(self.confirm_btn)
        lay.addLayout(btn_row)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _lookup(self) -> None:
        identifier = self.search_input.text().strip()
        if not identifier:
            return

        member = loyalty_model.find_member_by_contact(identifier)
        if not member:
            self._show_error("Pelanggan tidak ditemukan sebagai member.")
            self.info_card.hide()
            self.member_data = {}
            return

        self.lbl_error.hide()
        self.member_data = member
        self._populate_card(member)
        self.info_card.show()
        self.adjustSize()

    def _populate_card(self, m: dict) -> None:
        self.lbl_name.setText(f"👤 {m['name']}")

        tier_colors = {
            "Bronze":   ("#92400e", "#fef3c7"),
            "Silver":   ("#475569", "#f1f5f9"),
            "Gold":     ("#854d0e", "#fef9c3"),
            "Platinum": ("#1e3a5f", "#dbeafe"),
        }
        fg, bg = tier_colors.get(m["tier"], ("#0f172a", "#f8fafc"))
        self.lbl_tier.setText(f"  {m['tier']}  ")
        self.lbl_tier.setStyleSheet(
            f"color:{fg}; background:{bg}; border-radius:10px;"
            f" font-size:11px; font-weight:700; padding:2px 6px;"
        )

        self.lbl_points.setText(f"⭐ {m['points']:,} poin dimiliki")
        self.lbl_spent.setText(f"Total belanja: Rp{m['spent']:,.0f}")

        limit = loyalty_model.calculate_max_redeem(self.subtotal, m["points"])
        max_pts = limit["max_points_usable"]
        self.lbl_max_redeem.setText(
            f"Maks: {max_pts} poin (Rp{limit['max_discount_value']:,.0f})"
        )
        self.spin_points.setMaximum(max_pts)
        self.spin_points.setValue(0)
        self.lbl_discount_val.setText("Diskon: Rp0")

    def _on_points_changed(self, val: int) -> None:
        if not self.member_data:
            return
        result = loyalty_model.apply_point_discount(
            self.subtotal, val, self.member_data["points"]
        )
        if result["valid"]:
            self.points_to_use   = result["points_used"]
            self.discount_amount = result["discount_amount"]
            self.lbl_discount_val.setText(f"Diskon: Rp{result['discount_amount']:,.0f}")
            self.lbl_error.hide()
        else:
            self._show_error(result["error"])

    def _show_error(self, msg: str) -> None:
        self.lbl_error.setText(f"⚠ {msg}")
        self.lbl_error.show()


# ─────────────────────────────── Payment Dialog ───────────────────────────────

class PaymentDialog(QDialog):
    """Modal dialog — pilih metode bayar, tampilkan ringkasan termasuk diskon member."""

    def __init__(
        self,
        subtotal: float,
        tax: float,
        total: float,
        member_data: dict = None,
        discount_amount: float = 0.0,
        points_to_use: int = 0,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Selesaikan Pembayaran")
        self.setFixedWidth(440)
        self.setModal(True)
        self.payment_method: str = "card"

        # Hitung ulang total final setelah diskon poin
        final_subtotal = subtotal - discount_amount
        final_total    = final_subtotal + tax

        lay = QVBoxLayout(self)
        lay.setSpacing(14)
        lay.setContentsMargins(24, 24, 24, 24)

        lay.addWidget(make_label("Selesaikan Pembayaran", 16, bold=True))
        lay.addWidget(h_line())

        # ── Member banner (jika ada) ──
        if member_data:
            banner = QWidget()
            banner.setObjectName("memberBanner")
            banner.setStyleSheet(
                "QWidget#memberBanner { background:#eff6ff; border:1px solid #93c5fd;"
                " border-radius:8px; }"
            )
            b_lay = QHBoxLayout(banner)
            b_lay.setContentsMargins(12, 8, 12, 8)
            points_earned = loyalty_model.calculate_points_earned(final_subtotal + tax)
            b_lay.addWidget(make_label(
                f"👤 {member_data['name']}  ·  {member_data['tier']}",
                11, bold=True, color="#1d4ed8"
            ))
            b_lay.addStretch()
            b_lay.addWidget(make_label(
                f"+{points_earned} poin setelah bayar", 11, color="#1d4ed8"
            ))
            lay.addWidget(banner)

        lay.addWidget(make_label("Metode Pembayaran", 12, color="#64748b"))

        # ── Method buttons ──
        methods_row = QHBoxLayout()
        self._pay_btns: dict[str, QPushButton] = {}
        for method, label in [("card", "💳\nKartu"), ("cash", "💵\nTunai"), ("mobile", "📱\nMobile")]:
            btn = QPushButton(label)
            btn.setFixedHeight(70)
            btn.clicked.connect(lambda _, m=method: self._set_method(m))
            self._pay_btns[method] = btn
            methods_row.addWidget(btn)
        lay.addLayout(methods_row)
        self._set_method("card")

        lay.addWidget(h_line())

        # ── Ringkasan harga ──
        form = QFormLayout()
        form.setVerticalSpacing(6)
        form.addRow(
            make_label("Subtotal", 12, color="#64748b"),
            make_label(f"Rp{subtotal:,.0f}", 12),
        )
        if discount_amount > 0:
            form.addRow(
                make_label(f"Diskon Poin ({points_to_use} poin)", 12, color="#15803d"),
                make_label(f"- Rp{discount_amount:,.0f}", 12, color="#15803d"),
            )
            form.addRow(
                make_label("Subtotal Akhir", 12, color="#64748b"),
                make_label(f"Rp{final_subtotal:,.0f}", 12),
            )
        form.addRow(
            make_label("Pajak (10%)", 12, color="#64748b"),
            make_label(f"Rp{tax:,.0f}", 12),
        )
        lay.addLayout(form)

        lay.addWidget(h_line())

        total_row = QHBoxLayout()
        total_row.addWidget(make_label("Total", 16, bold=True))
        total_row.addStretch()
        total_row.addWidget(make_label(f"Rp{final_total:,.0f}", 18, bold=True, color=PRIMARY))
        lay.addLayout(total_row)

        # Simpan final_total agar bisa diambil oleh caller
        self.final_total = final_total

        lay.addWidget(h_line())

        btns = QHBoxLayout()
        cancel_btn = QPushButton("Batal")
        cancel_btn.setStyleSheet(
            f"QPushButton {{ background:transparent; color:#64748b;"
            f" border:1px solid {BORDER}; border-radius:6px; padding:8px 20px; }}"
            f"QPushButton:hover {{ background:#f1f5f9; }}"
        )
        cancel_btn.clicked.connect(self.reject)

        pay_btn = QPushButton("✓  Bayar Sekarang")
        pay_btn.setStyleSheet(
            f"QPushButton {{ background:{PRIMARY}; color:#fff; border:none;"
            f" border-radius:6px; padding:8px 24px; font-weight:700; font-size:13px; }}"
            f"QPushButton:hover {{ background:#4338ca; }}"
        )
        pay_btn.clicked.connect(self.accept)

        btns.addWidget(cancel_btn)
        btns.addStretch()
        btns.addWidget(pay_btn)
        lay.addLayout(btns)

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
                    f"background:transparent; color:#0f172a; border-radius:10px;"
                    f" padding:12px 8px; font-size:13px; border:1px solid {BORDER};"
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
    transaction_completed = pyqtSignal()

    def __init__(self, header_ref, parent=None) -> None:
        super().__init__(parent)
        self.header_ref = header_ref
        self._unit_selections: dict[str, str] = {}

        # Keranjang belanja disimpan di memori (list of dict), bukan JSON/file
        self._cart: list[dict] = []

        root = QHBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(0, 0, 0, 0)

        root.addLayout(self._build_product_panel(), stretch=2)

        # Cart harus fixed/sticky — bungkus dalam QScrollArea agar tidak ikut scroll product
        cart_scroll_wrapper = QScrollArea()
        cart_scroll_wrapper.setWidgetResizable(True)
        cart_scroll_wrapper.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        cart_scroll_wrapper.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        cart_scroll_wrapper.setFrameShape(cart_scroll_wrapper.Shape.NoFrame)
        cart_scroll_wrapper.setFixedWidth(316)
        cart_scroll_wrapper.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        cart_scroll_wrapper.setWidget(self._build_cart_panel())
        root.addWidget(cart_scroll_wrapper, stretch=0)

        self._refresh_grid()
        self._refresh_cart()

    def refresh_products(self) -> None:
        """Refresh the product grid when inventory or category data changes."""
        self._refresh_grid()

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
        panel.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        panel.setStyleSheet(
            f"QWidget#cartPanel {{ background:{BG_SURFACE}; border:1px solid {BORDER}; border-radius:10px; }}"
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
        self.cart_scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.cart_scroll.setFrameShape(self.cart_scroll.Shape.NoFrame)
        self.cart_inner = QWidget()
        self.cart_lay = QVBoxLayout(self.cart_inner)
        self.cart_lay.setSpacing(8)
        self.cart_lay.addStretch()
        self.cart_scroll.setWidget(self.cart_inner)
        lay.addWidget(self.cart_scroll)

        lay.addWidget(h_line())

        self.subtotal_lbl = make_label("Subtotal: Rp0", 12, color="#64748b")
        self.tax_lbl = make_label("Tax (10%): Rp0", 12, color="#64748b")
        lay.addWidget(self.subtotal_lbl)
        lay.addWidget(self.tax_lbl)
        lay.addWidget(h_line())

        self.total_lbl = make_label("Total: Rp0", 16, bold=True)
        lay.addWidget(self.total_lbl)

        self.checkout_btn = QPushButton("Checkout")
        self.checkout_btn.clicked.connect(self._checkout)
        lay.addWidget(self.checkout_btn)

        return panel

    # ── Grid refresh ─────────────────────────────────────────────────────────

    def _filtered_products(self) -> list[dict]:
        """Ambil produk dari SQLite, normalisasi ke dict UI."""
        q = self.search.text().lower().strip()
        rows = ProductRepository.get_all()

        prods = []
        for row in rows:
            p = self._row_to_product(row)
            prods.append(p)

        if not q:
            return prods

        return [
            p for p in prods
            if q in p["name"].lower()
            or q in p["sku"].lower()
            or q in p["category"].lower()
        ]

    @staticmethod
    def _row_to_product(row) -> dict:
        """Konversi sqlite3.Row produk → dict yang dipakai UI."""
        d = dict(row)
        return {
            "id":       d["id"],
            "name":     d["product_name"],
            "sku":      f"SKU-{d['id']}",
            "category": d.get("category", "Umum"),
            "stock":    d.get("stock", 0),
            "low":      10,                         # threshold stok rendah
            "image":    d["product_name"][:1].upper(),
            "pricing":  [
                {
                    "unit":  "piece",
                    "price": d.get("sell_price", 0),
                    "qty":   1,
                }
            ],
        }

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
        w.setStyleSheet(
            f"background:{BG_SURFACE}; border:1px solid {BORDER}; border-radius:10px;"
        )

        w.setMinimumHeight(280)
        w.setMinimumWidth(260)
        w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        v = QVBoxLayout(w)
        v.setContentsMargins(14, 14, 14, 14)
        v.setSpacing(6)

        # Product icon + stock badge
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
        if meta_text := p.get("brand") or p.get("category", ""):
            v.addWidget(make_label(meta_text, 11, color="#64748b"))
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
        pricing = next((pr for pr in p["pricing"] if pr["unit"] == cur_unit), p["pricing"][0])
        bottom.addWidget(make_label(f"Rp{pricing['price']:.0f}", 15, bold=True))
        bottom.addStretch()
        add_btn = QPushButton("+ Add")
        add_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background: {PRIMARY}; color: #ffffff;"
            f"  border: none; border-radius: 6px;"
            f"  padding: 5px 14px; font-size: 12px; font-weight: 600;"
            f"}}"
            f"QPushButton:hover {{ background: #4338ca; }}"
        )
        add_btn.clicked.connect(lambda _, p=p, cb=unit_combo: self._add_to_cart(p, cb))
        bottom.addWidget(add_btn)
        v.addLayout(bottom)

        return w

    # ── Cart refresh ─────────────────────────────────────────────────────────

    def _refresh_cart(self) -> None:
        # Hapus semua widget kecuali trailing stretch
        while self.cart_lay.count() > 1:
            item = self.cart_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for item in self._cart:
            item.setdefault("image", item.get("product_name", "?")[:1].upper())
            item.setdefault("productName", item.get("product_name", "Unknown"))
            item.setdefault("unit", "piece")
            item.setdefault("productId", item.get("product_id"))
            self.cart_lay.insertWidget(self.cart_lay.count() - 1, self._cart_row(item))

        subtotal = sum(i["subtotal"] for i in self._cart)
        tax      = subtotal * 0.1
        total    = subtotal + tax

        self.subtotal_lbl.setText(f"Subtotal: Rp{subtotal:,.0f}")
        self.tax_lbl.setText(f"Tax (10%): Rp{tax:,.0f}")
        self.total_lbl.setText(f"Total: Rp{total:,.0f}")

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
        info.addWidget(make_label(f"Rp{item['price']:.0f} / {item['unit']}", 10, color="#64748b"))
        h.addLayout(info)
        h.addStretch()

        # Qty controls
        ctrl = QVBoxLayout()
        qty_row = QHBoxLayout()
        qty_row.setSpacing(4)

        minus_btn = self._extracted_from__cart_row_24(
            "−",
            26,
            "QPushButton {"
            "  background: #fee2e2; color: #ef4444;"
            "  border: 1px solid #fca5a5; border-radius: 6px;"
            "  font-size: 15px; font-weight: 700;"
            "}"
            "QPushButton:hover { background: #fecaca; }",
        )
        minus_btn.clicked.connect(lambda _, i=item: self._change_qty(i, -1))

        qty_lbl = QLabel(str(item["qty"]))
        qty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qty_lbl.setFixedWidth(24)
        qty_lbl.setStyleSheet("font-size:12px; font-weight:600; color:#0f172a; background:transparent; border:none;")

        plus_btn = QPushButton("+")
        plus_btn.setFixedSize(26, 26)
        plus_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background: {PRIMARY}; color: #ffffff;"
            f"  border: none; border-radius: 6px;"
            f"  font-size: 15px; font-weight: 700;"
            f"}}"
            f"QPushButton:hover {{ background: #4338ca; }}"
        )
        plus_btn.clicked.connect(lambda _, i=item: self._change_qty(i, 1))

        qty_row.addWidget(minus_btn)
        qty_row.addWidget(qty_lbl)
        qty_row.addWidget(plus_btn)
        ctrl.addLayout(qty_row)

        line_total = make_label(f"Rp{item['price'] * item['qty']:.0f}", 11, bold=True, color=PRIMARY)
        line_total.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ctrl.addWidget(line_total)
        h.addLayout(ctrl)

        rm = self._extracted_from__cart_row_24(
            "🗑",
            28,
            "QPushButton {"
            "  background: transparent; color: #94a3b8;"
            "  border: none; border-radius: 6px; font-size: 14px;"
            "}"
            "QPushButton:hover { background: #fee2e2; color: #ef4444; }",
        )
        rm.clicked.connect(lambda _, i=item: self._remove(i))
        h.addWidget(rm)

        return w

    # TODO Rename this here and in `_cart_row`
    def _extracted_from__cart_row_24(self, arg0, arg1, arg2):
        result = QPushButton(arg0)
        result.setFixedSize(arg1, arg1)
        result.setStyleSheet(arg2)
        return result

    # ── Actions ───────────────────────────────────────────────────────────────

    def _add_to_cart(self, p: dict, unit_combo: QComboBox) -> None:
        unit     = unit_combo.currentData()
        pricing  = next((pr for pr in p["pricing"] if pr["unit"] == unit), p["pricing"][0])
        price    = pricing["price"]
        qty_mult = pricing["qty"]

        # Cek stok dari DB sebelum tambah
        db_row = ProductRepository.get_by_id(p["id"])
        if not db_row or db_row["stock"] < qty_mult:
            self.status_msg.emit(f"Stok {p['name']} tidak cukup!")
            return

        # Cek apakah sudah ada di cart
        for item in self._cart:
            if item["product_id"] == p["id"] and item["unit"] == unit:
                total_qty = item["qty"] + qty_mult
                if db_row["stock"] < total_qty:
                    self.status_msg.emit(f"Stok {p['name']} tidak cukup!")
                    return
                item["qty"]      = total_qty
                item["subtotal"] = price * total_qty
                self._refresh_cart()
                self.status_msg.emit(f"{p['name']} ({unit}) diperbarui di keranjang")
                return

        # Item baru
        self._cart.append({
            "product_id":  p["id"],
            "product_name": p["name"],
            "productName": p["name"],
            "productId":   p["id"],
            "name":        p["name"],
            "price":       price,
            "qty":         qty_mult,
            "unit":        unit,
            "subtotal":    price * qty_mult,
            "image":       p["image"],
        })
        self._refresh_cart()
        self.status_msg.emit(f"{p['name']} ({unit}) ditambahkan ke keranjang")

    def _change_qty(self, item: dict, delta: int) -> None:
        for c_item in self._cart:
            if c_item["product_id"] == item["productId"]:
                new_qty = c_item["qty"] + delta
                if new_qty > 0:
                    c_item["qty"]     = new_qty
                    c_item["subtotal"] = c_item["price"] * new_qty
                else:
                    self._remove(item)
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

        # ── Step 1: Cek Member ────────────────────────────────────────────────
        member_dlg      = MemberCheckDialog(subtotal, self)
        is_member       = False
        member_data     = {}
        discount_amount = 0.0
        points_to_use   = 0

        if member_dlg.exec():
            if member_dlg.member_data:
                is_member       = True
                member_data     = member_dlg.member_data
                discount_amount = member_dlg.discount_amount
                points_to_use   = member_dlg.points_to_use

        # ── Step 2: Payment Dialog ────────────────────────────────────────────
        pay_dlg = PaymentDialog(
            subtotal        = subtotal,
            tax             = tax,
            total           = subtotal + tax,
            member_data     = member_data if is_member else None,
            discount_amount = discount_amount,
            points_to_use   = points_to_use,
            parent          = self,
        )
        if not pay_dlg.exec():
            return

        final_total = pay_dlg.final_total

        # ── Step 3: Simpan transaksi ke SQLite ───────────────────────────────
        today     = datetime.now().strftime("%Y-%m-%d")
        daily_seq = TransactionRepository.get_daily_count(today) + 1
        order_id  = f"ORD-{datetime.now().strftime('%Y%m%d')}-{daily_seq:03d}"
        order_dt  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Resolusi user_id:
        # 1. Ambil dari atribut session jika sudah di-set (login system)
        # 2. Fallback ke user pertama yang ada di DB (biasanya admin default)
        # 3. Jika DB benar-benar kosong, tampilkan error dan batalkan
        user_id = getattr(self, "user_id", None)
        if not user_id:
            from database import get_connection as _gc
            with _gc() as _conn:
                _row = _conn.execute("SELECT id FROM user ORDER BY id LIMIT 1").fetchone()
            if not _row:
                QMessageBox.critical(
                    self,
                    "Error: Tidak ada User",
                    "Tidak ada data user di database.\n"
                    "Silakan tambahkan user terlebih dahulu melalui menu Settings.",
                )
                return
            user_id = _row["id"]

        trx_id = TransactionRepository.tambah({
            "order_id":       order_id,
            "order_date":     order_dt,
            "customer_name":  member_data.get("name", "Pelanggan Umum") if is_member else "Pelanggan Umum",
            "user_id":        user_id,
            "total":          final_total,
            "changes":        0.0,
            "payment_method": pay_dlg.payment_method,
            "is_member":      1 if is_member else 0,
        })

        # Simpan item transaksi & kurangi stok
        trx_items = []
        for item in self._cart:
            trx_items.append({
                "product_id":   item["product_id"],
                "product_name": item["product_name"],
                "price":        item["price"],
                "quantity":     item["qty"],
                "subtotal":     item["subtotal"],
            })
            ProductRepository.update_stock(item["product_id"], item["qty"])

        TransactionItemRepository.tambah_bulk(trx_id, trx_items)

        # ── Step 4: Update poin member ────────────────────────────────────────
        if is_member and member_data:
            points_earned = loyalty_model.calculate_points_earned(final_total)
            new_tier      = loyalty_model.calculate_tier(
                member_data["spent"] + final_total
            )
            loyalty_model.update_loyalty_stats(
                member_id    = member_data["id"],
                points_added = points_earned,
                points_used  = points_to_use,
                spent_added  = final_total,
                new_tier     = new_tier,
            )
            msg = (
                f"Transaksi {order_id} selesai!  "
                f"+{points_earned} poin untuk {member_data['name']}  "
                f"(Tier: {new_tier})"
            )
            if points_to_use > 0:
                msg += f"  |  Poin ditukar: {points_to_use}"
        else:
            msg = f"Pembayaran berhasil! {order_id} selesai."

        self.status_msg.emit(msg)
        self.transaction_completed.emit()
        self._clear_cart()
        self._refresh_grid()