# ─────────────────────────────────────────────────────────────────────────────
# views/pages/suppliers.py
# ─────────────────────────────────────────────────────────────────────────────

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QDialogButtonBox, QFormLayout, QComboBox,
    QTabWidget, QTextEdit, QGroupBox, QGridLayout, QMessageBox,
    QDoubleSpinBox, QScrollArea, QCheckBox, QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl
from PyQt6.QtGui import QColor
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    _HAS_WEBENGINE = True
except ImportError:
    _HAS_WEBENGINE = False

from views.styles.theme_manager import make_label, h_line, card_style
from views.styles.palettes import (
    PRIMARY, PRIMARY_LIGHT, SUCCESS_FG, SUCCESS_BG,
    TEXT_SECONDARY, BORDER, BG_SURFACE, WARNING_FG, WARNING_BG,
)

# ── Import controller (sambungan ke database) ─────────────────────────────────
from controllers.supplier_controller import (
    create_supplier,
    get_all_suppliers,
    get_supplier,
    update_supplier,
    delete_supplier,
    search_suppliers_local,
    get_stats,
    scrape_only,
    save_suppliers,
)
from services.places_service import PlacesAPIError
from config import API_KEY, TOKO_LAT, TOKO_LNG

SOURCE_OPTIONS = ["manual", "google_places", "scraping"]


def _fmt_idr(amount) -> str:
    try:
        return f"Rp {float(amount):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return "Rp 0"


def _stars(rating) -> str:
    try:
        return f"⭐ {float(rating):.1f}"
    except (TypeError, ValueError):
        return "⭐ 0.0"


# ─────────────────────────── Add Supplier Dialog ──────────────────────────────

