# ─────────────────────────────────────────────────────────────────────────────
# views/pages/register.py
#
# RegisterWidget  – standalone form (embed anywhere)
# RegisterDialog  – modal wrapper used by LoginDialog
#
# Bootstrap logic:
#   • If data/users.json is empty / missing → first-run mode.
#     The new account is automatically assigned role_id=1 (Admin).
#   • Otherwise only an already-authenticated Admin should call this.
#     In that case pass `auth_token` to RegisterDialog; the controller's
#     @requires_permission("manajemen_user") decorator guards the call.
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget,
)

from views.styles.palettes import (
    BG_APP, BG_SURFACE, BORDER, DANGER_FG,
    PRIMARY, PRIMARY_LIGHT, SUCCESS_FG,
    TEXT_PRIMARY, TEXT_SECONDARY,
)

# Role map shown in the combo-box.
# On first-run the combo is hidden and Admin (1) is used automatically.
ROLE_OPTIONS = [
    ("Admin",         1),
    ("Kasir",         2),
    ("Stok Manager",  3),
]

_USERS_PATH = Path("data/users.json")


def _no_users_exist() -> bool:
    """Return True when the users store is absent or empty → bootstrap mode."""
    if not _USERS_PATH.exists():
        return True
    try:
        data = json.loads(_USERS_PATH.read_text())
        # Consider only active accounts
        return not any(u.get("is_active", True) for u in data)
    except (json.JSONDecodeError, TypeError):
        return True


def _hash(plain: str) -> str:
    return hashlib.sha256(plain.encode()).hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# RegisterWidget
# ─────────────────────────────────────────────────────────────────────────────

