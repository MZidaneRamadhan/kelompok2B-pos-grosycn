# ─────────────────────────────────────────────────────────────────────────────
# views/pages/user_management.py
#
# Admin-only page for managing employee accounts (CRUD).
# Requires auth_token with role_id=1 (Admin / manajemen_user permission).
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from views.styles.palettes import (
    BG_SURFACE, BORDER, DANGER_BG, DANGER_BORDER, DANGER_FG,
    PRIMARY, PRIMARY_LIGHT, SUCCESS_BG, SUCCESS_FG,
    TEXT_PRIMARY, TEXT_SECONDARY, WARNING_BG, WARNING_FG, WARNING_BORDER,
)
from views.styles.theme_manager import make_label

ROLE_OPTIONS = [
    ("Admin",        1),
    ("Kasir",        2),
    ("Stok Manager", 3),
]
ROLE_LABEL = {r: lbl for lbl, r in ROLE_OPTIONS}


# ─────────────────────────────────────────────────────────────────────────────
# UserFormDialog – add or edit a single user
# ─────────────────────────────────────────────────────────────────────────────

class UserFormDialog(QDialog):
    """
    Modal form for creating or editing a user.

    Pass `user` dict to pre-fill fields for editing; omit (None) for creation.
    """

    def __init__(
        self,
        auth_token: str,
        user: dict | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._auth_token = auth_token
        self._user = user
        self._editing = user is not None

        self.setWindowTitle("Edit User" if self._editing else "Add User")
        self.setModal(True)
        self.setFixedWidth(420)
        self.setSizeGripEnabled(False)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 28, 28, 28)
        lay.setSpacing(14)

        title_text = "Edit Account" if self._editing else "Add New Account"
        lay.addWidget(make_label(title_text, 16, bold=True))

        # Full name
        lay.addWidget(self._lbl("Nama Lengkap"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. Budi Santoso")
        self.name_input.setStyleSheet(self._input_css())
        lay.addWidget(self.name_input)

        # Email
        lay.addWidget(self._lbl("Email"))
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("you@example.com")
        self.email_input.setStyleSheet(self._input_css())
        lay.addWidget(self.email_input)

        # Role
        lay.addWidget(self._lbl("Role"))
        self.role_combo = QComboBox()
        for label, _ in ROLE_OPTIONS:
            self.role_combo.addItem(label)
        self.role_combo.setStyleSheet(
            f"QComboBox {{ border:1px solid {BORDER}; border-radius:8px;"
            f" padding:9px 12px; font-size:13px; background:{BG_SURFACE}; color:{TEXT_PRIMARY};}}"
            f"QComboBox::drop-down {{ border:none; }}"
            f"QComboBox QAbstractItemView {{ border:1px solid {BORDER}; border-radius:6px;"
            f" background:{BG_SURFACE}; selection-background-color:{PRIMARY_LIGHT};}}"
        )
        lay.addWidget(self.role_combo)

        # Password section (always shown for new, optional for edit)
        if self._editing:
            pw_note = QLabel("Leave the password blank if you don't want to change it.")
            pw_note.setStyleSheet(
                f"color:{TEXT_SECONDARY}; font-size:11px; background:transparent; border:none;"
            )
            lay.addWidget(pw_note)

        lay.addWidget(self._lbl("Password" + (" New" if self._editing else "")))
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Min. 8 characters")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setStyleSheet(self._input_css())
        lay.addWidget(self.password_input)

        if not self._editing:
            lay.addWidget(self._lbl("Confirm Password"))
            self.confirm_input = QLineEdit()
            self.confirm_input.setPlaceholderText("Repeat password")
            self.confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.confirm_input.setStyleSheet(self._input_css())
            lay.addWidget(self.confirm_input)
        else:
            self.confirm_input = None  # not needed for edit

        # Show password toggle
        self.show_pw = QCheckBox("Show password")
        self.show_pw.setStyleSheet(
            f"color:{TEXT_SECONDARY}; font-size:12px; border:none; background:transparent;"
        )
        self.show_pw.toggled.connect(self._toggle_echo)
        lay.addWidget(self.show_pw)

        # Feedback label
        self._feedback = QLabel("")
        self._feedback.setWordWrap(True)
        self._feedback.setStyleSheet(
            f"color:{DANGER_FG}; font-size:12px; border:none; background:transparent;"
        )
        self._feedback.hide()
        lay.addWidget(self._feedback)

        # Buttons
        btn_row = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(
            f"QPushButton {{ border:1px solid {BORDER}; border-radius:8px;"
            f" padding:9px 20px; font-size:13px; background:{BG_SURFACE}; color:{TEXT_PRIMARY};}}"
            f"QPushButton:hover {{ background:#f1f5f9; }}"
        )
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        self.save_btn = QPushButton("Save")
        self.save_btn.setStyleSheet(
            f"QPushButton {{ background:{PRIMARY}; color:#fff; border:none; border-radius:8px;"
            f" padding:9px 20px; font-size:13px; font-weight:600;}}"
            f"QPushButton:hover {{ background:#4338ca; }}"
            f"QPushButton:pressed {{ background:#3730a3; }}"
        )
        self.save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(self.save_btn)
        lay.addLayout(btn_row)

        # Pre-fill for editing
        if self._editing:
            self.name_input.setText(user.get("name", ""))
            self.email_input.setText(user.get("email", ""))
            role_id = int(user.get("role_id", 2))
            idx = next((i for i, (_, r) in enumerate(ROLE_OPTIONS) if r == role_id), 0)
            self.role_combo.setCurrentIndex(idx)

    # ── Private ───────────────────────────────────────────────────────────────

    def _lbl(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color:{TEXT_PRIMARY}; font-size:12px; font-weight:600;"
            f"border:none; background:transparent;"
        )
        return lbl

    def _input_css(self) -> str:
        return (
            f"QLineEdit {{ border:1px solid {BORDER}; border-radius:8px;"
            f" padding:9px 12px; font-size:13px; background:{BG_SURFACE}; color:{TEXT_PRIMARY};}}"
            f"QLineEdit:focus {{ border-color:{PRIMARY}; }}"
        )

    def _toggle_echo(self, checked: bool) -> None:
        mode = QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        self.password_input.setEchoMode(mode)
        if self.confirm_input:
            self.confirm_input.setEchoMode(mode)

    def _show_error(self, msg: str) -> None:
        self._feedback.setStyleSheet(
            f"color:{DANGER_FG}; font-size:12px; border:none; background:transparent;"
        )
        self._feedback.setText(msg)
        self._feedback.show()

    def _on_save(self) -> None:
        from controllers import user_controller

        name    = self.name_input.text().strip()
        email   = self.email_input.text().strip()
        role_id = ROLE_OPTIONS[self.role_combo.currentIndex()][1]
        password = self.password_input.text()

        self._feedback.hide()

        try:
            if self._editing:
                # Update profile (name / email / role)
                user_controller.update_user(
                    self._auth_token,
                    self._user["id"],
                    name, email, role_id,
                )
                # Optionally update password if provided
                if password:
                    if len(password) < 8:
                        self._show_error("New password must be at least 8 characters.")
                        return
                    # update_password expects old_password; admin resets directly via model
                    from models import user_model
                    import hashlib
                    hashed = hashlib.sha256(password.encode()).hexdigest()
                    user_model.update_password(self._user["id"], hashed)
            else:
                confirm = self.confirm_input.text() if self.confirm_input else ""
                if password != confirm:
                    self._show_error("Confirm password does not match.")
                    return
                user_controller.create_user(
                    self._auth_token, name, email, password, role_id
                )

            self.accept()

        except (ValueError, PermissionError) as exc:
            self._show_error(str(exc))


# ─────────────────────────────────────────────────────────────────────────────
# UserManagementPage
# ─────────────────────────────────────────────────────────────────────────────

class UserManagementPage(QWidget):
    """
    Full-page employee management view (Admin only).
    Call set_auth_token(token) before the page is first shown.
    """

    status_msg = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._auth_token: str = ""
        self._build_ui()

    def set_auth_token(self, token: str) -> None:
        self._auth_token = token

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        lay = QVBoxLayout(self)
        lay.setSpacing(16)
        lay.setContentsMargins(0, 0, 0, 0)

        # Header row
        hdr = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.addWidget(make_label("User Management", 20, bold=True))
        title_col.addWidget(make_label("Manage employee accounts & access permission", 12, color=TEXT_SECONDARY))
        hdr.addLayout(title_col)
        hdr.addStretch()

        self.add_btn = QPushButton("+ Add User")
        self.add_btn.setFixedHeight(38)
        self.add_btn.setStyleSheet(
            f"QPushButton {{ background:{PRIMARY}; color:#fff; border:none; border-radius:8px;"
            f" padding:0 20px; font-size:13px; font-weight:600;}}"
            f"QPushButton:hover {{ background:#4338ca; }}"
        )
        self.add_btn.clicked.connect(self._on_add)
        hdr.addWidget(self.add_btn)
        lay.addLayout(hdr)

        # Search bar
        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍  Search for name or email…")
        self.search_input.setFixedHeight(38)
        self.search_input.setStyleSheet(
            f"QLineEdit {{ border:1px solid {BORDER}; border-radius:8px;"
            f" padding:0 12px; font-size:13px; background:{BG_SURFACE}; color:{TEXT_PRIMARY};}}"
            f"QLineEdit:focus {{ border-color:{PRIMARY}; }}"
        )
        self.search_input.textChanged.connect(self._filter_table)
        search_row.addWidget(self.search_input)
        lay.addLayout(search_row)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Nama", "Email", "Role", "Status", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 160)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet(
            f"QTableWidget {{ border:1px solid {BORDER}; border-radius:10px;"
            f" background:{BG_SURFACE}; gridline-color:{BORDER}; font-size:13px;}}"
            f"QHeaderView::section {{ background:#f8fafc; border:none; border-bottom:1px solid {BORDER};"
            f" padding:10px; font-weight:600; color:{TEXT_PRIMARY};}}"
            f"QTableWidget::item {{ padding:8px; }}"
        )
        lay.addWidget(self.table)

        self._all_users: list[dict] = []

    # ── Data ──────────────────────────────────────────────────────────────────

    def refresh_data(self) -> None:
        """Reload user list from the model. Called by MainWindow on page switch."""
        try:
            from controllers import user_controller
            # get_all_users only returns active users via controller
            # We want all users (incl inactive) for admin view, read from model directly
            from models import user_model
            self._all_users = user_model.get_all_users()
        except Exception as e:
            self._all_users = []
            self.status_msg.emit(f"Failed to load user data: {e}")
        self._populate_table(self._all_users)

    def _filter_table(self, query: str) -> None:
        q = query.lower()
        filtered = [
            u for u in self._all_users
            if q in u.get("name", "").lower() or q in u.get("email", "").lower()
        ] if q else self._all_users
        self._populate_table(filtered)

    def _populate_table(self, users: list[dict]) -> None:
        self.table.setRowCount(0)
        for user in users:
            row = self.table.rowCount()
            self.table.insertRow(row)

            self.table.setItem(row, 0, QTableWidgetItem(user.get("name", "—")))
            self.table.setItem(row, 1, QTableWidgetItem(user.get("email", "—")))

            role_id  = int(user.get("role_id", 0))
            role_lbl = ROLE_LABEL.get(role_id, f"Role {role_id}")
            self.table.setItem(row, 2, QTableWidgetItem(role_lbl))

            is_active = user.get("is_active", True)
            status_item = QTableWidgetItem("Active" if is_active else "Non-active")
            status_item.setForeground(
                __import__("PyQt6.QtGui", fromlist=["QColor"]).QColor(
                    SUCCESS_FG if is_active else DANGER_FG
                )
            )
            self.table.setItem(row, 3, status_item)

            # Action buttons cell
            cell = QWidget()
            cell_lay = QHBoxLayout(cell)
            cell_lay.setContentsMargins(4, 2, 4, 2)
            cell_lay.setSpacing(6)

            edit_btn = QPushButton("Edit")
            edit_btn.setFixedHeight(28)
            edit_btn.setStyleSheet(
                f"QPushButton {{ background:{PRIMARY_LIGHT}; color:{PRIMARY}; border:none;"
                f" border-radius:6px; padding:0 12px; font-size:12px; font-weight:600;}}"
                f"QPushButton:hover {{ background:#c7d2fe; }}"
            )
            edit_btn.clicked.connect(lambda _, u=user: self._on_edit(u))
            cell_lay.addWidget(edit_btn)

            if is_active:
                deact_btn = QPushButton("Deactivate")
                deact_btn.setFixedHeight(28)
                deact_btn.setStyleSheet(
                    f"QPushButton {{ background:{DANGER_BG}; color:{DANGER_FG};"
                    f" border:1px solid {DANGER_BORDER}; border-radius:6px;"
                    f" padding:0 10px; font-size:12px; font-weight:600;}}"
                    f"QPushButton:hover {{ background:#fecaca; }}"
                )
                deact_btn.clicked.connect(lambda _, u=user: self._on_deactivate(u))
                cell_lay.addWidget(deact_btn)
            else:
                react_btn = QPushButton("Activate")
                react_btn.setFixedHeight(28)
                react_btn.setStyleSheet(
                    f"QPushButton {{ background:{SUCCESS_BG}; color:{SUCCESS_FG};"
                    f" border:none; border-radius:6px;"
                    f" padding:0 10px; font-size:12px; font-weight:600;}}"
                    f"QPushButton:hover {{ background:#a7f3d0; }}"
                )
                react_btn.clicked.connect(lambda _, u=user: self._on_reactivate(u))
                cell_lay.addWidget(react_btn)

            self.table.setCellWidget(row, 4, cell)
            self.table.setRowHeight(row, 48)

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_add(self) -> None:
        dlg = UserFormDialog(self._auth_token, user=None, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.status_msg.emit("New user successfully added.")
            self.refresh_data()

    def _on_edit(self, user: dict) -> None:
        dlg = UserFormDialog(self._auth_token, user=user, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.status_msg.emit(f"Account '{user.get('name')}' updated successfully.")
            self.refresh_data()

    def _on_deactivate(self, user: dict) -> None:
        reply = QMessageBox.question(
            self, "Disable User",
            f"Disable account '{user.get('name')}'?\nUser cannot login after this.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            from controllers import user_controller
            user_controller.delete_user(self._auth_token, user["id"])
            self.status_msg.emit(f"Account '{user.get('name')}' is disabled.")
            self.refresh_data()
        except (ValueError, PermissionError) as e:
            QMessageBox.warning(self, "Gagal", str(e))

    def _on_reactivate(self, user: dict) -> None:
        """Re-activate a soft-deleted user directly via model (no controller method for this)."""
        from models import user_model
        users = user_model.get_all_users()
        for u in users:
            if u["id"] == user["id"]:
                u["is_active"] = True
                break
        user_model._save(users)
        self.status_msg.emit(f"Account '{user.get('name')}' reactivated.")
        self.refresh_data()