class AddSupplierDialog(QDialog):
    """
    Dialog dua tab:
      - Manual Input  → isi form lalu simpan ke DB
      - Google Places → scrape API lalu pilih import
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add New Supplier")
        self.setFixedWidth(620)
        self.setFixedHeight(680)
        self.setModal(True)

        # Data yang akan dikembalikan ke pemanggil setelah accept()
        self.saved_supplier: dict | None = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        lay.addWidget(make_label("Add New Supplier", 15, bold=True))
        lay.addWidget(make_label(
            "Tambah supplier secara manual atau temukan via Google Places",
            11, color=TEXT_SECONDARY,
        ))

        self._tabs = QTabWidget()
        self._tabs.addTab(self._manual_tab(), "Manual Input")
        self._tabs.addTab(self._google_tab(), "Google Places")
        lay.addWidget(self._tabs)

        btns = QDialogButtonBox()
        cancel = QPushButton("Cancel")
        cancel.setObjectName("btnOutline")
        self._save_btn = QPushButton("Add Supplier")
        btns.addButton(cancel, QDialogButtonBox.ButtonRole.RejectRole)
        btns.addButton(self._save_btn, QDialogButtonBox.ButtonRole.AcceptRole)
        cancel.clicked.connect(self.reject)
        self._save_btn.clicked.connect(self._on_save)
        lay.addWidget(btns)

    # ── Manual tab ────────────────────────────────────────────────────────────

    def _manual_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(12)
        v.setContentsMargins(0, 12, 0, 0)

        grid = QGridLayout()
        grid.setSpacing(10)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        # Field sesuai skema DB:
        #   supplier_name, email, number, rating, source_data
        # Field tambahan untuk UX: address (→ alamat di DB)
        fields = [
            ("Nama Supplier *",  "supplier_name", 0, 0),
            ("Email",            "email",         0, 1),
            ("No. Telepon / WA", "number",        1, 0),
            ("Alamat",           "alamat",        1, 1),
        ]
        self._fields: dict[str, QLineEdit] = {}
        for label, key, row, col in fields:
            cell = QVBoxLayout()
            cell.addWidget(make_label(label, 11, color=TEXT_SECONDARY))
            le = QLineEdit()
            le.setPlaceholderText("-")
            self._fields[key] = le
            cell.addWidget(le)
            grid.addLayout(cell, row, col)

        v.addLayout(grid)

        # Rating + Source Data
        row2 = QHBoxLayout()

        rating_col = QVBoxLayout()
        rating_col.addWidget(make_label("Rating (0.0 – 5.0)", 11, color=TEXT_SECONDARY))
        self._rating = QDoubleSpinBox()
        self._rating.setRange(0.0, 5.0)
        self._rating.setSingleStep(0.1)
        self._rating.setDecimals(1)
        self._rating.setValue(0.0)
        rating_col.addWidget(self._rating)
        row2.addLayout(rating_col)

        source_col = QVBoxLayout()
        source_col.addWidget(make_label("Sumber Data", 11, color=TEXT_SECONDARY))
        self._source = QComboBox()
        self._source.addItems(SOURCE_OPTIONS)
        source_col.addWidget(self._source)
        row2.addLayout(source_col)

        v.addLayout(row2)

        # Notes — disimpan sebagai bagian alamat / keterangan tambahan
        notes_col = QVBoxLayout()
        notes_col.addWidget(make_label("Catatan", 11, color=TEXT_SECONDARY))
        self._notes = QTextEdit()
        self._notes.setPlaceholderText("Catatan tambahan tentang supplier ini…")
        self._notes.setFixedHeight(72)
        notes_col.addWidget(self._notes)
        v.addLayout(notes_col)

        v.addStretch()
        return w

    # ── Google Places tab ─────────────────────────────────────────────────────

    def _google_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(12)
        v.setContentsMargins(0, 12, 0, 0)

        v.addWidget(make_label("Cari Supplier Terdekat via Google Places", 11, color=TEXT_SECONDARY))

        # Baris: kategori + radius + tombol cari
        row = QHBoxLayout()

        cat_col = QVBoxLayout()
        cat_col.addWidget(make_label("Kategori", 11, color=TEXT_SECONDARY))
        self._gp_category = QComboBox()
        self._gp_category.addItems([
            "Sembako", "Minyak Goreng", "Minuman", "Snack", "Frozen Food",
        ])
        cat_col.addWidget(self._gp_category)
        row.addLayout(cat_col)

        radius_col = QVBoxLayout()
        radius_col.addWidget(make_label("Radius (meter)", 11, color=TEXT_SECONDARY))
        self._gp_radius = QComboBox()
        self._gp_radius.addItems(["1000", "2000", "5000", "10000"])
        self._gp_radius.setCurrentText("5000")
        radius_col.addWidget(self._gp_radius)
        row.addLayout(radius_col)

        rating_col2 = QVBoxLayout()
        rating_col2.addWidget(make_label("Min. Rating", 11, color=TEXT_SECONDARY))
        self._gp_min_rating = QDoubleSpinBox()
        self._gp_min_rating.setRange(0.0, 5.0)
        self._gp_min_rating.setSingleStep(0.5)
        self._gp_min_rating.setValue(3.5)
        rating_col2.addWidget(self._gp_min_rating)
        row.addLayout(rating_col2)

        search_btn = QPushButton("🔍  Cari")
        search_btn.clicked.connect(self._do_scrape)
        row.addWidget(search_btn)

        v.addLayout(row)

        self._gp_status = QLabel("")
        self._gp_status.setStyleSheet(f"color:{TEXT_SECONDARY}; font-size:11px;")
        self._gp_status.setWordWrap(True)
        v.addWidget(self._gp_status)

        # Hasil scraping — dibungkus QScrollArea agar tidak meluap
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(340)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self._gp_results = QWidget()
        self._gp_results_lay = QVBoxLayout(self._gp_results)
        self._gp_results_lay.setSpacing(8)
        self._gp_results_lay.setContentsMargins(0, 0, 4, 0)
        self._gp_results_lay.addStretch()   # dorong card ke atas
        scroll.setWidget(self._gp_results)
        v.addWidget(scroll)

        # Action bar — Simpan Semua / Simpan Pilihan / Lewati
        self._action_bar = self._build_action_bar()
        v.addWidget(self._action_bar)

        return w

    # ── Scraping Google Places → controller ───────────────────────────────────

    def _do_scrape(self) -> None:
        """Panggil scrape_only() dari controller, tampilkan hasilnya + action bar."""
        self._clear_gp_results()
        self._gp_status.setText("⏳ Mencari supplier terdekat…")
        # Sembunyikan action bar dulu
        self._action_bar.setVisible(False)

        category   = self._gp_category.currentText()
        radius     = int(self._gp_radius.currentText())
        min_rating = self._gp_min_rating.value()

        try:
            results = scrape_only(category, radius, min_rating)
        except PlacesAPIError as e:
            self._gp_status.setText(f"❌ API Error: {e}")
            return
        except Exception as e:
            self._gp_status.setText(f"❌ Error: {e}")
            return

        if not results:
            self._gp_status.setText("Tidak ada supplier ditemukan dengan kriteria tersebut.")
            return

        new_count = sum(1 for r in results if not r.get("already_saved"))
        self._gp_status.setText(
            f"✅ Ditemukan {len(results)} supplier — "
            f"{new_count} baru, {len(results)-new_count} sudah tersimpan."
        )

        self._gp_data: list[dict] = results
        self._gp_checks: list = []          # simpan referensi QCheckBox

        for place in results:
            self._add_gp_card(place)

        # Tampilkan action bar jika ada data baru
        if new_count > 0:
            self._action_bar.setVisible(True)
        self._update_select_all_state()

    def _clear_gp_results(self) -> None:
        while self._gp_results_lay.count():
            item = self._gp_results_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._gp_checks = []
        self._gp_results_lay.addStretch()   # jaga stretch di akhir

    def _add_gp_card(self, place: dict) -> None:
        already = place.get("already_saved", False)

        card = QWidget()
        card.setStyleSheet(
            f"background:{BG_SURFACE}; border:1px solid {BORDER}; border-radius:8px;"
            + (f"opacity:0.55;" if already else "")
        )
        h = QHBoxLayout(card)
        h.setContentsMargins(12, 10, 12, 10)

        # Checkbox — disable jika sudah tersimpan
        from PyQt6.QtWidgets import QCheckBox
        cb = QCheckBox()
        cb.setChecked(not already)
        cb.setEnabled(not already)
        cb.setToolTip("Sudah ada di database" if already else "Pilih untuk disimpan")
        h.addWidget(cb)
        self._gp_checks.append((cb, place))

        info = QVBoxLayout()
        name_txt = place.get("supplierName", "-")
        if already:
            name_txt += "  ✓ tersimpan"
        info.addWidget(make_label(name_txt, 12, bold=True,
                                  color=TEXT_SECONDARY if already else None))
        info.addWidget(make_label(place.get("address", "-"), 10, color=TEXT_SECONDARY))
        info.addWidget(make_label(
            f"📞 {place.get('phone', '-')}  "
            f"⭐ {place.get('rating', 0)}  "
            f"📍 {place.get('distance_m', 0)} m",
            10, color=TEXT_SECONDARY,
        ))
        h.addLayout(info)
        h.addStretch()

        if not already:
            imp = QPushButton("Import ke Form")
            imp.setObjectName("btnSmall")
            imp.clicked.connect(lambda _, p=place: self._import_place(p))
            h.addWidget(imp)

        # Sisipkan sebelum stretch yang ada di akhir layout
        count = self._gp_results_lay.count()
        self._gp_results_lay.insertWidget(max(0, count - 1), card)

    # ── Action bar (Simpan Semua / Simpan Pilihan / Lewati) ───────────────────

    def _build_action_bar(self) -> QWidget:
        """Bar aksi di bawah hasil scraping — muncul setelah pencarian."""
        bar = QWidget()
        bar.setStyleSheet(
            f"background:{BG_SURFACE}; border:1px solid {BORDER}; border-radius:8px;"
        )
        h = QHBoxLayout(bar)
        h.setContentsMargins(12, 8, 12, 8)

        self._chk_all = QCheckBox("Pilih Semua")
        self._chk_all.setChecked(True)
        self._chk_all.stateChanged.connect(self._on_select_all)
        h.addWidget(self._chk_all)
        h.addStretch()

        self._lbl_selected = make_label("", 11, color=TEXT_SECONDARY)
        h.addWidget(self._lbl_selected)

        btn_all = QPushButton("💾  Simpan Semua")
        btn_all.clicked.connect(self._save_all)
        h.addWidget(btn_all)

        btn_sel = QPushButton("✔  Simpan Pilihan")
        btn_sel.setObjectName("btnOutline")
        btn_sel.clicked.connect(self._save_selected)
        h.addWidget(btn_sel)

        btn_skip = QPushButton("✖  Lewati")
        btn_skip.setObjectName("btnOutline")
        btn_skip.setStyleSheet("color:#DC2626;")
        btn_skip.clicked.connect(self._skip_save)
        h.addWidget(btn_skip)

        bar.setVisible(False)
        return bar

    def _update_select_all_state(self) -> None:
        enabled = [cb for cb, _ in getattr(self, "_gp_checks", []) if cb.isEnabled()]
        checked = [cb for cb in enabled if cb.isChecked()]
        total   = len(enabled)
        self._lbl_selected.setText(f"{len(checked)} dari {total} dipilih")
        # Update chk_all tanpa trigger loop
        self._chk_all.blockSignals(True)
        self._chk_all.setChecked(len(checked) == total and total > 0)
        self._chk_all.blockSignals(False)

    def _on_select_all(self, state: int) -> None:
        checked = bool(state)
        for cb, _ in getattr(self, "_gp_checks", []):
            if cb.isEnabled():
                cb.setChecked(checked)
        self._update_select_all_state()

    def _save_all(self) -> None:
        """Simpan semua supplier baru (yang belum ada di DB)."""
        new_places = [p for _, p in getattr(self, "_gp_checks", [])
                      if not p.get("already_saved")]
        n = save_suppliers(new_places)
        self._gp_status.setText(f"✅ {n} supplier berhasil disimpan ke database.")
        self._action_bar.setVisible(False)
        # Refresh checkbox state
        for cb, _ in self._gp_checks:
            if cb.isEnabled():
                cb.setChecked(False)
                cb.setEnabled(False)

    def _save_selected(self) -> None:
        """Simpan hanya supplier yang checkbox-nya dicentang."""
        selected = [p for cb, p in getattr(self, "_gp_checks", [])
                    if cb.isEnabled() and cb.isChecked()]
        if not selected:
            QMessageBox.information(self, "Info", "Tidak ada supplier yang dipilih.")
            return
        n = save_suppliers(selected)
        self._gp_status.setText(f"✅ {n} supplier pilihan berhasil disimpan.")
        self._action_bar.setVisible(False)
        for cb, _ in self._gp_checks:
            if cb.isEnabled():
                cb.setChecked(False)
                cb.setEnabled(False)

    def _skip_save(self) -> None:
        """Tutup action bar tanpa menyimpan apapun."""
        self._action_bar.setVisible(False)
        self._gp_status.setText("ℹ️ Tidak ada data yang disimpan.")

    def _import_place(self, place: dict) -> None:
        """Isi form Manual Input dengan data dari hasil scraping."""
        self._fields["supplier_name"].setText(place.get("supplierName", ""))
        self._fields["number"].setText(place.get("phone", ""))
        self._fields["alamat"].setText(place.get("address", ""))
        self._rating.setValue(float(place.get("rating", 0)))
        self._source.setCurrentText("google_places")
        self._notes.setPlainText(
            f"Diimpor dari Google Places\n"
            f"Kategori: {place.get('category', '-')}\n"
            f"Jarak: {place.get('distance_m', 0)} m"
        )
        self._tabs.setCurrentIndex(0)

    # ── Simpan ke database via controller ─────────────────────────────────────

    def _on_save(self) -> None:
        """Validasi form lalu panggil create_supplier()."""
        supplier_name = self._fields["supplier_name"].text().strip()
        email         = self._fields["email"].text().strip()
        number        = self._fields["number"].text().strip()
        alamat        = self._fields["alamat"].text().strip()
        rating        = self._rating.value()
        source_data   = self._source.currentText()

        # Gabungkan catatan ke alamat jika ada
        catatan = self._notes.toPlainText().strip()

        if not supplier_name:
            QMessageBox.warning(self, "Validasi", "Nama supplier tidak boleh kosong.")
            return

        try:
            new_id = create_supplier(
                supplier_name=supplier_name,
                email=email,
                phone=number,
                rating=rating,
                category=source_data,   # pakai source sebagai category sementara
                address=alamat,
            )
            # Simpan data yg baru dibuat supaya SuppliersPage bisa refresh
            self.saved_supplier = {
                "id":            new_id,
                "supplier_name": supplier_name,
                "email":         email,
                "number":        number,
                "alamat":        alamat,
                "rating":        rating,
                "source_data":   source_data,
                "aktif":         1,
            }
            self.accept()

        except ValueError as e:
            QMessageBox.warning(self, "Validasi", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Gagal menyimpan supplier:\n{e}")

    def get_data(self) -> dict | None:
        """Kembalikan data supplier yang baru disimpan (None jika cancel)."""
        return self.saved_supplier


# ─────────────────────────── Edit Supplier Dialog ────────────────────────────

class EditSupplierDialog(QDialog):
    """Form edit supplier — field sesuai skema DB."""

    def __init__(self, supplier_data: dict, parent=None) -> None:
        super().__init__(parent)
        self._supplier_id = supplier_data.get("id")
        self.setWindowTitle(f"Edit — {supplier_data.get('supplier_name', '')}")
        self.setFixedWidth(560)
        self.setModal(True)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        lay.addWidget(make_label("Edit Supplier", 15, bold=True))
        lay.addWidget(h_line())

        grid = QGridLayout()
        grid.setSpacing(10)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        fields_def = [
            ("Nama Supplier *",  "supplier_name", 0, 0),
            ("Email",            "email",         0, 1),
            ("No. Telepon / WA", "number",        1, 0),
            ("Alamat",           "alamat",        1, 1),
        ]
        self._fields: dict[str, QLineEdit] = {}
        for label, key, row, col in fields_def:
            cell = QVBoxLayout()
            cell.addWidget(make_label(label, 11, color=TEXT_SECONDARY))
            le = QLineEdit()
            value = str(supplier_data.get(key, "") or "")
            le.setText(value if value and value != "None" else "-")
            self._fields[key] = le
            cell.addWidget(le)
            grid.addLayout(cell, row, col)

        lay.addLayout(grid)

        # Rating
        r_row = QHBoxLayout()
        r_col = QVBoxLayout()
        r_col.addWidget(make_label("Rating (0.0 – 5.0)", 11, color=TEXT_SECONDARY))
        self._rating = QDoubleSpinBox()
        self._rating.setRange(0.0, 5.0)
        self._rating.setSingleStep(0.1)
        self._rating.setDecimals(1)
        self._rating.setValue(float(supplier_data.get("rating", 0)))
        r_col.addWidget(self._rating)
        r_row.addLayout(r_col)
        r_row.addStretch()
        lay.addLayout(r_row)

        # Buttons
        btns = QDialogButtonBox()
        cancel = QPushButton("Cancel")
        cancel.setObjectName("btnOutline")
        save = QPushButton("Simpan Perubahan")
        btns.addButton(cancel, QDialogButtonBox.ButtonRole.RejectRole)
        btns.addButton(save, QDialogButtonBox.ButtonRole.AcceptRole)
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self._on_save)
        lay.addWidget(btns)

    def _on_save(self) -> None:
        supplier_name = self._fields["supplier_name"].text().strip()
        email         = self._fields["email"].text().strip()
        number        = self._fields["number"].text().strip()
        rating        = self._rating.value()

        if not supplier_name:
            QMessageBox.warning(self, "Validasi", "Nama supplier tidak boleh kosong.")
            return

        try:
            update_supplier(
                supplier_id=self._supplier_id,
                supplier_name=supplier_name,
                email=email,
                phone=number,
                rating=rating,
            )
            self.accept()
        except ValueError as e:
            QMessageBox.warning(self, "Validasi", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Gagal memperbarui supplier:\n{e}")


# ─────────────────────────── Supplier Detail Dialog ──────────────────────────

class SupplierDetailDialog(QDialog):
    """Tampilkan detail satu supplier + tombol Edit dan Delete."""

    # Signal agar SuppliersPage tahu kalau ada perubahan
    supplier_updated = pyqtSignal()
    supplier_deleted = pyqtSignal()

    def __init__(self, supplier_data: dict, parent=None) -> None:
        super().__init__(parent)
        self._data = supplier_data
        self.setWindowTitle(supplier_data.get("supplier_name", "Detail Supplier"))
        self.setFixedWidth(580)
        self.setModal(True)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        # Judul
        lay.addWidget(make_label(
            f"🏢  {supplier_data.get('supplier_name', '-')}", 15, bold=True
        ))
        lay.addWidget(h_line())

        # Dua kolom: kontak | performa
        cols = QHBoxLayout()

        # Kontak
        contact = QGroupBox("Informasi Kontak")
        contact.setStyleSheet(
            f"QGroupBox {{ background:{BG_SURFACE}; border:1px solid {BORDER}; border-radius:10px; }}"
        )
        cv = QVBoxLayout(contact)
        for icon, key, fallback in [
            ("✉️", "email",  "—"),
            ("📞", "number", "—"),
            ("📍", "alamat", "—"),
        ]:
            row = QHBoxLayout()
            row.addWidget(make_label(icon, 12))
            lbl = make_label(supplier_data.get(key) or fallback, 11, color=TEXT_SECONDARY)
            lbl.setWordWrap(True)
            row.addWidget(lbl)
            row.addStretch()
            cv.addLayout(row)
        cols.addWidget(contact)

        # Performa
        metrics = QGroupBox("Performa")
        metrics.setStyleSheet(
            f"QGroupBox {{ background:{BG_SURFACE}; border:1px solid {BORDER}; border-radius:10px; }}"
        )
        mv = QFormLayout(metrics)
        mv.addRow(
            make_label("Rating", 11, color=TEXT_SECONDARY),
            make_label(_stars(supplier_data.get("rating")), 12, bold=True),
        )
        mv.addRow(
            make_label("Sumber Data", 11, color=TEXT_SECONDARY),
            make_label(str(supplier_data.get("source_data", "manual")), 12),
        )
        mv.addRow(
            make_label("Status", 11, color=TEXT_SECONDARY),
            make_label(
                "✅ Aktif" if supplier_data.get("aktif", 1) else "❌ Nonaktif",
                12, bold=True,
            ),
        )
        cols.addWidget(metrics)
        lay.addLayout(cols)

        # Tombol bawah: Close | Delete | Edit
        btns = QHBoxLayout()
        close_btn = QPushButton("Tutup")
        close_btn.setObjectName("btnOutline")
        close_btn.clicked.connect(self.reject)

        del_btn = QPushButton("🗑  Hapus")
        del_btn.setObjectName("btnOutline")
        del_btn.setStyleSheet(f"color: #DC2626;")
        del_btn.clicked.connect(self._on_delete)

        edit_btn = QPushButton("✏️  Edit Supplier")
        edit_btn.clicked.connect(self._on_edit)

        btns.addWidget(close_btn)
        btns.addStretch()
        btns.addWidget(del_btn)
        btns.addWidget(edit_btn)
        lay.addLayout(btns)

    def _on_edit(self) -> None:
        dlg = EditSupplierDialog(self._data, self)
        if dlg.exec():
            self.supplier_updated.emit()
            self.accept()

    def _on_delete(self) -> None:
        nama = self._data.get("supplier_name", "ini")
        konfirm = QMessageBox.question(
            self, "Konfirmasi Hapus",
            f"Yakin ingin menghapus supplier <b>{nama}</b>?<br>"
            f"Data akan di-nonaktifkan (soft delete).",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if konfirm != QMessageBox.StandardButton.Yes:
            return
        try:
            delete_supplier(self._data["id"])
            self.supplier_deleted.emit()
            self.accept()
        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Gagal menghapus supplier:\n{e}")


# ─────────────────────────── Suppliers Page ──────────────────────────────────

class SuppliersPage(QWidget):
    """Halaman manajemen supplier — tabel, tambah, edit, hapus."""

    status_msg = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._suppliers: list[dict] = []

        # Layout utama — hanya scroll area
        root_lay = QVBoxLayout(self)
        root_lay.setSpacing(0)
        root_lay.setContentsMargins(0, 0, 0, 0)

        # Scroll area internal agar tabel tidak mengecil
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(self._scroll.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setSpacing(16)
        lay.setContentsMargins(0, 0, 8, 16)

        lay.addLayout(self._build_header())
        self._stats_row = self._build_stats()
        lay.addLayout(self._stats_row)

        # ── Visualisasi (sebelum tabel) ───────────────────────────────────────
        self._map_widget     = self._build_map_section()
        self._scatter_widget = self._build_scatter_section()
        lay.addWidget(self._map_widget)
        lay.addWidget(self._scatter_widget)

        lay.addLayout(self._build_controls())

        # Tabel dengan minimum height agar tidak terlalu kecil
        tbl = self._build_table()
        tbl.setMinimumHeight(320)
        lay.addWidget(tbl, stretch=1)

        self._scroll.setWidget(inner)
        root_lay.addWidget(self._scroll)

        self._load_data()

    # ── Build sections ────────────────────────────────────────────────────────

    def _build_header(self) -> QHBoxLayout:
        hdr = QHBoxLayout()

        info = QVBoxLayout()
        info.addWidget(make_label("Supplier Management", 18, bold=True))
        info.addWidget(make_label(
            "Kelola supplier dan hubungan vendor", 12, color=TEXT_SECONDARY
        ))
        hdr.addLayout(info)
        hdr.addStretch()

        add_btn = QPushButton("+ Tambah Supplier")
        add_btn.clicked.connect(self._open_add_dialog)
        hdr.addWidget(add_btn)

        return hdr

    def _build_stats(self) -> QHBoxLayout:
        """Stat cards — diisi ulang tiap _refresh_stats()."""
        row = QHBoxLayout()
        self._stat_cards: list[tuple[QLabel, QLabel, QLabel]] = []

        titles = [
            ("Total Supplier",  "—", "dari database"),
            ("Avg Rating",      "—", "berdasarkan performa"),
            ("Supplier Aktif",  "—", "aktif saat ini"),
            ("Kategori",        "—", "jenis produk"),
        ]
        for title, val, sub in titles:
            card = QWidget()
            card.setStyleSheet(card_style())
            cv = QVBoxLayout(card)
            t_lbl = make_label(title, 11, color=TEXT_SECONDARY)
            v_lbl = make_label(val, 18, bold=True)
            s_lbl = make_label(sub, 10, color=TEXT_SECONDARY)
            cv.addWidget(t_lbl)
            cv.addWidget(v_lbl)
            cv.addWidget(s_lbl)
            self._stat_cards.append((t_lbl, v_lbl, s_lbl))
            row.addWidget(card)

        return row

    def _refresh_stats(self) -> None:
        """Update angka di stat cards dari controller."""
        try:
            stats = get_stats()
        except Exception:
            return

        aktif = sum(1 for s in self._suppliers if s.get("aktif", 1))
        cats  = set(
            s.get("source_data", "") for s in self._suppliers if s.get("source_data")
        )

        values = [
            str(stats.get("total", len(self._suppliers))),
            f"⭐ {stats.get('avg_rating', 0.0):.1f}",
            str(aktif),
            str(len(cats)),
        ]
        for (_, v_lbl, _), val in zip(self._stat_cards, values):
            v_lbl.setText(val)

    def _build_controls(self) -> QHBoxLayout:
        ctrl = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  Cari nama supplier, email, atau nomor…")
        self.search.textChanged.connect(self._on_search)
        ctrl.addWidget(self.search)

        refresh_btn = QPushButton("🔄")
        refresh_btn.setToolTip("Muat ulang data dari database")
        refresh_btn.setFixedWidth(36)
        refresh_btn.clicked.connect(self._load_data)
        ctrl.addWidget(refresh_btn)

        return ctrl

    # ── Visualisasi: Cluster Map ──────────────────────────────────────────────

    def _build_map_section(self) -> QWidget:
        """Section peta sebaran supplier menggunakan Leaflet.js via QWebEngineView."""
        wrapper = QWidget()
        wrapper.setObjectName("mapSection")
        wrapper.setStyleSheet(
            "QWidget#mapSection {"
            f" background:{BG_SURFACE}; border:1px solid {BORDER};"
            " border-radius:12px; }"
        )
        lay = QVBoxLayout(wrapper)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)

        hdr = QHBoxLayout()
        hdr.addWidget(make_label("🗺️  Peta Sebaran Supplier", 13, bold=True))
        hdr.addStretch()
        self._map_count_lbl = make_label("", 11, color="#64748b")
        hdr.addWidget(self._map_count_lbl)
        lay.addLayout(hdr)
        lay.addWidget(make_label(
            "Lokasi supplier dari data Google Places — titik cluster otomatis saat zoom out.",
            11, color="#64748b",
        ))

        if _HAS_WEBENGINE:
            self._map_view = QWebEngineView()
            self._map_view.setFixedHeight(320)
            self._map_view.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
            lay.addWidget(self._map_view)
        else:
            lay.addWidget(make_label(
                "⚠ PyQt6-WebEngine tidak terinstall.\n"
                "Jalankan: pip install PyQt6-WebEngine",
                12, color="#ef4444",
            ))

        return wrapper

    def _render_map(self, suppliers: list[dict]) -> None:
        """Render Leaflet cluster map dengan data supplier."""
        if not _HAS_WEBENGINE:
            return

        geo = [
            s for s in suppliers
            if s.get("lat") and s.get("lng")
            and float(s.get("lat", 0)) != 0.0
            and float(s.get("lng", 0)) != 0.0
        ]
        self._map_count_lbl.setText(f"{len(geo)} dari {len(suppliers)} supplier dipetakan")

        markers_js = ""
        for s in geo:
            name    = (s.get("supplier_name") or "").replace("'", "\'")
            alamat  = (s.get("alamat") or "-").replace("'", "\'")
            rating  = float(s.get("rating") or 0)
            lat     = float(s["lat"])
            lng     = float(s["lng"])
            color   = "#18A558" if rating >= 4.0 else "#F59E0B" if rating >= 3.0 else "#DC2626"
            markers_js += (
                f"L.circleMarker([{lat},{lng}], {{"
                f"radius:8, fillColor:'{color}', color:'#fff',"
                f"weight:2, opacity:1, fillOpacity:0.85"
                f"}}).addTo(markers)"
                f".bindPopup('<b>{name}</b><br>📍 {alamat}<br>⭐ {rating:.1f}');"
            )

        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset='utf-8'/>
<meta name='viewport' content='width=device-width,initial-scale=1'/>
<link rel='stylesheet' href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'/>
<link rel='stylesheet' href='https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css'/>
<link rel='stylesheet' href='https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css'/>
<script src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'></script>
<script src='https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js'></script>
<style>
  html,body,#map{{margin:0;padding:0;width:100%;height:100%;}}
  .legend{{background:#fff;padding:10px 14px;border-radius:8px;
           box-shadow:0 2px 8px rgba(0,0,0,.15);font-size:12px;line-height:20px;}}
  .legend span{{display:inline-block;width:12px;height:12px;
                border-radius:50%;margin-right:6px;vertical-align:middle;}}
</style>
</head>
<body>
<div id='map'></div>
<script>
  var map = L.map('map').setView([{TOKO_LAT},{TOKO_LNG}], 12);
  L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',
    {{attribution:'© OpenStreetMap contributors', maxZoom:18}}).addTo(map);

  // Toko sendiri — pin biru
  L.marker([{TOKO_LAT},{TOKO_LNG}])
    .addTo(map)
    .bindPopup('<b>📦 Toko Anda</b>')
    .openPopup();

  var markers = L.markerClusterGroup({{maxClusterRadius:50}});
  {markers_js}
  map.addLayer(markers);

  // Legend
  var legend = L.control({{position:'bottomright'}});
  legend.onAdd = function(){{
    var d=L.DomUtil.create('div','legend');
    d.innerHTML='<b>Rating</b><br>'
      +'<span style="background:#18A558"></span>≥ 4.0<br>'
      +'<span style="background:#F59E0B"></span>3.0 – 3.9<br>'
      +'<span style="background:#DC2626"></span>< 3.0';
    return d;
  }};
  legend.addTo(map);
</script>
</body>
</html>"""
        self._map_view.setHtml(html, QUrl("about:blank"))

    # ── Visualisasi: Scatter Plot Rating vs Review ─────────────────────────────

    def _build_scatter_section(self) -> QWidget:
        """Scatter plot Rating vs Jumlah Review via Chart.js."""
        wrapper = QWidget()
        wrapper.setObjectName("scatterSection")
        wrapper.setStyleSheet(
            "QWidget#scatterSection {"
            f" background:{BG_SURFACE}; border:1px solid {BORDER};"
            " border-radius:12px; }"
        )
        lay = QVBoxLayout(wrapper)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)

        hdr = QHBoxLayout()
        hdr.addWidget(make_label("📊  Rating vs Jumlah Review", 13, bold=True))
        hdr.addStretch()
        lay.addLayout(hdr)
        lay.addWidget(make_label(
            "Setiap titik = 1 supplier. Hover untuk detail. Warna = kategori insight.",
            11, color="#64748b",
        ))

        # Legend insight
        legend_row = QHBoxLayout()
        legend_row.setSpacing(16)
        for color, label in [
            ("#18A558", "⬤  Kuat & terpercaya (rating ≥4 + review banyak)"),
            ("#DC2626", "⬤  Peluang kompetitor (rating rendah + review tinggi)"),
            ("#5B5BD6", "⬤  Hidden gem (rating tinggi + review sedikit)"),
            ("#94a3b8", "⬤  Lainnya"),
        ]:
            lbl = QLabel(label)
            lbl.setStyleSheet(f"font-size:10px; color:{color};")
            legend_row.addWidget(lbl)
        legend_row.addStretch()
        lay.addLayout(legend_row)

        if _HAS_WEBENGINE:
            self._scatter_view = QWebEngineView()
            self._scatter_view.setFixedHeight(300)
            self._scatter_view.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
            lay.addWidget(self._scatter_view)
        else:
            lay.addWidget(make_label(
                "⚠ PyQt6-WebEngine tidak terinstall.\n"
                "Jalankan: pip install PyQt6-WebEngine",
                12, color="#ef4444",
            ))

        return wrapper

    def _render_scatter(self, suppliers: list[dict]) -> None:
        """Render Chart.js scatter plot Rating vs user_ratings_total."""
        if not _HAS_WEBENGINE:
            return

        points = []
        for s in suppliers:
            rating  = float(s.get("rating") or 0)
            reviews = int(s.get("user_ratings_total") or s.get("reviews") or 0)
            if rating == 0 and reviews == 0:
                continue
            # Sanitize untuk konteks JSON di dalam HTML (hindari karakter pemutus string)
            name   = (s.get("supplier_name") or "-").replace("\\", "").replace('"', "&quot;").replace("'", "&#39;")
            alamat = (s.get("alamat") or "-").replace("\\", "").replace('"', "&quot;").replace("'", "&#39;")

            # Tentukan warna berdasarkan kuadran insight
            avg_reviews = 50  # threshold: banyak review
            if rating >= 4.0 and reviews >= avg_reviews:
                color = "rgba(24,165,88,0.85)"   # hijau — kuat & terpercaya
            elif rating < 3.5 and reviews >= avg_reviews:
                color = "rgba(220,38,38,0.85)"   # merah — peluang kompetitor
            elif rating >= 4.0 and reviews < avg_reviews:
                color = "rgba(91,91,214,0.85)"   # ungu — hidden gem
            else:
                color = "rgba(148,163,184,0.75)" # abu — biasa

            points.append(
                f'{{"x":{reviews},"y":{rating},"label":"{name}","alamat":"{alamat}",'
                f'"borderColor":"{color}","backgroundColor":"{color}"}}'
            )

        points_json = "[" + ",".join(points) + "]"

        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset='utf-8'/>