class RegisterWidget(QWidget):
    """
    Standalone registration form.

    Signals
    -------
    register_requested(name, email, password, role_id)
        Emitted when the user clicks "Create account" and basic client-side
        validation passes.  The caller (controller / dialog) does the actual
        DB write and calls show_error() / show_success() on the result.

    back_requested()
        Emitted when the user clicks "Back to sign in".
    """

    register_requested = pyqtSignal(str, str, str, int)
    back_requested = pyqtSignal()

    def __init__(self, show_role: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._show_role = show_role
        self.setStyleSheet(f"background: {BG_APP};")
        self._build_ui()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addStretch()

        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(self._build_card())
        row.addStretch()

        outer.addLayout(row)
        outer.addStretch()

    def _build_card(self) -> QWidget:
        card = QWidget()
        card.setFixedWidth(420)
        card.setStyleSheet(
            f"QWidget {{"
            f"  background: {BG_SURFACE};"
            f"  border: 1px solid {BORDER};"
            f"  border-radius: 14px;"
            f"}}"
        )

        lay = QVBoxLayout(card)
        lay.setContentsMargins(32, 32, 32, 32)
        lay.setSpacing(0)

        # ── Brand mark ───────────────────────────────────────────────────────
        icon_row = QHBoxLayout()
        icon_lbl = QLabel("🛒")
        icon_lbl.setStyleSheet(
            f"background: {PRIMARY}; border: none; border-radius: 10px;"
            f"font-size: 20px; padding: 8px;"
        )
        icon_lbl.setFixedSize(44, 44)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_row.addWidget(icon_lbl)
        icon_row.addStretch()
        lay.addLayout(icon_row)

        lay.addSpacing(20)

        # ── Title ─────────────────────────────────────────────────────────────
        title = QLabel("Create an account")
        title.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 20px; font-weight: 700;"
            f"border: none; background: transparent;"
        )
        lay.addWidget(title)

        lay.addSpacing(6)

        subtitle_text = (
            "Set up the first Admin account to get started."
            if not self._show_role
            else "Fill in the details to add a new team member."
        )
        subtitle = QLabel(subtitle_text)
        subtitle.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 12px;"
            f"border: none; background: transparent;"
        )
        subtitle.setWordWrap(True)
        lay.addWidget(subtitle)

        lay.addSpacing(24)

        # ── Full name ─────────────────────────────────────────────────────────
        lay.addWidget(self._label("Full name"))
        lay.addSpacing(6)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. Budi Santoso")
        self.name_input.setClearButtonEnabled(True)
        self.name_input.setStyleSheet(self._input_style())
        self.name_input.textChanged.connect(self._sync_button)
        lay.addWidget(self.name_input)

        lay.addSpacing(14)

        # ── Email ─────────────────────────────────────────────────────────────
        lay.addWidget(self._label("Email"))
        lay.addSpacing(6)
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("you@example.com")
        self.email_input.setClearButtonEnabled(True)
        self.email_input.setStyleSheet(self._input_style())
        self.email_input.textChanged.connect(self._sync_button)
        lay.addWidget(self.email_input)

        lay.addSpacing(14)

        # ── Password ──────────────────────────────────────────────────────────
        lay.addWidget(self._label("Password"))
        lay.addSpacing(6)
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Min. 8 characters")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setClearButtonEnabled(True)
        self.password_input.setStyleSheet(self._input_style())
        self.password_input.textChanged.connect(self._sync_button)
        lay.addWidget(self.password_input)

        lay.addSpacing(14)

        # ── Confirm password ──────────────────────────────────────────────────
        lay.addWidget(self._label("Confirm password"))
        lay.addSpacing(6)
        self.confirm_input = QLineEdit()
        self.confirm_input.setPlaceholderText("Re-enter password")
        self.confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_input.setClearButtonEnabled(True)
        self.confirm_input.setStyleSheet(self._input_style())
        self.confirm_input.textChanged.connect(self._sync_button)
        self.confirm_input.returnPressed.connect(self._on_submit)
        lay.addWidget(self.confirm_input)

        lay.addSpacing(14)

        # ── Role selector (hidden on first-run / bootstrap) ───────────────────
        self._role_section = QWidget()
        role_lay = QVBoxLayout(self._role_section)
        role_lay.setContentsMargins(0, 0, 0, 0)
        role_lay.setSpacing(6)
        role_lay.addWidget(self._label("Role"))
        self.role_combo = QComboBox()
        for label, _ in ROLE_OPTIONS:
            self.role_combo.addItem(label)
        self.role_combo.setStyleSheet(
            f"QComboBox {{"
            f"  border: 1px solid {BORDER}; border-radius: 8px;"
            f"  padding: 9px 12px; font-size: 13px;"
            f"  background: {BG_SURFACE}; color: {TEXT_PRIMARY};"
            f"}}"
            f"QComboBox::drop-down {{ border: none; }}"
            f"QComboBox QAbstractItemView {{"
            f"  border: 1px solid {BORDER}; border-radius: 6px;"
            f"  background: {BG_SURFACE}; selection-background-color: {PRIMARY_LIGHT};"
            f"}}"
        )
        role_lay.addWidget(self.role_combo)
        self._role_section.setVisible(self._show_role)
        lay.addWidget(self._role_section)

        if self._show_role:
            lay.addSpacing(14)

        # ── Show password toggle ───────────────────────────────────────────────
        self.show_pw = QCheckBox("Show password")
        self.show_pw.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 12px;"
            f"border: none; background: transparent;"
        )
        self.show_pw.toggled.connect(self._toggle_echo)
        lay.addWidget(self.show_pw)

        lay.addSpacing(6)

        # ── Feedback labels ────────────────────────────────────────────────────
        self._error_lbl = QLabel("")
        self._error_lbl.setStyleSheet(
            f"color: {DANGER_FG}; font-size: 12px; border: none; background: transparent;"
        )
        self._error_lbl.setWordWrap(True)
        self._error_lbl.hide()
        lay.addWidget(self._error_lbl)

        self._success_lbl = QLabel("")
        self._success_lbl.setStyleSheet(
            f"color: {SUCCESS_FG}; font-size: 12px; border: none; background: transparent;"
        )
        self._success_lbl.setWordWrap(True)
        self._success_lbl.hide()
        lay.addWidget(self._success_lbl)

        lay.addSpacing(20)

        # ── Submit button ──────────────────────────────────────────────────────
        self.submit_btn = QPushButton("Create account")
        self.submit_btn.setFixedHeight(42)
        self.submit_btn.setEnabled(False)
        self.submit_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background: {PRIMARY}; color: #fff;"
            f"  border: none; border-radius: 8px;"
            f"  font-size: 14px; font-weight: 600;"
            f"}}"
            f"QPushButton:hover   {{ background: #4338ca; }}"
            f"QPushButton:pressed {{ background: #3730a3; }}"
            f"QPushButton:disabled {{ background: {PRIMARY_LIGHT}; color: #a5b4fc; }}"
        )
        self.submit_btn.clicked.connect(self._on_submit)
        lay.addWidget(self.submit_btn)

        lay.addSpacing(16)

        # ── Back link ─────────────────────────────────────────────────────────
        back_row = QHBoxLayout()
        back_row.addStretch()
        back_lbl = QLabel(
            f"<a style='color:{PRIMARY}; text-decoration:none;' href='#'>← Back to sign in</a>"
        )
        back_lbl.setStyleSheet("border: none; background: transparent; font-size: 12px;")
        back_lbl.setTextFormat(Qt.TextFormat.RichText)
        back_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        back_lbl.setOpenExternalLinks(False)
        back_lbl.linkActivated.connect(lambda _: self.back_requested.emit())
        back_row.addWidget(back_lbl)
        back_row.addStretch()
        lay.addLayout(back_row)

        return card

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 12px; font-weight: 600;"
            f"border: none; background: transparent;"
        )
        return lbl

    def _input_style(self) -> str:
        return (
            f"QLineEdit {{"
            f"  border: 1px solid {BORDER}; border-radius: 8px;"
            f"  padding: 9px 12px; font-size: 13px;"
            f"  background: {BG_SURFACE}; color: {TEXT_PRIMARY};"
            f"}}"
            f"QLineEdit:focus {{ border-color: {PRIMARY}; }}"
        )

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _toggle_echo(self, checked: bool) -> None:
        mode = QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        self.password_input.setEchoMode(mode)
        self.confirm_input.setEchoMode(mode)

    def _sync_button(self) -> None:
        ready = (
            bool(self.name_input.text().strip())
            and bool(self.email_input.text().strip())
            and bool(self.password_input.text())
            and bool(self.confirm_input.text())
        )
        self.submit_btn.setEnabled(ready)

    def _on_submit(self) -> None:
        self.clear_feedback()

        name     = self.name_input.text().strip()
        email    = self.email_input.text().strip()
        password = self.password_input.text()
        confirm  = self.confirm_input.text()

        # ── Client-side validation ────────────────────────────────────────────
        if not name or not email or not password:
            self.show_error("Semua field harus diisi.")
            return
        if "@" not in email or "." not in email.split("@")[-1]:
            self.show_error("Format email tidak valid.")
            return
        if len(password) < 8:
            self.show_error("Password minimal 8 karakter.")
            return
        if password != confirm:
            self.show_error("Konfirmasi password tidak cocok.")
            return

        role_id = ROLE_OPTIONS[self.role_combo.currentIndex()][1] if self._show_role else 1

        self.register_requested.emit(name, email, password, role_id)

    # ── Public API ─────────────────────────────────────────────────────────────

    def show_error(self, msg: str) -> None:
        self._success_lbl.hide()
        self._error_lbl.setText(msg)
        self._error_lbl.show()

    def show_success(self, msg: str) -> None:
        self._error_lbl.hide()
        self._success_lbl.setText(msg)
        self._success_lbl.show()

    def clear_feedback(self) -> None:
        self._error_lbl.hide()
        self._success_lbl.hide()

    def reset(self) -> None:
        self.name_input.clear()
        self.email_input.clear()
        self.password_input.clear()
        self.confirm_input.clear()
        self.show_pw.setChecked(False)
        self.role_combo.setCurrentIndex(0)
        self.clear_feedback()


