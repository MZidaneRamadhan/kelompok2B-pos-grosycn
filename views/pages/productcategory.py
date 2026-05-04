# ─────────────────────────────────────────────────────────────────────────────
# views/pages/category_product.py
# ─────────────────────────────────────────────────────────────────────────────

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QFormLayout, QDialogButtonBox, QMessageBox, QSizePolicy,
)
from PyQt6.QtCore import pyqtSignal, Qt

from views.styles.theme_manager import make_label
from controllers.barang_controller import (
    get_all_categories,
    create_category,
    update_category,
    delete_category,
)


# ─────────────────────────────────────────────────────────────────────────────
# Dialog: Tambah / Edit Category
# ─────────────────────────────────────────────────────────────────────────────

class CategoryDialog(QDialog):
    """Dialog untuk CREATE (category=None) atau UPDATE (category=dict)."""

    def __init__(self, parent=None, category: dict | None = None) -> None:
        super().__init__(parent)
        is_edit = category is not None
        self.category = category
        self.is_edit = is_edit

        self.setWindowTitle("Edit Category" if is_edit else "Tambah Category")
        self.setMinimumWidth(360)

        lay = QVBoxLayout(self)
        lay.setSpacing(12)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nama category")
        form.addRow("Nama Category:", self.name_input)

        lay.addLayout(form)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

        if is_edit:
            self.name_input.setText(category.get("category", ""))

    def _on_accept(self) -> None:
        new_name = self.name_input.text().strip()
        
        if not new_name:
            QMessageBox.warning(self, "Validasi", "Nama category tidak boleh kosong.")
            return
        
        # Jika edit mode, cek apakah nama sudah ada di kategori lain
        if self.is_edit:
            old_name = self.category.get("category", "")
            if new_name != old_name:  # Nama berubah
                all_categories = get_all_categories()
                for cat in all_categories:
                    if cat.get("category", "").lower() == new_name.lower():
                        QMessageBox.warning(
                            self, 
                            "Validasi", 
                            f"Nama category '{new_name}' sudah ada. Gunakan nama lain."
                        )
                        return
        else:  # Create mode
            all_categories = get_all_categories()
            for cat in all_categories:
                if cat.get("category", "").lower() == new_name.lower():
                    QMessageBox.warning(
                        self, 
                        "Validasi", 
                        f"Nama category '{new_name}' sudah ada. Gunakan nama lain."
                    )
                    return
        
        self.accept()

    def get_data(self) -> dict:
        return {"category_name": self.name_input.text().strip()}


# ─────────────────────────────────────────────────────────────────────────────
# Halaman utama: Category Product
# ─────────────────────────────────────────────────────────────────────────────

class CategoryProductPage(QWidget):
    """Manajemen category produk dengan tabel dan CRUD inline."""

    status_msg = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        lay = QVBoxLayout(self)
        lay.setSpacing(16)
        lay.setContentsMargins(0, 0, 0, 0)

        lay.addLayout(self._build_header())
        lay.addLayout(self._build_controls())
        lay.addWidget(self._build_table())

        self._refresh()

    # ── Sections ──────────────────────────────────────────────────────────────

    def _build_header(self) -> QHBoxLayout:
        hdr = QHBoxLayout()

        info = QVBoxLayout()
        info.addWidget(make_label("Category Product", 18, bold=True))
        info.addWidget(make_label("Kelola daftar category untuk produk", 12, color="#64748b"))
        hdr.addLayout(info)
        hdr.addStretch()

        add_btn = QPushButton("+ Add Category")
        add_btn.clicked.connect(self._open_create_dialog)
        hdr.addWidget(add_btn)

        return hdr

    def _build_controls(self) -> QHBoxLayout:
        ctrl = QHBoxLayout()

        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  Search by category name…")
        self.search.textChanged.connect(self._apply_filter)
        ctrl.addWidget(self.search)

        return ctrl

    def _build_table(self) -> QTableWidget:
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", "Nama Category", "Aksi"])

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)

        self.table.setColumnWidth(0, 60)
        self.table.setColumnWidth(2, 160)

        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.verticalHeader().setDefaultSectionSize(58)

        return self.table

    # ── Inline action widget ───────────────────────────────────────────────────

    def _make_action_widget(self, category: dict) -> QWidget:
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        hlay = QHBoxLayout(container)
        hlay.setContentsMargins(10, 11, 10, 11)
        hlay.setSpacing(8)

        edit_btn = QPushButton("✏ Edit")
        edit_btn.setFixedHeight(36)
        edit_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        edit_btn.setStyleSheet(
            "QPushButton { background-color: #3b82f6; color: white; border: none;"
            " border-radius: 4px; padding: 0 8px; font-size: 12px; }"
            "QPushButton:hover { background-color: #2563eb; }"
            "QPushButton:pressed { background-color: #1d4ed8; }"
        )
        edit_btn.clicked.connect(lambda _, c=category: self._open_edit_dialog(c))
        hlay.addWidget(edit_btn)

        del_btn = QPushButton("🗑")
        del_btn.setFixedSize(36, 36)
        del_btn.setToolTip("Hapus category ini")
        del_btn.setStyleSheet(
            "QPushButton { background-color: #ef4444; color: white; border: none;"
            " border-radius: 4px; font-size: 13px; padding: 0 10px; }"
            "QPushButton:hover { background-color: #dc2626; }"
            "QPushButton:pressed { background-color: #b91c1c; }"
        )
        del_btn.clicked.connect(lambda _, c=category: self._delete_category(c))
        hlay.addWidget(del_btn)

        return container

    # ── Data ─────────────────────────────────────────────────────────────────

    def _refresh(self) -> None:
        self._all_categories = get_all_categories()
        self._apply_filter()

    def _apply_filter(self) -> None:
        q = self.search.text().lower()

        rows = [
            c for c in self._all_categories
            if q in c["category"].lower()
        ]

        self.table.setRowCount(len(rows))
        for r, c in enumerate(rows):
            self.table.setItem(r, 0, QTableWidgetItem(str(c["id"])))
            self.table.setItem(r, 1, QTableWidgetItem(c["category"]))
            self.table.setCellWidget(r, 2, self._make_action_widget(c))

    # ── Aksi CRUD ─────────────────────────────────────────────────────────────

    def _open_create_dialog(self) -> None:
        dlg = CategoryDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            new_id = create_category(data["category_name"])
            if new_id:
                self.status_msg.emit(f"Category '{data['category_name']}' berhasil ditambahkan.")
                self._refresh()
            else:
                QMessageBox.critical(self, "Error", "Gagal menambahkan category.")

    def _open_edit_dialog(self, category: dict) -> None:
        dlg = CategoryDialog(self, category=category)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            ok = update_category(category["id"], data["category_name"])
            if ok:
                self.status_msg.emit(f"Category berhasil diperbarui menjadi '{data['category_name']}'.")
                self._refresh()
            else:
                QMessageBox.critical(self, "Error", "Gagal memperbarui category.")

    def _delete_category(self, category: dict) -> None:
        confirm = QMessageBox.question(
            self,
            "Konfirmasi Hapus",
            f"Yakin ingin menghapus category '{category['category']}'?\n"
            "Produk yang menggunakan category ini akan kehilangan referensinya.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            ok = delete_category(category["id"])
            if ok:
                self.status_msg.emit(f"Category '{category['category']}' berhasil dihapus.")
                self._refresh()
            else:
                QMessageBox.critical(self, "Error", "Gagal menghapus category.")