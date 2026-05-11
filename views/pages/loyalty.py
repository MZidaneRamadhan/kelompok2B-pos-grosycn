# ─────────────────────────────────────────────────────────────────────────────
# views/pages/loyalty.py
# ─────────────────────────────────────────────────────────────────────────────

import json
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QTabWidget, QDialog, QFormLayout, QProgressBar, QMessageBox,
    QComboBox, QSpinBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from views.styles.theme_manager import make_label, h_line, card_style, tier_badge_style
from views.styles.palettes import (
    PRIMARY, PRIMARY_LIGHT, PRIMARY_HOVER, PRIMARY_ACTIVE,
    BORDER, BG_SURFACE, BG_MUTED, TEXT_PRIMARY, TEXT_SECONDARY,
    DANGER_FG, SUCCESS_BG, SUCCESS_FG,
    tier_fg, tier_bg,
)
from controllers import loyalty_controller
from models import loyalty_model

# ── Persistent rewards store ──────────────────────────────────────────────────
_REWARDS_PATH = Path("data/rewards.json")

_DEFAULT_REWARDS = [
    {"id": "R001", "name": "Free Espresso",        "desc": "Redeem for one free espresso",         "cost": 200, "cat": "Free Item"},
    {"id": "R002", "name": "10% Off Next Purchase", "desc": "10% off your entire next order",       "cost": 150, "cat": "Discount"},
    {"id": "R003", "name": "Free Pastry",           "desc": "Choose any pastry from our selection", "cost": 250, "cat": "Free Item"},
    {"id": "R004", "name": "Buy One Get One",       "desc": "BOGO on any beverage",                 "cost": 500, "cat": "Special Offer"},
]

REWARD_CATEGORIES = ["Free Item", "Discount", "Special Offer", "Voucher", "Other"]


def _load_rewards() -> list[dict]:
    if not _REWARDS_PATH.exists():
        _save_rewards(_DEFAULT_REWARDS)
        return _DEFAULT_REWARDS
    try:
        return json.loads(_REWARDS_PATH.read_text())
    except Exception:
        return list(_DEFAULT_REWARDS)


def _save_rewards(rewards: list[dict]) -> None:
    _REWARDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _REWARDS_PATH.write_text(json.dumps(rewards, indent=2))


# ─────────────────────────────────────────────────────────────────────────────
# AddRewardDialog
# ─────────────────────────────────────────────────────────────────────────────

class AddRewardDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Tambah Reward Baru")
        self.setFixedWidth(380)
        self.setModal(True)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(14)

        lay.addWidget(make_label("Reward Baru", 16, bold=True))
        lay.addWidget(h_line())

        form = QFormLayout()
        form.setSpacing(10)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nama reward…")
        form.addRow("Nama *", self.name_input)

        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Deskripsi singkat…")
        form.addRow("Deskripsi", self.desc_input)

        self.cat_combo = QComboBox()
        for c in REWARD_CATEGORIES:
            self.cat_combo.addItem(c)
        form.addRow("Kategori", self.cat_combo)

        self.cost_spin = QSpinBox()
        self.cost_spin.setRange(1, 999_999)
        self.cost_spin.setValue(100)
        self.cost_spin.setSuffix(" poin")
        form.addRow("Biaya Poin *", self.cost_spin)

        lay.addLayout(form)

        self._err = make_label("", 11, color=DANGER_FG)
        self._err.hide()
        lay.addWidget(self._err)

        btn_row = QHBoxLayout()
        cancel = QPushButton("Batal")
        cancel.setStyleSheet(
            f"QPushButton {{ background:transparent; border:1px solid {BORDER};"
            f" border-radius:8px; padding:8px 20px; color:{TEXT_PRIMARY}; font-size:13px;}}"
            f"QPushButton:hover {{ background:{BG_MUTED}; }}"
        )
        cancel.clicked.connect(self.reject)
        save = QPushButton("Simpan Reward")
        save.setStyleSheet(
            f"QPushButton {{ background:{PRIMARY}; color:#fff; border:none;"
            f" border-radius:8px; padding:8px 20px; font-size:13px; font-weight:600;}}"
            f"QPushButton:hover {{ background:{PRIMARY_HOVER}; }}"
        )
        save.clicked.connect(self._on_save)
        btn_row.addWidget(cancel)
        btn_row.addWidget(save)
        lay.addLayout(btn_row)

    def _on_save(self) -> None:
        name = self.name_input.text().strip()
        if not name:
            self._err.setText("Nama reward tidak boleh kosong.")
            self._err.show()
            return
        self.result_reward = {
            "id":   f"R{len(_load_rewards()) + 1:03d}",
            "name": name,
            "desc": self.desc_input.text().strip(),
            "cat":  self.cat_combo.currentText(),
            "cost": self.cost_spin.value(),
        }
        self.accept()


