# ─────────────────────────────────────────────────────────────────────────────
# views/pages/storage.py
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

# Threshold stok rendah (bisa dipindah ke config global)
LOW_STOCK_THRESHOLD = 10


# ─────────────────────────────────────────────────────────────────────────────
# Dialog: Tambah / Edit Product
# ─────────────────────────────────────────────────────────────────────────────

class ProductDialog(QDialog):
    """
    Dialog untuk CREATE (product=None) atau UPDATE (product=dict).
    Semua field divalidasi sebelum diterima.
    """

    def __init__(self, parent=None, product: dict | None = None) -> None:
        super().__init__(parent)
        self._product = product
        is_edit = product is not None

        self.setWindowTitle("Edit Product" if is_edit else "Tambah Product")
        self.setMinimumWidth(420)

        lay = QVBoxLayout(self)
        lay.setSpacing(12)

        # ── Form ──────────────────────────────────────────────────────────────
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

        # ── Buttons ───────────────────────────────────────────────────────────
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

        # ── Pre-fill bila edit ─────────────────────────────────────────────
        if is_edit:
            self._prefill(product)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _load_categories(self) -> None:
        """Mengisi combo box dengan data category dari database."""
        self._categories = get_all_categories()
        for cat in self._categories:
            self.category_combo.addItem(cat["category"], userData=cat["id"])

    def _prefill(self, p: dict) -> None:
        """Mengisi form dengan data product yang akan diedit."""
        self.name_input.setText(p.get("product_name", ""))
        self.sell_price_input.setValue(p.get("sell_price", 0))
        self.buy_price_input.setValue(p.get("buy_price", 0))
        self.stock_input.setValue(p.get("stock", 0))
        self.stock_storage_input.setValue(p.get("stock_storage", 0))
        self.desc_input.setPlainText(p.get("description", ""))

        # Set combo ke category yang sesuai
        cat_id = p.get("category_id")
        for i, cat in enumerate(self._categories):
            if cat["id"] == cat_id:
                self.category_combo.setCurrentIndex(i)
                break

    def _on_accept(self) -> None:
        """Validasi input sebelum menutup dialog."""
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Validasi", "Nama product tidak boleh kosong.")
            return
        if self.sell_price_input.value() <= 0:
            QMessageBox.warning(self, "Validasi", "Harga jual harus lebih dari 0.")
            return
        self.accept()

    # ── Getter hasil form ──────────────────────────────────────────────────────

    def get_data(self) -> dict:
        """Mengembalikan data form sebagai dict siap dipakai controller."""
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
# Halaman utama: Inventory / Storage
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
        add_btn.clicked.connect(self._open_create_dialog)
        hdr.addWidget(add_btn)

        return hdr

    def _build_stats(self) -> tuple[QHBoxLayout, dict]:
        from PyQt6.QtWidgets import QWidget, QSizePolicy
        from views.styles.theme_manager import card_style

        row = QHBoxLayout()
        row.setSpacing(12)
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
        self.table.setColumnWidth(8, 200)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.verticalHeader().setDefaultSectionSize(80)
        return self.table

    # ── Inline action widget per baris ───────────────────────────────────────

    def _make_action_widget(self, product: dict) -> QWidget:
        """
        Membuat widget berisi tombol Edit dan Hapus untuk satu baris tabel.
        product di-capture via default argument agar tidak terjadi closure bug.
        """
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        hlay = QHBoxLayout(container)
        hlay.setContentsMargins(10, 11, 10, 11)
        hlay.setSpacing(11)

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

        del_btn = QPushButton("🗑")
        del_btn.setFixedSize(36, 36)
        del_btn.setToolTip("Hapus product ini")
        del_btn.setStyleSheet(
            "QPushButton { background-color: #ef4444; color: white; border: none;"
            " border-radius: 4px; font-size: 13px; padding: 0 10px;}"
            "QPushButton:hover { background-color: #dc2626; }"
            "QPushButton:pressed { background-color: #b91c1c; }"
        )
        del_btn.clicked.connect(lambda _, p=product: self._delete_product(p))
        hlay.addWidget(del_btn)

        return container

    # ── Data ─────────────────────────────────────────────────────────────────

    def _refresh(self) -> None:
        """Ambil semua data dari DB, simpan cache, lalu render."""
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
        """Filter berdasarkan teks pencarian dan checkbox low-stock."""
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

            # Tombol Edit + Hapus langsung di baris
            self.table.setCellWidget(r, 8, self._make_action_widget(p))

    # ── Aksi CRUD ─────────────────────────────────────────────────────────────

    def _open_create_dialog(self) -> None:
        """Buka dialog tambah product baru."""
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
        """Buka dialog edit untuk product yang diberikan."""
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

    def _delete_product(self, product: dict) -> None:
        """Konfirmasi lalu hapus product yang diberikan."""
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