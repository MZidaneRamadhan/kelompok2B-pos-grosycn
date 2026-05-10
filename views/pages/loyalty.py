# ─────────────────────────────────────────────────────────────────────────────
# views/pages/loyalty.py
# ─────────────────────────────────────────────────────────────────────────────

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QTabWidget, QDialog, QFormLayout, QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from views.styles.theme_manager import make_label, h_line, card_style, tier_badge_style
from views.styles.palettes import PRIMARY, PRIMARY_LIGHT, BORDER, BG_SURFACE, tier_fg, tier_bg
from data.store import REWARDS  # Removed CUSTOMERS since we will fetch from DB now

# Import your controller and model
from controllers import loyalty_controller
from models import loyalty_model

class LoyaltyPage(QWidget):
    """Customer loyalty program: member table, customer detail modal, rewards catalog."""

    status_msg = pyqtSignal(str)

    def __init__(self, auth_token: str = "", parent=None) -> None: # Tambahkan auth_token
        super().__init__(parent)
        self.auth_token = auth_token
        lay = QVBoxLayout(self)
        lay.setSpacing(16)
        lay.setContentsMargins(0, 0, 0, 0)

        lay.addLayout(self._build_header())
        lay.addLayout(self._build_stats())

        tabs = QTabWidget()
        tabs.addTab(self._build_customers_tab(), "Customers")
        tabs.addTab(self._build_rewards_tab(), "Rewards Catalog")
        lay.addWidget(tabs)

    # ── Sections ──────────────────────────────────────────────────────────────

    def _build_header(self) -> QHBoxLayout:
        hdr = QHBoxLayout()

        info = QVBoxLayout()
        info.addWidget(make_label("Loyalty Program", 18, bold=True))
        info.addWidget(make_label("Manage customer rewards and loyalty points", 12, color="#64748b"))
        hdr.addLayout(info)
        hdr.addStretch()

        new_btn = QPushButton("🎁  New Reward")
        new_btn.clicked.connect(lambda: self.status_msg.emit("New Reward feature coming soon"))
        hdr.addWidget(new_btn)

        return hdr

    def _build_stats(self) -> QHBoxLayout:
        all_members = loyalty_model.get_all_members()
        active_members = [m for m in all_members if m.get("is_active", True)]
        
        total_pts = sum(c["points"] for c in active_members)
        total_spent = sum(c["spent"] for c in active_members)

        row = QHBoxLayout()
        for title, val in [
            ("Total Members",  str(len(active_members))),
            ("Points Issued",  f"{total_pts:,}"),
            ("Total Spent",    f"${total_spent:,.2f}"),
            ("Active Rewards", str(len(REWARDS))),
        ]:
            card = QWidget()
            card.setStyleSheet(card_style())
            cv = QVBoxLayout(card)
            cv.addWidget(make_label(title, 11, color="#64748b"))
            cv.addWidget(make_label(val, 18, bold=True))
            row.addWidget(card)
        return row

    # ── Customers tab ─────────────────────────────────────────────────────────

    def _build_customers_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(10)

        # Toolbar: Search + Add Button
        toolbar = QHBoxLayout()
        self.cust_search = QLineEdit()
        self.cust_search.setPlaceholderText("🔍  Search customers…")
        self.cust_search.textChanged.connect(self._refresh_customers)
        toolbar.addWidget(self.cust_search)

        add_btn = QPushButton("➕ Add Member")
        add_btn.setStyleSheet("background-color: #4f46e5; color: white; padding: 6px 12px; border-radius: 4px;")
        add_btn.clicked.connect(self._show_add_member_dialog)
        toolbar.addWidget(add_btn)
        
        v.addLayout(toolbar)

        self.cust_table = QTableWidget()
        self.cust_table.setColumnCount(7)
        self.cust_table.setHorizontalHeaderLabels(
            ["Name", "Email", "Phone", "Tier", "Points", "Total Spent", "Visits"]
        )
        self.cust_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.cust_table.setAlternatingRowColors(True)
        self.cust_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.cust_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.cust_table.cellDoubleClicked.connect(self._show_customer_detail)
        v.addWidget(self.cust_table)

        self._refresh_customers()
        return w

    def _refresh_customers(self) -> None:
        q = self.cust_search.text().lower() if hasattr(self, "cust_search") else ""
        
        # Fetch directly from the DB model
        all_members = loyalty_model.get_all_members()
        active_members = [m for m in all_members if m.get("is_active", True)]
        
        rows = (
            [c for c in active_members if q in c["name"].lower() or q in c.get("email", "").lower()]
            if q else active_members
        )

        self.cust_table.setRowCount(len(rows))
        
        # Keep track of the actual data in a hidden way or parallel list, 
        # but storing the raw data attached to the table is easier.
        self._current_table_data = rows 
        
        for r, c in enumerate(rows):
            self.cust_table.setItem(r, 0, QTableWidgetItem(c["name"]))
            self.cust_table.setItem(r, 1, QTableWidgetItem(c.get("email", "")))
            self.cust_table.setItem(r, 2, QTableWidgetItem(c.get("phone", "")))

            tier_item = QTableWidgetItem(c["tier"])
            tier_item.setForeground(QColor(tier_fg(c["tier"])))
            self.cust_table.setItem(r, 3, tier_item)

            self.cust_table.setItem(r, 4, QTableWidgetItem(f"{c['points']:,}"))
            self.cust_table.setItem(r, 5, QTableWidgetItem(f"${c['spent']:.2f}"))
            self.cust_table.setItem(r, 6, QTableWidgetItem(str(c["visits"])))

    def _show_customer_detail(self, row: int, _: int) -> None:
        c = self._current_table_data[row]

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Customer: {c['name']}")
        dlg.setFixedWidth(380)

        v = QVBoxLayout(dlg)
        v.setSpacing(10)
        v.setContentsMargins(20, 20, 20, 20)

        # Avatar
        initials = "".join(n[0] for n in c["name"].split() if n)
        if not initials: initials = "?"
        
        av = QLabel(initials[:2].upper())
        av.setFixedSize(56, 56)
        av.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fg, bg = tier_fg(c["tier"]), tier_bg(c["tier"])
        av.setStyleSheet(
            f"background:{bg}; color:{fg}; border-radius:28px; font-size:20px; font-weight:bold;"
        )
        v.addWidget(av, alignment=Qt.AlignmentFlag.AlignHCenter)

        v.addWidget(make_label(c["name"], 16, bold=True), alignment=Qt.AlignmentFlag.AlignHCenter)

        tier_lbl = QLabel(c["tier"])
        tier_lbl.setStyleSheet(tier_badge_style(fg, bg) + " padding:4px 12px;")
        tier_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(tier_lbl)

        v.addWidget(h_line())

        form = QFormLayout()
        for label, val in [
            ("Email",        c.get("email", "-")),
            ("Phone",        c.get("phone", "-")),
            ("Points",       f"{c['points']:,}"),
            ("Total Spent",  f"${c['spent']:.2f}"),
            ("Visits",       str(c["visits"])),
            ("Member Since", c.get("join", "-")),
        ]:
            form.addRow(make_label(label, 11, color="#64748b"), make_label(val, 12))
        v.addLayout(form)

        v.addWidget(make_label("Tier Progress", 11, color="#64748b"))
        prog = QProgressBar()
        prog.setValue({"Bronze": 25, "Silver": 50, "Gold": 75, "Platinum": 100}.get(c["tier"], 25))
        prog.setFixedHeight(8)
        v.addWidget(prog)

        # Action Buttons
        btn_layout = QHBoxLayout()
        
        edit_btn = QPushButton("Edit")
        edit_btn.clicked.connect(lambda: self._show_edit_member_dialog(c, dlg))
        
        delete_btn = QPushButton("Delete")
        delete_btn.setStyleSheet("color: #ef4444;") 
        delete_btn.clicked.connect(lambda: self._delete_member(c, dlg))
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dlg.accept)

        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(delete_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        
        v.addLayout(btn_layout)

        dlg.exec()

    # ── CRUD Actions ─────────────────────────────────────────────────────────

    def _show_add_member_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Add New Member")
        dlg.setFixedWidth(300)
        lay = QVBoxLayout(dlg)

        form = QFormLayout()
        name_input = QLineEdit()
        email_input = QLineEdit()
        phone_input = QLineEdit()

        form.addRow("Name *:", name_input)
        form.addRow("Email:", email_input)
        form.addRow("Phone *:", phone_input)
        lay.addLayout(form)

        btn_box = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        btn_box.addWidget(save_btn)
        btn_box.addWidget(cancel_btn)
        lay.addLayout(btn_box)

        cancel_btn.clicked.connect(dlg.reject)

        def save_member():
            try:
                loyalty_controller.create_member(
                    auth_token=self.auth_token, 
                    member_name=name_input.text(), 
                    email=email_input.text(), 
                    phone_number=phone_input.text()
                )
                self.status_msg.emit(f"Member {name_input.text()} added successfully!")
                self._refresh_customers()
                dlg.accept()
            except ValueError as e:
                QMessageBox.warning(dlg, "Error", str(e))
            except Exception as e:
                QMessageBox.critical(dlg, "System Error", f"An unexpected error occurred: {str(e)}")

        save_btn.clicked.connect(save_member)
        dlg.exec()

    def _show_edit_member_dialog(self, customer_data: dict, parent_dlg: QDialog):
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Edit Member: {customer_data['name']}")
        dlg.setFixedWidth(300)
        lay = QVBoxLayout(dlg)

        form = QFormLayout()
        name_input = QLineEdit(customer_data.get("name", ""))
        email_input = QLineEdit(customer_data.get("email", ""))
        phone_input = QLineEdit(customer_data.get("phone", ""))

        form.addRow("Name *:", name_input)
        form.addRow("Email:", email_input)
        form.addRow("Phone *:", phone_input)
        lay.addLayout(form)

        btn_box = QHBoxLayout()
        save_btn = QPushButton("Save Changes")
        cancel_btn = QPushButton("Cancel")
        btn_box.addWidget(save_btn)
        btn_box.addWidget(cancel_btn)
        lay.addLayout(btn_box)

        cancel_btn.clicked.connect(dlg.reject)

        def update_member():
            try:
                loyalty_controller.update_member(
                    auth_token=self.auth_token,
                    member_id=customer_data.get("id", ""), 
                    member_name=name_input.text(),
                    email=email_input.text(),
                    phone_number=phone_input.text()
                )
                self.status_msg.emit("Member updated successfully!")
                self._refresh_customers()
                dlg.accept()
                parent_dlg.accept() 
            except ValueError as e:
                QMessageBox.warning(dlg, "Error", str(e))
            except Exception as e:
                QMessageBox.critical(dlg, "System Error", f"An unexpected error occurred: {str(e)}")

        save_btn.clicked.connect(update_member)
        dlg.exec()

    def _delete_member(self, customer_data: dict, parent_dlg: QDialog):
        confirm = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to remove {customer_data['name']}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                loyalty_controller.delete_member(
                    auth_token=self.auth_token, 
                    member_id=customer_data.get("id", "")
                )
                self.status_msg.emit(f"Member {customer_data['name']} deleted.")
                self._refresh_customers()
                parent_dlg.accept()
            except ValueError as e:
                QMessageBox.warning(self, "Error", str(e))
            except Exception as e:
                QMessageBox.critical(self, "System Error", f"An unexpected error occurred: {str(e)}")


    # ── Rewards tab ───────────────────────────────────────────────────────────

    def _build_rewards_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(10)

        for rw in REWARDS:
            card = QWidget()
            card.setStyleSheet(
                f"background:{BG_SURFACE}; border:1px solid {BORDER}; border-radius:10px; padding:14px;"
            )
            row = QHBoxLayout(card)

            info = QVBoxLayout()
            info.addWidget(make_label(rw["name"], 13, bold=True))
            info.addWidget(make_label(rw["desc"], 11, color="#64748b"))

            cat_lbl = QLabel(rw["cat"])
            cat_lbl.setStyleSheet(
                f"background:{PRIMARY_LIGHT}; color:{PRIMARY}; border-radius:6px; "
                f"padding:2px 8px; font-size:11px; font-weight:600; margin-top:4px;"
            )
            info.addWidget(cat_lbl)
            row.addLayout(info)
            row.addStretch()

            pts_col = QVBoxLayout()
            pts_col.addWidget(
                make_label(str(rw["cost"]), 18, bold=True, color=PRIMARY),
                alignment=Qt.AlignmentFlag.AlignCenter,
            )
            pts_col.addWidget(
                make_label("points", 10, color="#64748b"),
                alignment=Qt.AlignmentFlag.AlignCenter,
            )
            redeem_btn = QPushButton("Redeem")
            redeem_btn.setObjectName("btnSmall")
            redeem_btn.clicked.connect(
                lambda _, r=rw: self.status_msg.emit(f"Redeemed: {r['name']}")
            )
            pts_col.addWidget(redeem_btn)
            row.addLayout(pts_col)

            v.addWidget(card)

        v.addStretch()
        return w