<script src='https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js'></script>
<style>
  html,body{{margin:0;padding:12px;background:#fff;box-sizing:border-box;}}
  #c{{width:100%;height:320px;}}
  #tooltip-box{{
    position:absolute;display:none;background:#1e293b;color:#f8fafc;
    padding:8px 12px;border-radius:8px;font-size:12px;
    pointer-events:none;max-width:240px;line-height:1.6;
    box-shadow:0 4px 12px rgba(0,0,0,.3);
  }}
</style>
</head>
<body>
<canvas id='c'></canvas>
<div id='tooltip-box'></div>
<script>
var raw = {points_json};

// Semua titik digabung ke SATU dataset agar tidak ada batas jumlah dataset.
// FIX: pointRadius & pointHoverRadius harus berupa ARRAY (satu nilai per titik)
// agar Chart.js v4 render semua titik dengan benar, bukan skalar tunggal.
var n = raw.length;
var dataset = {{
  data:             raw.map(function(p){{ return {{x:p.x, y:p.y}}; }}),
  backgroundColor:  raw.map(function(p){{ return p.backgroundColor; }}),
  borderColor:      raw.map(function(p){{ return p.borderColor; }}),
  pointRadius:      Array(n).fill(9),
  pointHoverRadius: Array(n).fill(12),
  borderWidth:      2,
}};

