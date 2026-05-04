# ─────────────────────────────────────────────────────────────────────────────
# views/pages/suppliers.py
# ─────────────────────────────────────────────────────────────────────────────

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QDialogButtonBox, QFormLayout, QComboBox,
    QTabWidget, QTextEdit, QGroupBox, QGridLayout,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from views.styles.theme_manager import make_label, h_line, card_style
from views.styles.palettes import (
    PRIMARY, PRIMARY_LIGHT, SUCCESS_FG, SUCCESS_BG,
    TEXT_SECONDARY, BORDER, BG_SURFACE, WARNING_FG, WARNING_BG,
)


# ── Seed data (will come from your friend's data layer eventually) ────────────
SUPPLIERS = [
    {
        "id": "SUP001", "name": "Paperline Global", "contactPerson": "Andi Cahya",
        "email": "Cahyandi@paperlineglobal.com", "phone": "+62 812-3456-7890",
        "address": "Dago", "city": "Bandung", "state": "Jawa Barat", "zipCode": "75201",
        "country": "Indonesia", "categories": ["Office Supplies"],
        "rating": 4.8, "totalOrders": 145, "totalSpent": 1_312_500_000,
        "status": "active", "paymentTerms": "Net 30", "deliveryTime": "2-3 business days",
        "notes": "Reliable supplier with consistent quality",
    },
    {
        "id": "SUP002", "name": "CV. Multi Solution Marketing", "contactPerson": "Azka Khalid",
        "email": "KhAzka@multisolutionmarketing.com", "phone": "+62 812-3456-7890",
        "address": "Cipondoj", "city": "Tangerang", "state": "Banten", "zipCode": "30301",
        "country": "Indonesia", "categories": ["Office Supplies"],
        "rating": 4.5, "totalOrders": 98, "totalSpent": 934_500_000,
        "status": "active", "paymentTerms": "Net 45", "deliveryTime": "3-5 business days",
        "notes": "Good pricing on bulk orders",
    },
    {
        "id": "SUP003", "name": "Sumber Berkat Abadi", "contactPerson": "Eka Wicaksana",
        "email": "wicak@sumberberkatabadi.com", "phone": "+62 812-3456-7890",
        "address": "Sawah Besar", "city": "Jakarta Pusat", "state": "DKI Jakarta", "zipCode": "95110",
        "country": "Indonesia", "categories": ["Electronics"],
        "rating": 4.9, "totalOrders": 76, "totalSpent": 1_881_000_000,
        "status": "active", "paymentTerms": "Net 30", "deliveryTime": "1-2 business days",
        "notes": "Excellent selection of electronics and fast shipping",
    },
    {
        "id": "SUP004", "name": "PT Indomarco", "contactPerson": "Johan Sugana",
        "email": "johSugana@indomarco.com", "phone": "+62 812-3456-7890",
        "address": "TelukJambe", "city": "Karawang Barat", "state": "Jawa Barat", "zipCode": "85001",
        "country": "Indonesia", "categories": ["Health & Safety"],
        "rating": 4.7, "totalOrders": 112, "totalSpent": 1_413_000_000,
        "status": "active", "paymentTerms": "Net 30", "deliveryTime": "2-4 business days",
        "notes": "Certified medical and safety products",
    },
    {
        "id": "SUP005", "name": "PT Bersih Jaya", "contactPerson": "Jajang",
        "email": "jajangss@bersihjaya.com", "phone": "+62 812-3456-7890",
        "address": "Cibubur", "city": "Bekasi", "state": "Jawa Barat", "zipCode": "60601",
        "country": "Indonesia", "categories": ["Cleaning Supplies"],
        "rating": 4.6, "totalOrders": 132, "totalSpent": 1_183_500_000,
        "status": "active", "paymentTerms": "Net 30", "deliveryTime": "2-3 business days",
        "notes": "Wide range of cleaning products at competitive prices",
    },
]

