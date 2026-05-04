# ─────────────────────────────────────────────────────────────────────────────
# views/pages/loyalty.py
# ─────────────────────────────────────────────────────────────────────────────

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QTabWidget, QDialog, QFormLayout, QProgressBar,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from views.styles.theme_manager import make_label, h_line, card_style, tier_badge_style
from views.styles.palettes import PRIMARY, PRIMARY_LIGHT, BORDER, BG_SURFACE, tier_fg, tier_bg
from data.store import CUSTOMERS, REWARDS


class LoyaltyPage(QWidget):
    """Customer loyalty program: member table, customer detail modal, rewards catalog."""

    status_msg = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

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
        total_pts = sum(c["points"] for c in CUSTOMERS)
        total_spent = sum(c["spent"] for c in CUSTOMERS)

        row = QHBoxLayout()
        for title, val in [
            ("Total Members",  str(len(CUSTOMERS))),
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

        self.cust_search = QLineEdit()
        self.cust_search.setPlaceholderText("🔍  Search customers…")
        self.cust_search.textChanged.connect(self._refresh_customers)
        v.addWidget(self.cust_search)

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
        rows = (
            [c for c in CUSTOMERS if q in c["name"].lower() or q in c["email"].lower()]
            if q else CUSTOMERS
        )

        self.cust_table.setRowCount(len(rows))
        for r, c in enumerate(rows):
            self.cust_table.setItem(r, 0, QTableWidgetItem(c["name"]))
            self.cust_table.setItem(r, 1, QTableWidgetItem(c["email"]))
            self.cust_table.setItem(r, 2, QTableWidgetItem(c["phone"]))

            tier_item = QTableWidgetItem(c["tier"])
            tier_item.setForeground(QColor(tier_fg(c["tier"])))
            self.cust_table.setItem(r, 3, tier_item)

            self.cust_table.setItem(r, 4, QTableWidgetItem(f"{c['points']:,}"))
            self.cust_table.setItem(r, 5, QTableWidgetItem(f"${c['spent']:.2f}"))
            self.cust_table.setItem(r, 6, QTableWidgetItem(str(c["visits"])))

    def _show_customer_detail(self, row: int, _: int) -> None:
        q = self.cust_search.text().lower()
        rows = (
            [c for c in CUSTOMERS if q in c["name"].lower() or q in c["email"].lower()]
            if q else CUSTOMERS
        )
        c = rows[row]

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Customer: {c['name']}")
        dlg.setFixedWidth(380)

        v = QVBoxLayout(dlg)
        v.setSpacing(10)
        v.setContentsMargins(20, 20, 20, 20)

        # Avatar
        initials = "".join(n[0] for n in c["name"].split())
        av = QLabel(initials)
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
            ("Email",        c["email"]),
            ("Phone",        c["phone"]),
            ("Points",       f"{c['points']:,}"),
            ("Total Spent",  f"${c['spent']:.2f}"),
            ("Visits",       str(c["visits"])),
            ("Member Since", c["join"]),
        ]:
            form.addRow(make_label(label, 11, color="#64748b"), make_label(val, 12))
        v.addLayout(form)

        v.addWidget(make_label("Tier Progress", 11, color="#64748b"))
        prog = QProgressBar()
        prog.setValue({"Bronze": 25, "Silver": 50, "Gold": 75, "Platinum": 100}.get(c["tier"], 25))
        prog.setFixedHeight(8)
        v.addWidget(prog)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dlg.accept)
        v.addWidget(close_btn)

        dlg.exec()

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
