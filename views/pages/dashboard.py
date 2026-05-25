from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QFrame, QProgressBar,
)
from PyQt6.QtCore import Qt

from views.styles.theme_manager import make_label, h_line
from views.styles.palettes import PRIMARY, SUCCESS, WARNING, PINK, BG_SURFACE, BORDER

from controllers.dashboard_controller import get_dashboard_summary

# Palet warna kategori — dipakai berulang jika kategori > 4
_CAT_COLORS = [PRIMARY, SUCCESS, WARNING, PINK, "#06b6d4", "#8b5cf6"]


class DashboardPage(QWidget):
    """Overview page: KPI cards, revenue trend, kategori, transaksi, member."""

    # Label tab → key period untuk controller
    _PERIOD_MAP = {
        "Harian":   "daily",
        "Mingguan": "weekly",
        "Bulanan":  "monthly",
        "Tahunan":  "annually",
    }

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._period = "monthly"        # default
        self._data   = {}               # cache hasil get_dashboard_summary

        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        lay.setContentsMargins(0, 0, 0, 0)

        lay.addLayout(self._build_header())

        # ── placeholder widgets yang akan diisi ulang saat refresh ────────────
        self._kpi_row_widget   = QWidget()
        self._kpi_row_layout   = QHBoxLayout(self._kpi_row_widget)
        self._kpi_row_layout.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._kpi_row_widget)

        self._charts_row_widget  = QWidget()
        self._charts_row_layout  = QHBoxLayout(self._charts_row_widget)
        self._charts_row_layout.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._charts_row_widget)

        self._orders_placeholder = QWidget()
        self._orders_layout      = QVBoxLayout(self._orders_placeholder)
        self._orders_layout.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._orders_placeholder)

        self._activity_row_widget  = QWidget()
        self._activity_row_layout  = QHBoxLayout(self._activity_row_widget)
        self._activity_row_layout.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._activity_row_widget)

        self._stock_placeholder = QWidget()
        self._stock_layout      = QVBoxLayout(self._stock_placeholder)
        self._stock_layout.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._stock_placeholder)

        # Muat data pertama kali
        self.refresh()

    # ── Public ────────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        """Ambil ulang semua data dari DB dan render ulang."""
        self._data = get_dashboard_summary(self._period)
        self._render_all()

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self) -> QHBoxLayout:
        header_layout = QHBoxLayout()

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_col.addWidget(make_label("Dashboard", 18, bold=True))
        title_col.addWidget(make_label("Ringkasan operasional toko grosir", 11, color="#64748b"))
        hdr.addLayout(title_col)
        hdr.addStretch()

        # Tombol periode — lebih ringkas dari QTabWidget (tidak ada padding tab internal)
        self._period_btns: list = []
        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)
        for label in self._PERIOD_MAP:
            from PyQt6.QtWidgets import QPushButton
            btn = QPushButton(label)
            btn.setFixedHeight(28)
            btn.setCheckable(True)
            btn.setChecked(label == "Bulanan")
            btn.setStyleSheet(
                "QPushButton { border:1px solid #cbd5e1; border-radius:5px; "
                "padding:0 12px; font-size:11px; background:#f8fafc; color:#334155; }"
                "QPushButton:checked { background:#5B5BD6; color:white; border-color:#5B5BD6; }"
                "QPushButton:hover:!checked { background:#f1f5f9; }"
            )
            btn.clicked.connect(lambda _, lbl=label: self._on_period_changed(lbl))
            btn_row.addWidget(btn)
            self._period_btns.append((label, btn))
        hdr.addLayout(btn_row)

    def _refresh_dashboard(self, period_index: int | None = None) -> None:
        if period_index is not None:
            self.current_period = period_index

        self.transactions = self._load_transactions()
        self.filtered_transactions = self._filter_transactions(self.transactions)

        self._clear_layout(self.content_layout)

        self.content_layout.addLayout(self._build_kpi_row())
        self.content_layout.addLayout(self._build_charts_row())
        self.content_layout.addWidget(self._build_orders_chart())
        self.content_layout.addLayout(self._build_activity_row())
        self.content_layout.addStretch()

    def _load_transactions(self) -> list[dict]:
        if not TRANSACTION_FILE.exists():
            return []

        with open(TRANSACTION_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        return list(data.values())

    def _filter_transactions(self, transactions: list[dict]) -> list[dict]:
        days = TIME_FILTERS.get(self.current_period, 30)
        threshold = datetime.now() - timedelta(days=days)

        filtered_data = []

        for transaction in transactions:
            transaction_date = datetime.strptime(
                transaction["timestamp"], "%Y-%m-%d %H:%M:%S"
            )

            if transaction_date >= threshold:
                filtered_data.append(transaction)

        return sorted(
            filtered_data,
            key=lambda transaction: transaction["timestamp"],
            reverse=True,
        )

    def _on_period_changed(self, label: str) -> None:
        for lbl, btn in self._period_btns:
            btn.setChecked(lbl == label)
        self._period = self._PERIOD_MAP[label]
        self.refresh()

    # ── Render semua section ──────────────────────────────────────────────────

    def _render_all(self) -> None:
        self._render_kpi_row()
        self._render_charts_row()
        self._render_orders_chart()
        self._render_activity_row()
        self._render_low_stock()

    @staticmethod
    def _clear_layout(layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    # ── KPI ───────────────────────────────────────────────────────────────────

    def _render_kpi_row(self) -> None:
        self._clear_layout(self._kpi_row_layout)
        kpi = self._data.get("kpi", {})

        cards = [
            ("Total Revenue",       f"Rp{kpi.get('total_revenue',   {}).get('value', 0):,.0f}",
             kpi.get("total_revenue",   {}).get("change_pct", 0)),
            ("Total Transaksi",     str(kpi.get("total_orders",    {}).get("value", 0)),
             kpi.get("total_orders",    {}).get("change_pct", 0)),
            ("Member Aktif",        str(kpi.get("active_members",  {}).get("value", 0)),
             kpi.get("active_members",  {}).get("change_pct", 0)),
            ("Rata-rata Transaksi", f"Rp{kpi.get('avg_order_value', {}).get('value', 0):,.0f}",
             kpi.get("avg_order_value", {}).get("change_pct", 0)),
        ]

        for title, value, change_pct in cards:
            self._kpi_row_layout.addWidget(self._kpi_card(title, value, change_pct))

    def _kpi_card(self, title: str, value: str, change_pct: float) -> QWidget:
        w = QWidget()
        w.setStyleSheet(
            f"QWidget {{ background:{BG_SURFACE}; border:1px solid {BORDER}; "
            f"border-radius:10px; padding:16px; }}"
        )
        v = QVBoxLayout(w)
        v.setSpacing(4)
        v.addWidget(make_label(title, 11, color="#64748b"))
        v.addWidget(make_label(value, 20, bold=True))

        arrow   = "▲" if change_pct >= 0 else "▼"
        color   = SUCCESS if change_pct >= 0 else "#dc2626"
        vs_text = {
            "daily": "kemarin", "weekly": "minggu lalu",
            "monthly": "bulan lalu", "annually": "tahun lalu",
        }.get(self._period, "periode lalu")
        v.addWidget(make_label(f"{arrow} {abs(change_pct):.1f}% vs {vs_text}", 11, color=color))
        return w

    # ── Charts row ────────────────────────────────────────────────────────────

    def _render_charts_row(self) -> None:
        self._clear_layout(self._charts_row_layout)
        self._charts_row_layout.addWidget(self._revenue_chart())
        self._charts_row_layout.addWidget(self._category_chart())

    def _revenue_chart(self) -> QGroupBox:
        trend = self._data.get("revenue_trend", [])

        grp = QGroupBox("Tren Revenue (Rp)")
        grp.setStyleSheet(
            f"QGroupBox {{ background:{BG_SURFACE}; border:1px solid {BORDER}; border-radius:10px; }}"
        )
        v = QVBoxLayout(grp)

        if not trend:
            v.addWidget(make_label("Belum ada data transaksi.", 11, color="#64748b"))
            return grp

        max_rev = max((r["revenue"] for r in trend), default=1) or 1
        for item in trend:
            row = QHBoxLayout()
            row.addWidget(make_label(item["month"], 11, color="#64748b"))

            bar_w = max(4, int((item["revenue"] / max_rev) * 200))
            bar = QFrame()
            bar.setFixedSize(bar_w, 14)
            bar.setStyleSheet(f"background:{PRIMARY}; border-radius:3px;")
            row.addWidget(bar)

            rev_txt = f"Rp{item['revenue'] / 1_000_000:.1f}jt" if item["revenue"] >= 1_000_000 \
                      else f"Rp{item['revenue']:,.0f}"
            row.addWidget(make_label(rev_txt, 11))
            row.addStretch()
            v.addLayout(row)

        return group_box

    def _category_chart(self) -> QGroupBox:
        cats = self._data.get("sales_by_category", [])

        grp = QGroupBox("Penjualan per Kategori")
        grp.setStyleSheet(
            f"QGroupBox {{ background:{BG_SURFACE}; border:1px solid {BORDER}; border-radius:10px; }}"
        )
        v = QVBoxLayout(grp)

        if not cats:
            v.addWidget(make_label("Belum ada data penjualan.", 11, color="#64748b"))
            return grp

        for i, item in enumerate(cats[:6]):
            color   = _CAT_COLORS[i % len(_CAT_COLORS)]
            section = QVBoxLayout()

            hdr = QHBoxLayout()
            hdr.addWidget(make_label(item["category"], 11))
            hdr.addStretch()
            hdr.addWidget(make_label(f"{item['pct']}%", 11, bold=True))
            section.addLayout(hdr)

            bar = QProgressBar()
            bar.setValue(item["pct"])
            bar.setFixedHeight(8)
            bar.setStyleSheet(
                f"QProgressBar {{ background:#e2e8f0; border-radius:4px; border:none; }}"
                f"QProgressBar::chunk {{ background:{color}; border-radius:4px; }}"
            )
            section.addWidget(bar)
            v.addLayout(section)
            v.addSpacing(4)

        return grp

    # ── Orders bar chart ──────────────────────────────────────────────────────

    def _render_orders_chart(self) -> None:
        self._clear_layout(self._orders_layout)
        self._orders_layout.addWidget(self._build_orders_chart())

    def _build_orders_chart(self) -> QGroupBox:
        trend = self._data.get("revenue_trend", [])

        grp = QGroupBox("Jumlah Transaksi per Bulan")
        grp.setStyleSheet(
            f"QGroupBox {{ background:{BG_SURFACE}; border:1px solid {BORDER}; border-radius:10px; }}"
        )
        h = QHBoxLayout(grp)

        if not trend:
            h.addWidget(make_label("Belum ada data transaksi.", 11, color="#64748b"))
            return grp

        max_ord = max((r["orders"] for r in trend), default=1) or 1
        for item in trend:
            col = QVBoxLayout()
            col.setAlignment(Qt.AlignmentFlag.AlignBottom)
            col.addStretch()

            bar_h = max(4, int((item["orders"] / max_ord) * 80))
            bar = QFrame()
            bar.setFixedSize(32, max(8, int((total_order / max_orders) * 80)))
            bar.setStyleSheet(f"background:{SUCCESS}; border-radius:4px;")
            col.addWidget(bar, alignment=Qt.AlignmentFlag.AlignHCenter)
            col.addWidget(make_label(str(item["orders"]), 10, color="#64748b"),
                          alignment=Qt.AlignmentFlag.AlignHCenter)
            col.addWidget(make_label(item["month"], 10, color="#94a3b8"),
                          alignment=Qt.AlignmentFlag.AlignHCenter)
            h.addLayout(col)

        return grp

    # ── Activity row ──────────────────────────────────────────────────────────

    def _render_activity_row(self) -> None:
        self._clear_layout(self._activity_row_layout)
        self._activity_row_layout.addWidget(self._recent_transactions())
        self._activity_row_layout.addWidget(self._top_members())

    def _recent_transactions(self) -> QGroupBox:
        trx_list = self._data.get("recent_transactions", [])

        grp = QGroupBox("Transaksi Terbaru")
        grp.setStyleSheet(
            f"QGroupBox {{ background:{BG_SURFACE}; border:1px solid {BORDER}; border-radius:10px; }}"
        )

        layout = QVBoxLayout(group_box)

        if not trx_list:
            v.addWidget(make_label("Belum ada transaksi.", 11, color="#64748b"))
            return grp

        for t in trx_list:
            row = QHBoxLayout()

            left = QVBoxLayout()
            left.addWidget(make_label(t["order_id"], 12, bold=True))
            # order_date bisa "2024-06-01 14:30:00" → tampilkan tanggal & waktu
            date_str = str(t["order_date"])
            left.addWidget(make_label(date_str[:16], 11, color="#64748b"))
            row.addLayout(left)
            row.addStretch()

            right = QVBoxLayout()
            right.addWidget(
                make_label(f"Rp{t['total']:,.0f}", 12, bold=True),
                alignment=Qt.AlignmentFlag.AlignRight,
            )
            right.addWidget(
                make_label(t["payment_method"].capitalize(), 11, color="#64748b"),
                alignment=Qt.AlignmentFlag.AlignRight,
            )
            row.addLayout(right)

            v.addLayout(row)
            v.addWidget(h_line())

        return group_box

    def _top_members(self) -> QGroupBox:
        members = self._data.get("top_members", [])

        grp = QGroupBox("Member Teratas")
        grp.setStyleSheet(
            f"QGroupBox {{ background:{BG_SURFACE}; border:1px solid {BORDER}; border-radius:10px; }}"
        )

        layout = QVBoxLayout(group_box)
        customer_data = defaultdict(lambda: {"spent": 0, "orders": 0})

        if not members:
            v.addWidget(make_label("Belum ada data member.", 11, color="#64748b"))
            return grp

        for c in members:
            row = QHBoxLayout()

            name = c.get("member_name", "-")
            initials = "".join(n[0].upper() for n in name.split()[:2])
            avatar = QLabel(initials)
            avatar.setFixedSize(36, 36)
            avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            avatar.setStyleSheet(
                f"background:#ede9fe; color:{PRIMARY}; border-radius:18px; font-weight:bold;"
            )

            row_layout.addWidget(avatar)

            info = QVBoxLayout()
            info.addWidget(make_label(name, 12, bold=True))
            info.addWidget(make_label(f"{c['visit_count']} kunjungan", 11, color="#64748b"))
            row.addLayout(info)
            row.addStretch()

            right = QVBoxLayout()
            right.addWidget(
                make_label(f"Rp{c['spent']:,.0f}", 12, bold=True),
                alignment=Qt.AlignmentFlag.AlignRight,
            )
            right.addWidget(
                make_label(f"{c['total_point']} poin", 11, color="#64748b"),
                alignment=Qt.AlignmentFlag.AlignRight,
            )
            row.addLayout(right)

            v.addLayout(row)
            v.addWidget(h_line())

        return grp

    # ── Low stock alert ───────────────────────────────────────────────────────

    def _render_low_stock(self) -> None:
        self._clear_layout(self._stock_layout)
        low = self._data.get("low_stock", [])
        if low:
            self._stock_layout.addWidget(self._low_stock_card(low))

    def _low_stock_card(self, items: list[dict]) -> QGroupBox:
        grp = QGroupBox("⚠️  Stok Menipis")
        grp.setStyleSheet(
            f"QGroupBox {{ background:#fff7ed; border:1px solid #fdba74; border-radius:10px; }}"
        )
        v = QVBoxLayout(grp)

        for item in items:
            row = QHBoxLayout()
            row.addWidget(make_label(item["product_name"], 12, bold=True))
            row.addWidget(make_label(f"[{item['category']}]", 11, color="#64748b"))
            row.addStretch()
            stock_color = "#dc2626" if item["stock"] == 0 else WARNING
            row.addWidget(make_label(f"Toko: {item['stock']}", 11, color=stock_color, bold=True))
            row.addWidget(make_label(f"  Gudang: {item['stock_storage']}", 11, color="#64748b"))
            v.addLayout(row)

        return grp