PAYMENT_TERMS = ["Net 15", "Net 30", "Net 45", "Net 60", "COD"]


def _fmt_idr(amount: int) -> str:
    return f"Rp {amount:,.0f}".replace(",", ".")


# ─────────────────────────── Add Supplier Dialog ──────────────────────────────

class AddSupplierDialog(QDialog):
    """Two-tab dialog: Manual input | Google Places (mock)."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add New Supplier")
        self.setFixedWidth(600)
        self.setModal(True)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        lay.addWidget(make_label("Add New Supplier", 15, bold=True))
        lay.addWidget(make_label("Add a supplier manually or find nearby via Google Places", 11, color=TEXT_SECONDARY))

        tabs = QTabWidget()
        tabs.addTab(self._manual_tab(), "Manual Input")
        tabs.addTab(self._google_tab(), "Google Places")
        lay.addWidget(tabs)

        btns = QDialogButtonBox()
        cancel = QPushButton("Cancel")
        cancel.setObjectName("btnOutline")
        save = QPushButton("Add Supplier")
        btns.addButton(cancel, QDialogButtonBox.ButtonRole.RejectRole)
        btns.addButton(save, QDialogButtonBox.ButtonRole.AcceptRole)
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self.accept)
        lay.addWidget(btns)

    # ── Manual tab ────────────────────────────────────────────────────────────

    def _manual_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(12)
        v.setContentsMargins(0, 12, 0, 0)

        grid = QGridLayout()
        grid.setSpacing(10)

        fields = [
            ("Company Name *",   "name",          0, 0),
            ("Contact Person *", "contactPerson", 0, 1),
            ("Email *",          "email",         1, 0),
            ("Phone *",          "phone",         1, 1),
            ("Address *",        "address",       2, 0),
            ("City *",           "city",          3, 0),
            ("State *",          "state",         3, 1),
            ("ZIP Code *",       "zipCode",       4, 0),
        ]
        self._fields: dict[str, QLineEdit] = {}
        for label, key, row, col in fields:
            cell = QVBoxLayout()
            cell.addWidget(make_label(label, 11, color=TEXT_SECONDARY))
            le = QLineEdit()
            le.setPlaceholderText(label.rstrip(" *"))
            self._fields[key] = le
            cell.addWidget(le)
            grid.addLayout(cell, row, col)

        # Address spans full width
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        v.addLayout(grid)

        # Payment terms + delivery
        row2 = QHBoxLayout()
        terms_col = QVBoxLayout()
        terms_col.addWidget(make_label("Payment Terms", 11, color=TEXT_SECONDARY))
        self._terms = QComboBox()
        self._terms.addItems(PAYMENT_TERMS)
        terms_col.addWidget(self._terms)
        row2.addLayout(terms_col)

        delivery_col = QVBoxLayout()
        delivery_col.addWidget(make_label("Delivery Time", 11, color=TEXT_SECONDARY))
        self._delivery = QLineEdit()
        self._delivery.setPlaceholderText("e.g., 2-3 business days")
        delivery_col.addWidget(self._delivery)
        row2.addLayout(delivery_col)
        v.addLayout(row2)

        # Notes
        notes_col = QVBoxLayout()
        notes_col.addWidget(make_label("Notes", 11, color=TEXT_SECONDARY))
        self._notes = QTextEdit()
        self._notes.setPlaceholderText("Additional notes about this supplier…")
        self._notes.setFixedHeight(72)
        notes_col.addWidget(self._notes)
        v.addLayout(notes_col)

        v.addStretch()
        return w

    # ── Google Places tab (mock) ───────────────────────────────────────────────

    def _google_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(12)
        v.setContentsMargins(0, 12, 0, 0)

        v.addWidget(make_label("Search Nearby Suppliers", 11, color=TEXT_SECONDARY))

        row = QHBoxLayout()
        self._gp_search = QLineEdit()
        self._gp_search.setPlaceholderText("e.g., 'office supplies near me'")
        row.addWidget(self._gp_search)
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self._mock_search)
        row.addWidget(search_btn)
        v.addLayout(row)

        note = QLabel("Note: This is a demo. In production this would use the Google Places API.")
        note.setStyleSheet(f"color:{TEXT_SECONDARY}; font-size:11px;")
        note.setWordWrap(True)
        v.addWidget(note)

        self._gp_results = QWidget()
        self._gp_results_lay = QVBoxLayout(self._gp_results)
        self._gp_results_lay.setSpacing(8)
        v.addWidget(self._gp_results)

        v.addStretch()
        return w

    def _mock_search(self) -> None:
        # Clear previous results
        while self._gp_results_lay.count():
            item = self._gp_results_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        mock = [
            {"name": "Metro Office Supply Co.",  "address": "456 Business Ave, Your City, ST 12345", "phone": "+1 (555) 111-2222", "rating": 4.5},
            {"name": "Wholesale Direct Inc.",     "address": "789 Commerce Blvd, Your City, ST 12346", "phone": "+1 (555) 333-4444", "rating": 4.8},
        ]
        for place in mock:
            card = QWidget()
            card.setStyleSheet(
                f"background:{BG_SURFACE}; border:1px solid {BORDER}; border-radius:8px;"
            )
            h = QHBoxLayout(card)
            h.setContentsMargins(12, 10, 12, 10)

            info = QVBoxLayout()
            info.addWidget(make_label(place["name"], 12, bold=True))
            info.addWidget(make_label(place["address"], 10, color=TEXT_SECONDARY))
            info.addWidget(make_label(f"📞 {place['phone']}  ⭐ {place['rating']}", 10, color=TEXT_SECONDARY))
            h.addLayout(info)
            h.addStretch()

            imp = QPushButton("Import")
            imp.setObjectName("btnSmall")
            imp.clicked.connect(lambda _, p=place: self._import_place(p))
            h.addWidget(imp)

            self._gp_results_lay.addWidget(card)

    def _import_place(self, place: dict) -> None:
        self._fields.get("name", QLineEdit()).setText(place["name"])
        self._fields.get("phone", QLineEdit()).setText(place["phone"])
        self._fields.get("address", QLineEdit()).setText(place["address"])
        self._notes.setPlainText("Auto-imported from Google Places")


# ─────────────────────────── Supplier Detail Dialog ──────────────────────────

class SupplierDetailDialog(QDialog):
    def __init__(self, supplier: dict, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(supplier["name"])
        self.setFixedWidth(580)
        self.setModal(True)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        # Title
        title_row = QHBoxLayout()
        title_row.addWidget(make_label(f"🏢  {supplier['name']}", 15, bold=True))
        lay.addLayout(title_row)

        lay.addWidget(h_line())

        # Two columns
        cols = QHBoxLayout()

        # Contact card
        contact = QGroupBox("Contact Information")
        contact.setStyleSheet(f"QGroupBox {{ background:{BG_SURFACE}; border:1px solid {BORDER}; border-radius:10px; }}")
        cv = QVBoxLayout(contact)
        for icon, val in [
            ("✉️", supplier["email"]),
            ("📞", supplier["phone"]),
            ("📍", f"{supplier['address']}, {supplier['city']}, {supplier['state']} {supplier['zipCode']}"),
        ]:
            row = QHBoxLayout()
            row.addWidget(make_label(icon, 12))
            lbl = make_label(val, 11, color=TEXT_SECONDARY)
            lbl.setWordWrap(True)
            row.addWidget(lbl)
            row.addStretch()
            cv.addLayout(row)
        cols.addWidget(contact)

        # Metrics card
        metrics = QGroupBox("Performance Metrics")
        metrics.setStyleSheet(f"QGroupBox {{ background:{BG_SURFACE}; border:1px solid {BORDER}; border-radius:10px; }}")
        mv = QFormLayout(metrics)
        mv.addRow(make_label("Rating", 11, color=TEXT_SECONDARY),
                  make_label(f"⭐ {supplier['rating']}", 12, bold=True))
        mv.addRow(make_label("Total Orders", 11, color=TEXT_SECONDARY),
                  make_label(str(supplier["totalOrders"]), 12, bold=True))
        mv.addRow(make_label("Total Spent", 11, color=TEXT_SECONDARY),
                  make_label(_fmt_idr(supplier["totalSpent"]), 12, bold=True))
        cols.addWidget(metrics)

        lay.addLayout(cols)

        # Business terms
        terms = QGroupBox("Business Terms")
        terms.setStyleSheet(f"QGroupBox {{ background:{BG_SURFACE}; border:1px solid {BORDER}; border-radius:10px; }}")
        tf = QFormLayout(terms)
        tf.addRow(make_label("Payment Terms", 11, color=TEXT_SECONDARY),
                  make_label(supplier["paymentTerms"], 12))
        tf.addRow(make_label("Delivery Time", 11, color=TEXT_SECONDARY),
                  make_label(supplier["deliveryTime"], 12))
        tf.addRow(make_label("Categories", 11, color=TEXT_SECONDARY),
                  make_label(", ".join(supplier["categories"]), 12))
        lay.addWidget(terms)

        # Notes
        if supplier.get("notes"):
            notes = QGroupBox("Notes")
            notes.setStyleSheet(f"QGroupBox {{ background:{BG_SURFACE}; border:1px solid {BORDER}; border-radius:10px; }}")
            nv = QVBoxLayout(notes)
            nv.addWidget(make_label(supplier["notes"], 11, color=TEXT_SECONDARY))
            lay.addWidget(notes)

        # Footer buttons
        btns = QDialogButtonBox()
        close_btn = QPushButton("Close")
        close_btn.setObjectName("btnOutline")
        edit_btn = QPushButton("Edit Supplier")
        btns.addButton(close_btn, QDialogButtonBox.ButtonRole.RejectRole)
        btns.addButton(edit_btn, QDialogButtonBox.ButtonRole.AcceptRole)
        close_btn.clicked.connect(self.reject)
        edit_btn.clicked.connect(self.accept)
        lay.addWidget(btns)


# ─────────────────────────── Suppliers Page ──────────────────────────────────

class SuppliersPage(QWidget):
    """Supplier management: directory table, add dialog, detail view."""

    status_msg = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._suppliers = list(SUPPLIERS)  # local copy (add would append here)

        lay = QVBoxLayout(self)
        lay.setSpacing(16)
        lay.setContentsMargins(0, 0, 0, 0)

        lay.addLayout(self._build_header())
        lay.addLayout(self._build_stats())
        lay.addLayout(self._build_controls())
        lay.addWidget(self._build_table())

        self._refresh()

    # ── Sections ──────────────────────────────────────────────────────────────

    def _build_header(self) -> QHBoxLayout:
        hdr = QHBoxLayout()

        info = QVBoxLayout()
        info.addWidget(make_label("Supplier Management", 18, bold=True))
        info.addWidget(make_label("Manage suppliers and vendor relationships", 12, color=TEXT_SECONDARY))
        hdr.addLayout(info)
        hdr.addStretch()

        add_btn = QPushButton("+ Add Supplier")
        add_btn.clicked.connect(self._open_add_dialog)
        hdr.addWidget(add_btn)

        return hdr

    def _build_stats(self) -> QHBoxLayout:
        active = sum(1 for s in self._suppliers if s["status"] == "active")
        avg_rating = sum(s["rating"] for s in self._suppliers) / len(self._suppliers)
        total_spent = sum(s["totalSpent"] for s in self._suppliers)
        all_cats = set(c for s in self._suppliers for c in s["categories"])

        row = QHBoxLayout()
        for title, val, sub in [
            ("Active Suppliers", str(active),              f"of {len(self._suppliers)} total"),
            ("Avg Rating",       f"⭐ {avg_rating:.1f}",   "Based on performance"),
            ("Total Spent",      _fmt_idr(total_spent),    "All-time purchases"),
            ("Categories",       str(len(all_cats)),       "Product categories"),
        ]:
            card = QWidget()
            card.setStyleSheet(card_style())
            cv = QVBoxLayout(card)
            cv.addWidget(make_label(title, 11, color=TEXT_SECONDARY))
            cv.addWidget(make_label(val, 18, bold=True))
            cv.addWidget(make_label(sub, 10, color=TEXT_SECONDARY))
            row.addWidget(card)
        return row

    def _build_controls(self) -> QHBoxLayout:
        ctrl = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  Search by name, contact, category…")
        self.search.textChanged.connect(self._refresh)
        ctrl.addWidget(self.search)
        return ctrl

    def _build_table(self) -> QTableWidget:
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["Supplier", "Contact", "Categories", "Rating", "Orders", "Total Spent", "Status"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.cellDoubleClicked.connect(self._open_detail)
        self.table.setToolTip("Double-click a row to view supplier details")
        return self.table

    # ── Data ─────────────────────────────────────────────────────────────────

    def _filtered(self) -> list[dict]:
        q = self.search.text().lower()
        if not q:
            return self._suppliers
        return [
            s for s in self._suppliers
            if q in s["name"].lower()
            or q in s["contactPerson"].lower()
            or any(q in c.lower() for c in s["categories"])
        ]

    def _refresh(self) -> None:
        rows = self._filtered()
        self.table.setRowCount(len(rows))
        for r, s in enumerate(rows):
            # Supplier name + location
            name_widget = QWidget()
            nv = QVBoxLayout(name_widget)
            nv.setContentsMargins(8, 4, 8, 4)
            nv.addWidget(make_label(s["name"], 12, bold=True))
            nv.addWidget(make_label(f"📍 {s['city']}, {s['state']}", 10, color=TEXT_SECONDARY))
            self.table.setCellWidget(r, 0, name_widget)

            # Contact
            contact_widget = QWidget()
            cv = QVBoxLayout(contact_widget)
            cv.setContentsMargins(8, 4, 8, 4)
            cv.addWidget(make_label(s["contactPerson"], 11))
            cv.addWidget(make_label(f"✉️ {s['email']}", 10, color=TEXT_SECONDARY))
            self.table.setCellWidget(r, 1, contact_widget)

            # Categories
            self.table.setItem(r, 2, QTableWidgetItem(", ".join(s["categories"])))

            # Rating
            self.table.setItem(r, 3, QTableWidgetItem(f"⭐ {s['rating']}"))

            # Orders
            self.table.setItem(r, 4, QTableWidgetItem(str(s["totalOrders"])))

            # Spent
            self.table.setItem(r, 5, QTableWidgetItem(_fmt_idr(s["totalSpent"])))

            # Status badge
            status_item = QTableWidgetItem(s["status"].capitalize())
            if s["status"] == "active":
                status_item.setForeground(QColor(SUCCESS_FG))
                status_item.setBackground(QColor(SUCCESS_BG))
            else:
                status_item.setForeground(QColor(TEXT_SECONDARY))
            self.table.setItem(r, 6, status_item)

        self.table.resizeRowsToContents()

    # ── Dialogs ───────────────────────────────────────────────────────────────

    def _open_add_dialog(self) -> None:
        dlg = AddSupplierDialog(self)
        if dlg.exec():
            self.status_msg.emit("Supplier added successfully!")

    def _open_detail(self, row: int, _: int) -> None:
        rows = self._filtered()
        if row >= len(rows):
            return
        dlg = SupplierDetailDialog(rows[row], self)
        if dlg.exec():
            self.status_msg.emit(f"Edit supplier: {rows[row]['name']} (coming soon)")