var ctx = document.getElementById('c').getContext('2d');
var chart = new Chart(ctx, {{
  type: 'scatter',
  data: {{datasets: [dataset]}},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{
      legend: {{display: false}},
      tooltip: {{
        enabled: false,
        external: function(context) {{
          var tip = document.getElementById('tooltip-box');
          if (context.tooltip.opacity === 0) {{ tip.style.display='none'; return; }}
          var d = context.tooltip.dataPoints[0];
          var p = raw[d.dataIndex];
          tip.innerHTML = '<b>'+p.label+'</b><br>📍 '+p.alamat
            +'<br>⭐ Rating: <b>'+d.parsed.y.toFixed(1)+'</b>'
            +'<br>💬 Review: <b>'+d.parsed.x+'</b>';
          tip.style.display = 'block';
          tip.style.left = (context.tooltip.caretX + 16) + 'px';
          tip.style.top  = (context.tooltip.caretY - 10) + 'px';
        }}
      }}
    }},
    scales: {{
      x: {{
        title: {{display:true, text:'Jumlah Review', font:{{size:12}}}},
        beginAtZero: true,
        grid: {{color:'rgba(0,0,0,.06)'}},
      }},
      y: {{
        title: {{display:true, text:'Rating', font:{{size:12}}}},
        min: 0, max: 5.5,
        ticks: {{stepSize: 0.5}},
        grid: {{color:'rgba(0,0,0,.06)'}},
      }}
    }}
  }}
}});
</script>
</body>
</html>"""
        self._scatter_view.setHtml(html, QUrl("about:blank"))

    def _build_table(self) -> QTableWidget:
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Supplier", "Email", "No. Telepon", "Rating", "Sumber", "Status"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.cellDoubleClicked.connect(self._open_detail)
        self.table.setToolTip("Double-click untuk melihat detail supplier")
        return self.table

    # ── Data loading ──────────────────────────────────────────────────────────

    def _load_data(self) -> None:
        """Ambil semua supplier dari database via controller."""
        try:
            self._suppliers = get_all_suppliers()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Gagal memuat data supplier:\n{e}")
            self._suppliers = []

        self._refresh_table(self._suppliers)
        self._refresh_stats()
        self._render_map(self._suppliers)
        self._render_scatter(self._suppliers)

    def _on_search(self) -> None:
        keyword = self.search.text().strip()
        if not keyword:
            self._refresh_table(self._suppliers)
            return
        try:
            hasil = search_suppliers_local(keyword)
            self._refresh_table(hasil)
        except Exception:
            self._refresh_table(self._suppliers)

    # ── Table rendering ───────────────────────────────────────────────────────

    def _refresh_table(self, rows: list[dict]) -> None:
        self.table.setRowCount(len(rows))

        for r, s in enumerate(rows):
            # Kolom 0: Nama supplier + alamat
            name_widget = QWidget()
            nv = QVBoxLayout(name_widget)
            nv.setContentsMargins(8, 4, 8, 4)
            nv.addWidget(make_label(s.get("supplier_name", "—"), 12, bold=True))
            alamat = s.get("alamat", "") or s.get("address", "")
            if alamat:
                nv.addWidget(make_label(f"📍 {alamat}", 10, color=TEXT_SECONDARY))
            self.table.setCellWidget(r, 0, name_widget)

            # Kolom 1: Email
            self.table.setItem(r, 1, QTableWidgetItem(s.get("email", "—") or "—"))

            # Kolom 2: Nomor telepon
            self.table.setItem(r, 2, QTableWidgetItem(s.get("number", "—") or "—"))

            # Kolom 3: Rating
            self.table.setItem(r, 3, QTableWidgetItem(_stars(s.get("rating"))))

            # Kolom 4: Sumber data
            self.table.setItem(r, 4, QTableWidgetItem(s.get("source_data", "manual")))

            # Kolom 5: Status badge
            aktif = s.get("aktif", 1)
            status_item = QTableWidgetItem("Aktif" if aktif else "Nonaktif")
            if aktif:
                status_item.setForeground(QColor(SUCCESS_FG))
                status_item.setBackground(QColor(SUCCESS_BG))
            else:
                status_item.setForeground(QColor(WARNING_FG))
                status_item.setBackground(QColor(WARNING_BG))
            self.table.setItem(r, 5, status_item)

        self.table.resizeRowsToContents()

    # ── Dialogs ───────────────────────────────────────────────────────────────

    def _open_add_dialog(self) -> None:
        dlg = AddSupplierDialog(self)
        if dlg.exec():
            new_data = dlg.get_data()
            if new_data:
                nama = new_data.get("supplier_name", "")
                self.status_msg.emit(f"✅ Supplier '{nama}' berhasil ditambahkan.")
            self._load_data()   # reload dari DB

    def _open_detail(self, row: int, _: int) -> None:
        # Ambil data dari tabel yang sedang ditampilkan (bisa hasil search)
        keyword = self.search.text().strip()
        if keyword:
            try:
                displayed = search_suppliers_local(keyword)
            except Exception:
                displayed = self._suppliers
        else:
            displayed = self._suppliers

        if row >= len(displayed):
            return

        supplier_data = displayed[row]

        dlg = SupplierDetailDialog(supplier_data, self)
        dlg.supplier_updated.connect(lambda: (
            self.status_msg.emit(f"✅ Supplier '{supplier_data.get('supplier_name')}' diperbarui."),
            self._load_data(),
        ))
        dlg.supplier_deleted.connect(lambda: (
            self.status_msg.emit(f"🗑 Supplier '{supplier_data.get('supplier_name')}' dihapus."),
            self._load_data(),
        ))
        dlg.exec()