# ─────────────────────────────────────────────────────────────────────────────
# RegisterDialog
# ─────────────────────────────────────────────────────────────────────────────

class RegisterDialog(QDialog):
    """
    Modal dialog that wraps RegisterWidget.

    Parameters
    ----------
    auth_token : str | None
        Pass None on first-run (no users exist yet).
        Pass the logged-in Admin's token when adding users from Settings.
    parent : QWidget | None
    """

    registered = pyqtSignal(str)   # emits the new user's ID on success

    def __init__(self, auth_token: str | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._auth_token = auth_token
        self._bootstrap  = _no_users_exist()

        self.setWindowTitle("Create account – GroSync")
        self.setModal(True)
        self.setFixedWidth(480)
        self.setSizeGripEnabled(False)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)

        # On first-run hide the role combo (always Admin)
        show_role = not self._bootstrap
        self.form = RegisterWidget(show_role=show_role)
        self.form.register_requested.connect(self._handle_register)
        self.form.back_requested.connect(self.reject)
        lay.addWidget(self.form)

    # ── Handler ───────────────────────────────────────────────────────────────

    def _handle_register(self, name: str, email: str, password: str, role_id: int) -> None:
        from models import user_model   # local import avoids circular deps

        try:
            if self._bootstrap:
                # ── First-run: bypass permission check, create Admin directly ──
                hashed = _hash(password)
                new_id = user_model.create_user(name, email, hashed, 1)
            else:
                # ── Normal path: controller enforces manajemen_user permission ──
                from controllers import user_controller
                new_id = user_controller.create_user(
                    self._auth_token, name, email, password, role_id
                )

            self.registered.emit(new_id)
            self.form.show_success(
                f"Akun berhasil dibuat! ID: {new_id}  "
                f"({'Admin' if self._bootstrap else ''})"
            )
            # Give the user a moment to read the success message, then close.
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(1400, self.accept)

        except (ValueError, PermissionError) as exc:
            self.form.show_error(str(exc))