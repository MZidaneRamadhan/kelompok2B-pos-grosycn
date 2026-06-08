# ─────────────────────────────────────────────────────────────────────────────
# views/pages/storage.py  (updated — tambahan fitur Supplier Product)
# ─────────────────────────────────────────────────────────────────────────────

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QFormLayout, QSpinBox, QDoubleSpinBox, QComboBox,
    QTextEdit, QDialogButtonBox, QMessageBox, QSizePolicy,
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor

from views.styles.theme_manager import make_label, alert_style, card_style
from views.styles.palettes import DANGER_FG, SUCCESS_FG

from controllers.barang_controller import (
    get_all_products, get_all_categories,
    create_product, update_product, delete_product,
)
from controllers.supplier_product_controller import (
    get_suppliers_for_product,
    get_all_suppliers_with_linked_flag,
    link_supplier_to_product,
    unlink_supplier_from_product,
)

LOW_STOCK_THRESHOLD = 10


# ─────────────────────────────────────────────────────────────────────────────
# Dialog: Tambah / Edit Product  (tidak diubah)
# ─────────────────────────────────────────────────────────────────────────────

class ProductDialog(QDialog):
    """Dialog CREATE (product=None) atau UPDATE (product=dict)."""

    def __init__(self, parent=None, product: dict | None = None) -> None:
        super().__init__(parent)
        self._product = product
        is_edit = product is not None

        self.setWindowTitle("Edit Product" if is_edit else "Tambah Product")
        self.setMinimumWidth(420)

        lay = QVBoxLayout(self)
        lay.setSpacing(12)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nama produk")
        form.addRow("Nama Product:", self.name_input)

        self.category_combo = QComboBox()
        self._load_categories()
        form.addRow("Category:", self.category_combo)

        self.sell_price_input = QDoubleSpinBox()
        self.sell_price_input.setRange(0, 999_999_999)
        self.sell_price_input.setDecimals(0)
        self.sell_price_input.setPrefix("Rp ")
        form.addRow("Harga Jual:", self.sell_price_input)

        self.buy_price_input = QDoubleSpinBox()
        self.buy_price_input.setRange(0, 999_999_999)
        self.buy_price_input.setDecimals(0)
        self.buy_price_input.setPrefix("Rp ")
        form.addRow("Harga Beli:", self.buy_price_input)

        self.stock_input = QSpinBox()
        self.stock_input.setRange(0, 999_999)
        form.addRow("Stok Toko:", self.stock_input)

        self.stock_storage_input = QSpinBox()
        self.stock_storage_input.setRange(0, 999_999)
        form.addRow("Stok Gudang:", self.stock_storage_input)

        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("Deskripsi produk (opsional)")
        self.desc_input.setFixedHeight(80)
        form.addRow("Deskripsi:", self.desc_input)

        lay.addLayout(form)
        self._error_lbl = QLabel()
        self._error_lbl.setStyleSheet("color: #DC2626; font-size: 13px; font-weight: 600;")
        self._error_lbl.hide()
        lay.addWidget(self._error_lbl)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

        if is_edit:
            self._prefill(product)

    def _load_categories(self) -> None:
        self._categories = get_all_categories()
        for cat in self._categories:
            self.category_combo.addItem(cat["category"], userData=cat["id"])

    def _prefill(self, p: dict) -> None:
        self.name_input.setText(p.get("product_name", ""))
        self.sell_price_input.setValue(p.get("sell_price", 0))
        self.buy_price_input.setValue(p.get("buy_price", 0))
        self.stock_input.setValue(p.get("stock", 0))
        self.stock_storage_input.setValue(p.get("stock_storage", 0))
        self.desc_input.setPlainText(p.get("description", ""))

        cat_id = p.get("category_id")
        for i, cat in enumerate(self._categories):
            if cat["id"] == cat_id:
                self.category_combo.setCurrentIndex(i)
                break

    def _on_accept(self) -> None:
        self.sell_price_input.setStyleSheet("")
        self.buy_price_input.setStyleSheet("")
        self._error_lbl.hide()

        if not self.name_input.text().strip():
            self.name_input.setStyleSheet("border: 2px solid red; border-radius: 4px;")
            return

        if self.sell_price_input.value() <= 0:
            self.sell_price_input.setStyleSheet("border: 2px solid red; border-radius: 4px;")
            self._error_lbl.setText("⚠️ Harga jual harus lebih dari 0")
            self._error_lbl.show()
            return

        if self.sell_price_input.value() < self.buy_price_input.value():
            self.sell_price_input.setStyleSheet("border: 2px solid red; border-radius: 4px;")
            self.buy_price_input.setStyleSheet("border: 2px solid red; border-radius: 4px;")
            self._error_lbl.setText("⚠️ Harga jual tidak boleh lebih kecil dari harga beli!")
            self._error_lbl.show()
            return

        self.accept()

    def get_data(self) -> dict:
        return {
            "product_name":  self.name_input.text().strip(),
            "category_id":   self.category_combo.currentData(),
            "sell_price":    self.sell_price_input.value(),
            "buy_price":     self.buy_price_input.value(),
            "stock":         self.stock_input.value(),
            "stock_storage": self.stock_storage_input.value(),
            "description":   self.desc_input.toPlainText().strip(),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Dialog BARU: Kelola Supplier untuk satu Product
# ─────────────────────────────────────────────────────────────────────────────

class SupplierProductDialog(QDialog):
    """
    Menampilkan daftar supplier yang sudah terhubung ke satu product,
    dan memungkinkan user menambah / melepas relasi.

    Layout:
    ┌─────────────────────────────────────────────────┐
    │  Product: Indomie Goreng                        │
    ├──── Supplier terhubung ─────────────────────────┤
    │  [tabel: Nama | Rating | Alamat | Tanggal | ✕] │
    ├──── Tambah Supplier ────────────────────────────┤
    │  ComboBox (supplier belum terhubung)  [Tambah]  │
    └─────────────────────────────────────────────────┘
    """

    def __init__(self, parent=None, product: dict | None = None) -> None:
        super().__init__(parent)
        if product is None:
            raise ValueError("product harus diberikan")

        self._product = product
        self._product_id = product["id"]

        self.setWindowTitle(f"Supplier — {product['product_name']}")
        self.setMinimumSize(680, 420)

        root = QVBoxLayout(self)
        root.setSpacing(14)

        # ── Judul ─────────────────────────────────────────────────────────────
        title = make_label(f"🏷 {product['product_name']}", 14, bold=True)
        root.addWidget(title)

        # ── Tabel supplier terhubung ──────────────────────────────────────────
        root.addWidget(make_label("Supplier yang menyediakan product ini:", 11, color="#64748b"))
        self._table = self._build_linked_table()
        root.addWidget(self._table)

        # ── Tambah supplier baru ──────────────────────────────────────────────
        add_row = QHBoxLayout()
        add_row.addWidget(make_label("Tambah Supplier:", 11))

        self._supplier_combo = QComboBox()
        self._supplier_combo.setMinimumWidth(260)
        add_row.addWidget(self._supplier_combo, stretch=1)

        add_btn = QPushButton("＋ Tambah")
        add_btn.setFixedHeight(34)
        add_btn.setStyleSheet(
            "QPushButton { background-color: #16a34a; color: white; border: none;"
            " border-radius: 4px; padding: 0 14px; font-size: 12px; font-weight: 600; }"
            "QPushButton:hover { background-color: #15803d; }"
            "QPushButton:pressed { background-color: #166534; }"
        )
        add_btn.clicked.connect(self._add_supplier)
        add_row.addWidget(add_btn)
        root.addLayout(add_row)

        # ── Tutup ─────────────────────────────────────────────────────────────
        close_btn = QPushButton("Tutup")
        close_btn.clicked.connect(self.accept)
        root.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self._refresh()

    # ── Builder ───────────────────────────────────────────────────────────────

    def _build_linked_table(self) -> QTableWidget:
        t = QTableWidget()
        t.setColumnCount(5)
        t.setHorizontalHeaderLabels(["Nama Supplier", "Rating", "Alamat", "Tanggal Terhubung", ""])
        hh = t.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)   # Nama → fleksibel
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)     # Rating → tetap
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)   # Alamat → fleksibel
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)     # Tanggal → tetap
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)     # Tombol → tetap
        t.setColumnWidth(1, 70)
        t.setColumnWidth(3, 130)
        t.setColumnWidth(4, 50)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        t.setAlternatingRowColors(True)
        t.verticalHeader().setDefaultSectionSize(44)
        t.verticalHeader().hide()   # sembunyikan nomor baris di kiri
        return t

    # ── Data refresh ──────────────────────────────────────────────────────────

    def _refresh(self) -> None:
        """Muat ulang tabel + combo setiap ada perubahan."""
        self._load_linked_table()
        self._load_combo()

    def _load_linked_table(self) -> None:
        # Reset span dulu sebelum apapun
        self._table.clearSpans()
        
        rows = get_suppliers_for_product(self._product_id)
        self._table.setRowCount(max(len(rows), 1))

        if not rows:
            self._table.setRowCount(1)
            self._table.setSpan(0, 0, 1, 5)
            placeholder = QTableWidgetItem("Belum ada supplier yang terhubung")
            placeholder.setForeground(QColor("#94a3b8"))
            placeholder.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(0, 0, placeholder)
            return  # keluar lebih awal, jangan lanjut ke loop

        for r, s in enumerate(rows):
            def cell(text):
                item = QTableWidgetItem(str(text))
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                return item

            self._table.setItem(r, 0, cell(s["supplier_name"]))

            rating_item = cell(f"⭐ {s['rating']:.1f}" if s.get("rating") else "—")
            rating_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(r, 1, rating_item)

            self._table.setItem(r, 2, cell(s.get("address") or "—"))
            self._table.setItem(r, 3, cell((s.get("supplied_date") or "")[:10]))

            del_btn = QPushButton("✕")
            del_btn.setFixedSize(32, 32)
            del_btn.setToolTip(f"Lepas {s['supplier_name']} dari product ini")
            del_btn.setStyleSheet(
                "QPushButton { background-color: #ef4444; color: white; border: none;"
                " border-radius: 4px; font-weight: bold; }"
                "QPushButton:hover { background-color: #dc2626; }"
            )
            link_id = s["link_id"]
            supplier_name = s["supplier_name"]
            del_btn.clicked.connect(
                lambda _, lid=link_id, sn=supplier_name: self._remove_supplier(lid, sn)
            )

            wrap = QWidget()
            wrap.setStyleSheet("background: transparent;")
            wl = QHBoxLayout(wrap)
            wl.setContentsMargins(8, 6, 8, 6)
            wl.addWidget(del_btn, alignment=Qt.AlignmentFlag.AlignCenter)
            self._table.setCellWidget(r, 4, wrap)

    def _load_combo(self) -> None:
        """Isi combo hanya dengan supplier yang BELUM terhubung."""
        self._supplier_combo.clear()
        self._available_suppliers = [
            s for s in get_all_suppliers_with_linked_flag(self._product_id)
            if not s["is_linked"]
        ]
        if self._available_suppliers:
            for s in self._available_suppliers:
                label = f"{s['supplier_name']}  (⭐ {s.get('rating', 0):.1f})"
                self._supplier_combo.addItem(label, userData=s["id"])
        else:
            self._supplier_combo.addItem("— Semua supplier sudah terhubung —")

    # ── Aksi ──────────────────────────────────────────────────────────────────

    def _add_supplier(self) -> None:
        supplier_id = self._supplier_combo.currentData()
        if supplier_id is None:
            QMessageBox.information(self, "Info", "Tidak ada supplier yang bisa ditambahkan.")
            return
        try:
            link_supplier_to_product(supplier_id, self._product_id)
            self._refresh()
        except ValueError as e:
            QMessageBox.warning(self, "Gagal", str(e))

    def _remove_supplier(self, link_id: int, supplier_name: str) -> None:
        confirm = QMessageBox.question(
            self,
            "Konfirmasi",
            f"Lepas '{supplier_name}' dari product ini?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                unlink_supplier_from_product(link_id)
                self._refresh()
            except ValueError as e:
                QMessageBox.warning(self, "Gagal", str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Halaman utama: Inventory / Storage  (kolom Aksi diperluas)
# ─────────────────────────────────────────────────────────────────────────────

class StoragePage(QWidget):
    """Inventory management: searchable product table with low-stock alerts."""

    status_msg = pyqtSignal(str)
    data_changed = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        lay = QVBoxLayout(self)
        lay.setSpacing(16)
        lay.setContentsMargins(0, 0, 0, 0)

        lay.addLayout(self._build_header())

        self._alert_label = QLabel()
        self._alert_label.setStyleSheet(alert_style("warning"))
        self._alert_label.hide()
        lay.addWidget(self._alert_label)

        self._stat_widgets: dict = {}
        stat_row, self._stat_widgets = self._build_stats()
        lay.addLayout(stat_row)

        lay.addLayout(self._build_controls())
        lay.addWidget(self._build_table())

        self._all_products: list[dict] = []
        self._refresh()

    # ── Builder UI ────────────────────────────────────────────────────────────

    def _build_header(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(make_label("📦 Inventory", 18, bold=True))
        row.addStretch()
        add_btn = QPushButton("＋ Tambah Product")
        add_btn.setFixedHeight(36)
        add_btn.setStyleSheet(
            "QPushButton { background-color: #2563eb; color: white; border: none;"
            " border-radius: 6px; padding: 0 16px; font-size: 13px; font-weight: 600; }"
            "QPushButton:hover { background-color: #1d4ed8; }"
        )
        add_btn.clicked.connect(self._open_create_dialog)
        row.addWidget(add_btn)
        return row

    def _build_stats(self) -> tuple[QHBoxLayout, dict]:
        row = QHBoxLayout()
        widgets: dict[str, QLabel] = {}

        for key, title in [
            ("total", "Total Products"),
            ("low",   "Low Stock"),
            ("value", "Total Stock Value"),
        ]:
            card = QWidget()
            card.setStyleSheet(card_style())
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            cv = QVBoxLayout(card)
            cv.addWidget(make_label(title, 11, color="#64748b"))
            val_lbl = make_label("–", 18, bold=True)
            cv.addWidget(val_lbl)
            widgets[key] = val_lbl
            row.addWidget(card)

        return row, widgets

    def _build_controls(self) -> QHBoxLayout:
        ctrl = QHBoxLayout()

        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  Search by name or category…")
        self.search.textChanged.connect(self._apply_filter)
        ctrl.addWidget(self.search)

        self.low_cb = QCheckBox("Low stock only")
        self.low_cb.toggled.connect(self._apply_filter)
        ctrl.addWidget(self.low_cb)

        return ctrl

    def _build_table(self) -> QTableWidget:
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "ID", "Nama Product", "Category",
            "Harga Jual", "Harga Beli",
            "Stok Toko", "Stok Gudang", "Status", "Aksi",
        ])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)
        # Kolom Aksi diperlebar: Edit + Hapus + Supplier
        self.table.setColumnWidth(8, 290)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.verticalHeader().setDefaultSectionSize(80)
        return self.table

    # ── Action widget per baris ───────────────────────────────────────────────

    def _make_action_widget(self, product: dict) -> QWidget:
        """
        Tiga tombol per baris:
          [✏ Edit]  [🏪 Supplier]  [🗑]
        """
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        hlay = QHBoxLayout(container)
        hlay.setContentsMargins(8, 10, 8, 10)
        hlay.setSpacing(8)

        # ── Edit ──────────────────────────────────────────────────────────────
        edit_btn = QPushButton("✏ Edit")
        edit_btn.setFixedHeight(36)
        edit_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        edit_btn.setStyleSheet(
            "QPushButton { background-color: #3b82f6; color: white; border: none;"
            " border-radius: 4px; padding: 0 8px; font-size: 12px; }"
            "QPushButton:hover { background-color: #2563eb; }"
            "QPushButton:pressed { background-color: #1d4ed8; }"
        )
        edit_btn.clicked.connect(lambda _, p=product: self._open_edit_dialog(p))
        hlay.addWidget(edit_btn)

        # ── Supplier ──────────────────────────────────────────────────────────
        sup_btn = QPushButton("🏪 Supplier")
        sup_btn.setFixedHeight(36)
        sup_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sup_btn.setToolTip("Lihat & kelola supplier untuk produk ini")
        sup_btn.setStyleSheet(
            "QPushButton { background-color: #7c3aed; color: white; border: none;"
            " border-radius: 4px; padding: 0 8px; font-size: 12px; }"
            "QPushButton:hover { background-color: #6d28d9; }"
            "QPushButton:pressed { background-color: #5b21b6; }"
        )
        sup_btn.clicked.connect(lambda _, p=product: self._open_supplier_dialog(p))
        hlay.addWidget(sup_btn)

        # ── Hapus ─────────────────────────────────────────────────────────────
        del_btn = QPushButton("🗑")
        del_btn.setFixedSize(36, 36)
        del_btn.setToolTip("Hapus product ini")
        del_btn.setStyleSheet(
            "QPushButton { background-color: #ef4444; color: white; border: none;"
            " border-radius: 4px; font-size: 13px; }"
            "QPushButton:hover { background-color: #dc2626; }"
            "QPushButton:pressed { background-color: #b91c1c; }"
        )
        del_btn.clicked.connect(lambda _, p=product: self._delete_product(p))
        hlay.addWidget(del_btn)

        return container

    # ── Data ──────────────────────────────────────────────────────────────────

    def _refresh(self) -> None:
        self._all_products = get_all_products()
        self._update_stats()
        self._apply_filter()

    def _update_stats(self) -> None:
        products = self._all_products
        low_count = sum(1 for p in products if p["stock"] <= LOW_STOCK_THRESHOLD)
        total_val = sum(p["sell_price"] * (p["stock"] + p["stock_storage"]) for p in products)

        self._stat_widgets["total"].setText(str(len(products)))
        self._stat_widgets["low"].setText(str(low_count))
        self._stat_widgets["value"].setText(f"Rp {total_val:,.0f}")

        if low_count:
            self._alert_label.setText(
                f"⚠️  {low_count} produk stoknya rendah – pertimbangkan untuk reorder"
            )
            self._alert_label.show()
        else:
            self._alert_label.hide()

    def _apply_filter(self) -> None:
        q = self.search.text().lower()
        low_only = self.low_cb.isChecked()

        rows = [
            p for p in self._all_products
            if (q in p["product_name"].lower() or q in (p.get("category_name") or "").lower())
            and (not low_only or p["stock"] <= LOW_STOCK_THRESHOLD)
        ]

        self.table.setRowCount(len(rows))
        for r, p in enumerate(rows):
            is_low = p["stock"] <= LOW_STOCK_THRESHOLD

            def cell(text: str) -> QTableWidgetItem:
                return QTableWidgetItem(str(text))

            self.table.setItem(r, 0, cell(p["id"]))
            self.table.setItem(r, 1, cell(p["product_name"]))
            self.table.setItem(r, 2, cell(p.get("category_name", "")))
            self.table.setItem(r, 3, cell(f"Rp {p['sell_price']:,.0f}"))
            self.table.setItem(r, 4, cell(f"Rp {p['buy_price']:,.0f}"))
            self.table.setItem(r, 5, cell(p["stock"]))
            self.table.setItem(r, 6, cell(p["stock_storage"]))

            status_item = QTableWidgetItem("⚠ Stok Rendah" if is_low else "✓ Tersedia")
            status_item.setForeground(QColor(DANGER_FG if is_low else SUCCESS_FG))
            self.table.setItem(r, 7, status_item)

            self.table.setCellWidget(r, 8, self._make_action_widget(p))

    # ── Aksi CRUD ─────────────────────────────────────────────────────────────

    def _open_create_dialog(self) -> None:
        dlg = ProductDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            new_id = create_product(**data)
            if new_id:
                self.status_msg.emit(f"Product '{data['product_name']}' berhasil ditambahkan (ID: {new_id})")
                self._refresh()
                self.data_changed.emit()
            else:
                QMessageBox.critical(self, "Error", "Gagal menambahkan product.")

    def _open_edit_dialog(self, product: dict) -> None:
        dlg = ProductDialog(self, product=product)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            ok = update_product(product_id=product["id"], **data)
            if ok:
                self.status_msg.emit(f"Product '{data['product_name']}' berhasil diperbarui.")
                self._refresh()
                self.data_changed.emit()
            else:
                QMessageBox.critical(self, "Error", "Gagal memperbarui product.")

    def _open_supplier_dialog(self, product: dict) -> None:
        """Buka SupplierProductDialog untuk product yang diklik."""
        dlg = SupplierProductDialog(self, product=product)
        dlg.exec()
        # Tidak perlu refresh StoragePage karena relasi supplier
        # tidak mengubah data product itu sendiri.

    def _delete_product(self, product: dict) -> None:
        confirm = QMessageBox.question(
            self,
            "Konfirmasi Hapus",
            f"Yakin ingin menghapus '{product['product_name']}'?\nAksi ini tidak dapat dibatalkan.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            ok = delete_product(product["id"])
            if ok:
                self.status_msg.emit(f"Product '{product['product_name']}' berhasil dihapus.")
                self._refresh()
                self.data_changed.emit()
            else:
                QMessageBox.critical(self, "Error", "Gagal menghapus product.")