# ─────────────────────────────────────────────────────────────────────────────
# RedeemDialog – pick a member then confirm redemption
# ─────────────────────────────────────────────────────────────────────────────

class RedeemDialog(QDialog):
    def __init__(self, reward: dict, auth_token: str, parent=None) -> None:
        super().__init__(parent)
        self._reward     = reward
        self._auth_token = auth_token
        self._member: dict | None = None

        self.setWindowTitle(f"Tukar: {reward['name']}")
        self.setFixedWidth(380)
        self.setModal(True)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(12)

        lay.addWidget(make_label(f"Tukar: {reward['name']}", 15, bold=True))
        lay.addWidget(make_label(f"Biaya: {reward['cost']:,} poin", 12, color=TEXT_SECONDARY))
        lay.addWidget(h_line())

        lay.addWidget(make_label("Cari Member (HP atau Email)", 12, color=TEXT_SECONDARY))
        search_row = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText("Nomor HP atau Email…")
        self._search.returnPressed.connect(self._lookup)
        search_row.addWidget(self._search)
        cari_btn = QPushButton("Cari")
        cari_btn.setStyleSheet(
            f"QPushButton {{ background:{PRIMARY}; color:#fff; border:none;"
            f" border-radius:8px; padding:7px 14px; font-size:12px; font-weight:600;}}"
            f"QPushButton:hover {{ background:{PRIMARY_HOVER}; }}"
        )
        cari_btn.clicked.connect(self._lookup)
        search_row.addWidget(cari_btn)
        lay.addLayout(search_row)

        self._banner = QWidget()
        self._banner.setStyleSheet(f"background:{SUCCESS_BG}; border-radius:8px;")
        b_lay = QHBoxLayout(self._banner)
        b_lay.setContentsMargins(10, 8, 10, 8)
        self._b_name = make_label("", 12, bold=True, color=SUCCESS_FG)
        self._b_pts  = make_label("", 11, color=SUCCESS_FG)
        b_lay.addWidget(QLabel("⭐"))
        b_lay.addWidget(self._b_name)
        b_lay.addStretch()
        b_lay.addWidget(self._b_pts)
        self._banner.hide()
        lay.addWidget(self._banner)

        self._err = make_label("", 11, color=DANGER_FG)
        self._err.hide()
        lay.addWidget(self._err)

        btn_row = QHBoxLayout()
        cancel = QPushButton("Batal")
        cancel.setStyleSheet(
            f"QPushButton {{ background:transparent; border:1px solid {BORDER};"
            f" border-radius:8px; padding:8px 16px; color:{TEXT_PRIMARY}; font-size:13px;}}"
            f"QPushButton:hover {{ background:{BG_MUTED}; }}"
        )
        cancel.clicked.connect(self.reject)
        self._redeem_btn = QPushButton(f"Tukar ({reward['cost']:,} poin)")
        self._redeem_btn.setEnabled(False)
        self._redeem_btn.setStyleSheet(
            f"QPushButton {{ background:{PRIMARY}; color:#fff; border:none;"
            f" border-radius:8px; padding:8px 16px; font-size:13px; font-weight:600;}}"
            f"QPushButton:hover {{ background:{PRIMARY_HOVER}; }}"
            f"QPushButton:disabled {{ background:#c7d2fe; color:#fff; }}"
        )
        self._redeem_btn.clicked.connect(self._on_redeem)
        btn_row.addWidget(cancel)
        btn_row.addWidget(self._redeem_btn)
        lay.addLayout(btn_row)

    def _lookup(self) -> None:
        self._err.hide()
        self._banner.hide()
        self._redeem_btn.setEnabled(False)
        identifier = self._search.text().strip()
        if not identifier:
            return
        try:
            member = loyalty_controller.verify_member(self._auth_token, identifier)
            self._member = member
            self._b_name.setText(member["name"])
            self._b_pts.setText(f"{member.get('points', 0):,} pts")
            self._banner.show()
            can_redeem = member.get("points", 0) >= self._reward["cost"]
            self._redeem_btn.setEnabled(can_redeem)
            if not can_redeem:
                self._err.setText(
                    f"Poin tidak cukup. Butuh {self._reward['cost']:,}, "
                    f"punya {member.get('points', 0):,}."
                )
                self._err.show()
        except ValueError as e:
            self._err.setText(str(e))
            self._err.show()

    def _on_redeem(self) -> None:
        if not self._member:
            return
        try:
            loyalty_controller.redeem_reward(
                auth_token=self._auth_token,
                member_id=self._member["id"],
                reward_cost=self._reward["cost"],
                reward_name=self._reward["name"],
            )
            self.accept()
        except ValueError as e:
            self._err.setText(str(e))
            self._err.show()


