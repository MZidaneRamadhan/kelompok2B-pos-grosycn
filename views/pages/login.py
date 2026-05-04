# ─────────────────────────────────────────────────────────────────────────────
# views/pages/login.py
# ─────────────────────────────────────────────────────────────────────────────

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QLabel, QCheckBox, QDialog,
)
from PyQt6.QtCore import Qt, pyqtSignal

from views.styles.palettes import (
    PRIMARY, PRIMARY_LIGHT, BG_APP, BG_SURFACE,
    BORDER, TEXT_PRIMARY, TEXT_SECONDARY, DANGER_FG,
)


class LoginWidget(QWidget):
    """
    Standalone login form. Emits `login_requested(username, password, remember)`
    when the user submits. Drop it into any layout or wrap in LoginDialog.
    """

    login_requested = pyqtSignal(str, str, bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet(f"background: {BG_APP};")
        self._build_ui()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # Full-screen centering
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
        card.setFixedWidth(400)
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

        # ── Title & subtitle (no border, no background override) ─────────────
        title = QLabel("Sign in to GroSync")
        title.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 20px; font-weight: 700; border: none; background: transparent;"
        )
        lay.addWidget(title)

        lay.addSpacing(6)

        subtitle = QLabel("Enter your credentials to access the POS dashboard.")
        subtitle.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 12px; border: none; background: transparent;"
        )
        subtitle.setWordWrap(True)
        lay.addWidget(subtitle)

        lay.addSpacing(28)

        # ── Email ─────────────────────────────────────────────────────────────
        lay.addWidget(self._field_label("Email or username"))
        lay.addSpacing(6)
        self.username = QLineEdit()
        self.username.setPlaceholderText("you@example.com")
        self.username.setClearButtonEnabled(True)
        self.username.setStyleSheet(self._input_style())
        self.username.textChanged.connect(self._sync_button)
        lay.addWidget(self.username)

        lay.addSpacing(16)

        # ── Password ──────────────────────────────────────────────────────────
        pwd_header = QHBoxLayout()
        pwd_header.addWidget(self._field_label("Password"))
        pwd_header.addStretch()
        forgot = QLabel("<a style='color:{c}; text-decoration:none;' href='#'>Forgot password?</a>".format(c=PRIMARY))
        forgot.setStyleSheet("border: none; background: transparent; font-size: 12px;")
        forgot.setTextFormat(Qt.TextFormat.RichText)
        forgot.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        forgot.setOpenExternalLinks(False)
        pwd_header.addWidget(forgot)
        lay.addLayout(pwd_header)

        lay.addSpacing(6)

        self.password = QLineEdit()
        self.password.setPlaceholderText("••••••••")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setClearButtonEnabled(True)
        self.password.setStyleSheet(self._input_style())
        self.password.textChanged.connect(self._sync_button)
        self.password.returnPressed.connect(self._on_submit)
        lay.addWidget(self.password)

        lay.addSpacing(16)

        # ── Remember me ───────────────────────────────────────────────────────
        self.remember = QCheckBox("Remember me")
        self.remember.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 12px; border: none; background: transparent;"
        )
        lay.addWidget(self.remember)

        lay.addSpacing(6)

        # ── Error message ─────────────────────────────────────────────────────
        self._error_lbl = QLabel("")
        self._error_lbl.setStyleSheet(
            f"color: {DANGER_FG}; font-size: 12px; border: none; background: transparent;"
        )
        self._error_lbl.setWordWrap(True)
        self._error_lbl.hide()
        lay.addWidget(self._error_lbl)

        lay.addSpacing(24)

        # ── Sign in button ────────────────────────────────────────────────────
        self.login_btn = QPushButton("Sign in")
        self.login_btn.setFixedHeight(42)
        self.login_btn.setEnabled(False)
        self.login_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background: {PRIMARY}; color: #fff;"
            f"  border: none; border-radius: 8px;"
            f"  font-size: 14px; font-weight: 600;"
            f"}}"
            f"QPushButton:hover   {{ background: #4338ca; }}"
            f"QPushButton:pressed {{ background: #3730a3; }}"
            f"QPushButton:disabled {{ background: {PRIMARY_LIGHT}; color: #a5b4fc; }}"
        )
        self.login_btn.clicked.connect(self._on_submit)
        lay.addWidget(self.login_btn)

        return card

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _field_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 12px; font-weight: 600;"
            f"border: none; background: transparent;"
        )
        return lbl

    def _input_style(self) -> str:
        return (
            f"QLineEdit {{"
            f"  border: 1px solid {BORDER};"
            f"  border-radius: 8px;"
            f"  padding: 9px 12px;"
            f"  font-size: 13px;"
            f"  background: {BG_SURFACE};"
            f"  color: {TEXT_PRIMARY};"
            f"}}"
            f"QLineEdit:focus {{ border-color: {PRIMARY}; }}"
        )

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _sync_button(self) -> None:
        ready = bool(self.username.text().strip()) and bool(self.password.text())
        self.login_btn.setEnabled(ready)

    def _on_submit(self) -> None:
        u = self.username.text().strip()
        p = self.password.text()
        if not u or not p:
            return
        self.clear_error()
        self.login_requested.emit(u, p, self.remember.isChecked())

    # ── Public API ────────────────────────────────────────────────────────────

    def show_error(self, msg: str) -> None:
        self._error_lbl.setText(msg)
        self._error_lbl.show()

    def clear_error(self) -> None:
        self._error_lbl.hide()

    def reset(self) -> None:
        self.username.clear()
        self.password.clear()
        self.remember.setChecked(False)
        self.clear_error()


class LoginDialog(QDialog):
    """
    Modal dialog wrapping LoginWidget. Accepts on valid credentials.
    `username` property exposes the authenticated user after accept().
    """

    accepted_login = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Sign in – GroSync")
        self.setModal(True)
        self.setFixedWidth(480)
        self.setSizeGripEnabled(False)
        self._username: str | None = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)

        self.form = LoginWidget()
        self.form.login_requested.connect(self._validate)
        lay.addWidget(self.form)

    # ── Validation (swap with real auth) ──────────────────────────────────────

    def _validate(self, username: str, password: str, remember: bool) -> None:
        # Demo: any non-empty credentials pass
        if username and password:
            self._username = username
            self.accepted_login.emit(username)
            self.accept()
        else:
            self.form.show_error("Invalid username or password.")

    @property
    def username(self) -> str | None:
        return self._username