# ─────────────────────────────────────────────────────────────────────────────
# LoyaltyPage
# ─────────────────────────────────────────────────────────────────────────────

class LoyaltyPage(QWidget):
    """Customer loyalty program: member table, customer detail modal, rewards catalog."""

    status_msg = pyqtSignal(str)

    def __init__(self, auth_token: str = "", parent=None) -> None:
        super().__init__(parent)
        self.auth_token = auth_token

        lay = QVBoxLayout(self)
        lay.setSpacing(16)
        lay.setContentsMargins(0, 0, 0, 0)

        lay.addLayout(self._build_header())
        lay.addLayout(self._build_stats())

        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_customers_tab(), "Customers")
        self._tabs.addTab(self._build_rewards_tab(),   "Rewards Catalog")
        lay.addWidget(self._tabs)

    # ── Called by MainWindow on page switch and after transactions ────────────

    def refresh_data(self) -> None:
        """Reload stats row, customer table, and rewards tab."""
        self._refresh_stats()
        self._refresh_customers()
        self._refresh_rewards_tab()

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self) -> QHBoxLayout:
        hdr = QHBoxLayout()
        info = QVBoxLayout()
        info.addWidget(make_label("Loyalty Program", 18, bold=True))
        info.addWidget(make_label("Manage customer rewards and loyalty points", 12, color=TEXT_SECONDARY))
        hdr.addLayout(info)
        hdr.addStretch()

        new_btn = QPushButton("🎁  New Reward")
        new_btn.setStyleSheet(
            f"QPushButton {{ background:{PRIMARY}; color:#fff; border:none;"
            f" border-radius:8px; padding:8px 16px; font-size:13px; font-weight:600;}}"
            f"QPushButton:hover {{ background:{PRIMARY_HOVER}; }}"
        )
        new_btn.clicked.connect(self._show_add_reward_dialog)
        hdr.addWidget(new_btn)
        return hdr

    # ── Stats row ─────────────────────────────────────────────────────────────

    def _build_stats(self) -> QHBoxLayout:
        self._stat_cards: dict[str, QLabel] = {}
        row = QHBoxLayout()
        for key, title, val in [
            ("members",  "Total Members",  "0"),
            ("points",   "Points Issued",  "0"),
            ("spent",    "Total Spent",    "Rp0"),
            ("rewards",  "Active Rewards", str(len(_load_rewards()))),
        ]:
            card = QWidget()
            card.setStyleSheet(card_style())
            cv = QVBoxLayout(card)
            cv.addWidget(make_label(title, 11, color=TEXT_SECONDARY))
            val_lbl = make_label(val, 18, bold=True)
            self._stat_cards[key] = val_lbl
            cv.addWidget(val_lbl)
            row.addWidget(card)

        self._refresh_stats()
        return row

    def _refresh_stats(self) -> None:
        all_members    = loyalty_model.get_all_members()
        active_members = [m for m in all_members if m.get("is_active", True)]
        total_pts      = sum(m["points"] for m in active_members)
        total_spent    = sum(m["spent"]  for m in active_members)
        rewards        = _load_rewards()

        self._stat_cards["members"].setText(str(len(active_members)))
        self._stat_cards["points"].setText(f"{total_pts:,}")
        self._stat_cards["spent"].setText(f"Rp{total_spent:,.0f}")
        self._stat_cards["rewards"].setText(str(len(rewards)))

    # ── Customers tab ─────────────────────────────────────────────────────────

    def _build_customers_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(10)

        toolbar = QHBoxLayout()
        self.cust_search = QLineEdit()
        self.cust_search.setPlaceholderText("🔍  Search customers…")
        self.cust_search.textChanged.connect(self._refresh_customers)
        toolbar.addWidget(self.cust_search)

        add_btn = QPushButton("➕  Add Member")
        add_btn.setStyleSheet(
            f"QPushButton {{ background:{PRIMARY}; color:#fff; border:none;"
            f" border-radius:8px; padding:7px 16px; font-size:13px; font-weight:600;}}"
            f"QPushButton:hover {{ background:{PRIMARY_HOVER}; }}"
        )
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
        all_members    = loyalty_model.get_all_members()
        active_members = [m for m in all_members if m.get("is_active", True)]
        rows = (
            [c for c in active_members if q in c["name"].lower() or q in c.get("email", "").lower()]
            if q else active_members
        )
        self._current_table_data = rows
        self.cust_table.setRowCount(len(rows))
        for r, c in enumerate(rows):
            self.cust_table.setItem(r, 0, QTableWidgetItem(c["name"]))
            self.cust_table.setItem(r, 1, QTableWidgetItem(c.get("email", "")))
            self.cust_table.setItem(r, 2, QTableWidgetItem(c.get("phone", "")))
            tier_item = QTableWidgetItem(c["tier"])
            tier_item.setForeground(QColor(tier_fg(c["tier"])))
            self.cust_table.setItem(r, 3, tier_item)
            self.cust_table.setItem(r, 4, QTableWidgetItem(f"{c['points']:,}"))
            self.cust_table.setItem(r, 5, QTableWidgetItem(f"Rp{c['spent']:,.0f}"))
            self.cust_table.setItem(r, 6, QTableWidgetItem(str(c["visits"])))

    def _show_customer_detail(self, row: int, _: int) -> None:
        c = self._current_table_data[row]
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Customer: {c['name']}")
        dlg.setFixedWidth(380)

        v = QVBoxLayout(dlg)
        v.setSpacing(10)
        v.setContentsMargins(20, 20, 20, 20)

        initials = "".join(n[0] for n in c["name"].split() if n) or "?"
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
            ("Email",       c.get("email", "-")),
            ("Phone",       c.get("phone", "-")),
            ("Points",      f"{c['points']:,}"),
            ("Total Spent", f"Rp{c['spent']:,.0f}"),
            ("Visits",      str(c["visits"])),
            ("Join Date",   c.get("join_date", c.get("join", "-"))),
        ]:
            form.addRow(make_label(label, 11, color=TEXT_SECONDARY), make_label(val, 12))
        v.addLayout(form)

        v.addWidget(make_label("Tier Progress", 11, color=TEXT_SECONDARY))
        prog = QProgressBar()
        prog.setValue({"Bronze": 25, "Silver": 50, "Gold": 75, "Platinum": 100}.get(c["tier"], 25))
        prog.setFixedHeight(8)
        v.addWidget(prog)

        btn_layout = QHBoxLayout()
        edit_btn = QPushButton("Edit")
        edit_btn.setStyleSheet(
            f"QPushButton {{ background:{PRIMARY_LIGHT}; color:{PRIMARY}; border:none;"
            f" border-radius:8px; padding:7px 16px; font-size:12px; font-weight:600;}}"
        )
        edit_btn.clicked.connect(lambda: self._show_edit_member_dialog(c, dlg))
        delete_btn = QPushButton("Nonaktifkan")
        delete_btn.setStyleSheet(
            f"QPushButton {{ background:transparent; color:{DANGER_FG}; border:1px solid {DANGER_FG};"
            f" border-radius:8px; padding:7px 16px; font-size:12px; font-weight:600;}}"
        )
        delete_btn.clicked.connect(lambda: self._delete_member(c, dlg))
        close_btn = QPushButton("Tutup")
        close_btn.setStyleSheet(
            f"QPushButton {{ background:transparent; border:1px solid {BORDER};"
            f" border-radius:8px; padding:7px 16px; color:{TEXT_PRIMARY}; font-size:12px;}}"
            f"QPushButton:hover {{ background:{BG_MUTED}; }}"
        )
        close_btn.clicked.connect(dlg.accept)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(delete_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        v.addLayout(btn_layout)

        dlg.exec()

    # ── CRUD Actions ──────────────────────────────────────────────────────────

    def _show_add_member_dialog(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle("Add New Member")
        dlg.setFixedWidth(320)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)
        lay.addWidget(make_label("Daftarkan Member Baru", 14, bold=True))

        form = QFormLayout()
        name_input  = QLineEdit(); name_input.setPlaceholderText("Nama lengkap")
        email_input = QLineEdit(); email_input.setPlaceholderText("email@contoh.com")
        phone_input = QLineEdit(); phone_input.setPlaceholderText("08xx-xxxx-xxxx")
        form.addRow("Nama *",  name_input)
        form.addRow("Email",   email_input)
        form.addRow("HP *",    phone_input)
        lay.addLayout(form)

        err = make_label("", 11, color=DANGER_FG); err.hide()
        lay.addWidget(err)

        btn_row = QHBoxLayout()
        cancel_btn = QPushButton("Batal")
        cancel_btn.setStyleSheet(
            f"QPushButton {{ background:transparent; border:1px solid {BORDER};"
            f" border-radius:8px; padding:7px 16px; color:{TEXT_PRIMARY}; font-size:13px;}}"
        )
        cancel_btn.clicked.connect(dlg.reject)
        save_btn = QPushButton("Simpan")
        save_btn.setStyleSheet(
            f"QPushButton {{ background:{PRIMARY}; color:#fff; border:none;"
            f" border-radius:8px; padding:7px 16px; font-size:13px; font-weight:600;}}"
            f"QPushButton:hover {{ background:{PRIMARY_HOVER}; }}"
        )
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        lay.addLayout(btn_row)

        def save_member():
            try:
                loyalty_controller.create_member(
                    auth_token=self.auth_token,
                    member_name=name_input.text(),
                    email=email_input.text(),
                    phone_number=phone_input.text(),
                )
                self.status_msg.emit(f"Member '{name_input.text()}' berhasil ditambahkan!")
                self.refresh_data()
                dlg.accept()
            except ValueError as e:
                err.setText(str(e)); err.show()
            except Exception as e:
                err.setText(f"Error: {e}"); err.show()

        save_btn.clicked.connect(save_member)
        dlg.exec()

    def _show_edit_member_dialog(self, customer_data: dict, parent_dlg: QDialog) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Edit: {customer_data['name']}")
        dlg.setFixedWidth(320)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)
        lay.addWidget(make_label("Edit Data Member", 14, bold=True))

        form = QFormLayout()
        name_input  = QLineEdit(customer_data.get("name", ""))
        email_input = QLineEdit(customer_data.get("email", ""))
        phone_input = QLineEdit(customer_data.get("phone", ""))
        form.addRow("Nama *",  name_input)
        form.addRow("Email",   email_input)
        form.addRow("HP *",    phone_input)
        lay.addLayout(form)

        err = make_label("", 11, color=DANGER_FG); err.hide()
        lay.addWidget(err)

        btn_row = QHBoxLayout()
        cancel_btn = QPushButton("Batal")
        cancel_btn.setStyleSheet(
            f"QPushButton {{ background:transparent; border:1px solid {BORDER};"
            f" border-radius:8px; padding:7px 16px; color:{TEXT_PRIMARY}; font-size:13px;}}"
        )
        cancel_btn.clicked.connect(dlg.reject)
        save_btn = QPushButton("Simpan")
        save_btn.setStyleSheet(
            f"QPushButton {{ background:{PRIMARY}; color:#fff; border:none;"
            f" border-radius:8px; padding:7px 16px; font-size:13px; font-weight:600;}}"
            f"QPushButton:hover {{ background:{PRIMARY_HOVER}; }}"
        )
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        lay.addLayout(btn_row)

        def update_member():
            try:
                loyalty_controller.update_member(
                    auth_token=self.auth_token,
                    member_id=customer_data.get("id", ""),
                    member_name=name_input.text(),
                    email=email_input.text(),
                    phone_number=phone_input.text(),
                )
                self.status_msg.emit("Member berhasil diperbarui!")
                self.refresh_data()
                dlg.accept()
                parent_dlg.accept()
            except ValueError as e:
                err.setText(str(e)); err.show()
            except Exception as e:
                err.setText(f"Error: {e}"); err.show()

        save_btn.clicked.connect(update_member)
        dlg.exec()

    def _delete_member(self, customer_data: dict, parent_dlg: QDialog) -> None:
        confirm = QMessageBox.question(
            self, "Konfirmasi",
            f"Nonaktifkan member '{customer_data['name']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                loyalty_controller.delete_member(
                    auth_token=self.auth_token,
                    member_id=customer_data.get("id", ""),
                )
                self.status_msg.emit(f"Member '{customer_data['name']}' dinonaktifkan.")
                self.refresh_data()
                parent_dlg.accept()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    # ── Rewards tab ───────────────────────────────────────────────────────────

    def _build_rewards_tab(self) -> QWidget:
        self._rewards_container = QWidget()
        self._rewards_lay = QVBoxLayout(self._rewards_container)
        self._rewards_lay.setSpacing(10)
        self._refresh_rewards_tab()
        return self._rewards_container

    def _refresh_rewards_tab(self) -> None:
        # Clear old cards
        while self._rewards_lay.count():
            item = self._rewards_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        rewards = _load_rewards()
        for rw in rewards:
            card = QWidget()
            card.setStyleSheet(
                f"QWidget {{ background:{BG_SURFACE}; border:1px solid {BORDER};"
                f" border-radius:10px; padding:14px; }}"
            )
            row = QHBoxLayout(card)

            info = QVBoxLayout()
            info.addWidget(make_label(rw["name"], 13, bold=True))
            info.addWidget(make_label(rw["desc"], 11, color=TEXT_SECONDARY))
            cat_lbl = QLabel(rw["cat"])
            cat_lbl.setStyleSheet(
                f"background:{PRIMARY_LIGHT}; color:{PRIMARY}; border-radius:6px;"
                f" padding:2px 8px; font-size:11px; font-weight:600; margin-top:4px;"
            )
            info.addWidget(cat_lbl)
            row.addLayout(info)
            row.addStretch()

            pts_col = QVBoxLayout()
            pts_col.addWidget(
                make_label(f"{rw['cost']:,}", 18, bold=True, color=PRIMARY),
                alignment=Qt.AlignmentFlag.AlignCenter,
            )
            pts_col.addWidget(
                make_label("poin", 10, color=TEXT_SECONDARY),
                alignment=Qt.AlignmentFlag.AlignCenter,
            )
            redeem_btn = QPushButton("Redeem")
            redeem_btn.setStyleSheet(
                f"QPushButton {{ background:{PRIMARY}; color:#fff; border:none;"
                f" border-radius:6px; padding:5px 14px; font-size:12px; font-weight:600;}}"
                f"QPushButton:hover {{ background:{PRIMARY_HOVER}; }}"
            )
            redeem_btn.clicked.connect(lambda _, r=rw: self._on_redeem(r))
            pts_col.addWidget(redeem_btn)
            row.addLayout(pts_col)

            self._rewards_lay.addWidget(card)

        self._rewards_lay.addStretch()

    def _on_redeem(self, reward: dict) -> None:
        dlg = RedeemDialog(reward, self.auth_token, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.status_msg.emit(
                f"✅ Berhasil menukar '{reward['name']}' ({reward['cost']:,} poin)"
            )
            self.refresh_data()

    # ── Add Reward ────────────────────────────────────────────────────────────

    def _show_add_reward_dialog(self) -> None:
        dlg = AddRewardDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            rewards = _load_rewards()
            rewards.append(dlg.result_reward)
            _save_rewards(rewards)
            self.status_msg.emit(f"Reward '{dlg.result_reward['name']}' berhasil ditambahkan!")
            self.refresh_data()