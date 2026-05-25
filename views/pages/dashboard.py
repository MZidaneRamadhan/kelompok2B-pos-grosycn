# ─────────────────────────────────────────────────────────────────────────────
# views/pages/dashboard.py
# ─────────────────────────────────────────────────────────────────────────────

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QFrame, QProgressBar, QTabWidget,
)
from PyQt6.QtCore import Qt

from views.styles.theme_manager import make_label, h_line
from views.styles.palettes import PRIMARY, SUCCESS, WARNING, PINK, BG_SURFACE, BORDER
from data.store import CUSTOMERS, TRANSACTIONS, REVENUE_DATA


class DashboardPage(QWidget):
    """Overview page: KPI cards, mini charts, recent activity."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        lay = QVBoxLayout(self)
        lay.setSpacing(20)
        lay.setContentsMargins(0, 0, 0, 0)

        lay.addLayout(self._build_header())
        lay.addLayout(self._build_kpi_row())
        lay.addLayout(self._build_charts_row())
        lay.addWidget(self._build_orders_chart())
        lay.addLayout(self._build_activity_row())
        lay.addStretch()

    # ── Sections ──────────────────────────────────────────────────────────────

    def _build_header(self) -> QHBoxLayout:
        hdr = QHBoxLayout()

        title_col = QVBoxLayout()
        title_col.addWidget(make_label("Dasbor", 20, bold=True))
        title_col.addWidget(make_label("Ringkasan operasional grosir Anda", 12, color="#64748b"))
        hdr.addLayout(title_col)
        hdr.addStretch()

        time_tabs = QTabWidget()
        time_tabs.setMaximumWidth(380)
        for label in ("Harian", "Mingguan", "Bulanan", "Tahunan"):
            time_tabs.addTab(QWidget(), label)
        time_tabs.setCurrentIndex(2)
        # Sambungkan perubahan tab ke slot refresh dashboard
        time_tabs.currentChanged.connect(self._on_period_changed)
        hdr.addWidget(time_tabs)

        return hdr

    def _on_period_changed(self, period_index: int) -> None:
        """Dipanggil saat tab Harian/Mingguan/Bulanan/Tahunan berubah."""
        period_labels = ["Harian", "Mingguan", "Bulanan", "Tahunan"]
        # TODO: Setelah data dinamis dari database tersedia (isu #1),
        # implementasikan query dengan rentang tanggal berdasarkan period_index:
        # 0 = hari ini, 1 = 7 hari terakhir, 2 = 30 hari, 3 = 365 hari
        # Contoh: WHERE order_date BETWEEN ? AND ?
        period = period_labels[period_index] if period_index < len(period_labels) else "Bulanan"
        print(f"[Dashboard] Filter periode diubah ke: {period}")
        # self._refresh_kpi(period_index)  # aktifkan setelah data dinamis tersedia

    def _build_kpi_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        kpis = [
            ("Total Pendapatan",   "Rp 185.750.000", "+18.5%"),
            ("Pesanan Grosir",     "342",       "+12.8%"),
            ("Klien Aktif",  "127",       "+9.3%"),
            ("Rata-rata Nilai Pesanan", "Rp 543.120",   "+5.7%"),
        ]
        for title, value, change in kpis:
            row.addWidget(self._kpi_card(title, value, change))
        return row

    def _build_charts_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(self._revenue_chart())
        row.addWidget(self._category_chart())
        return row

    def _build_activity_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(self._recent_transactions())
        row.addWidget(self._top_customers())
        return row

    # ── Card builders ─────────────────────────────────────────────────────────

    def _kpi_card(self, title: str, value: str, change: str) -> QWidget:
        w = QWidget()
        w.setStyleSheet(
            f"QWidget {{ background:{BG_SURFACE}; border:1px solid {BORDER}; "
            f"border-radius:10px; padding:16px; }}"
        )
        v = QVBoxLayout(w)
        v.setSpacing(4)
        v.addWidget(make_label(title, 11, color="#64748b"))
        v.addWidget(make_label(value, 20, bold=True))
        # Tampilkan panah naik/turun berdasarkan nilai perubahan
        is_positive = not str(change).startswith("-")
        arrow = "▲" if is_positive else "▼"
        arrow_color = SUCCESS if is_positive else "#DC2626"
        v.addWidget(make_label(f"{arrow} {change} vs periode lalu", 11, color=arrow_color))
        return w

    def _revenue_chart(self) -> QGroupBox:
        grp = QGroupBox("Tren Pendapatan (Rp000)")
        grp.setStyleSheet(
            f"QGroupBox {{ background:{BG_SURFACE}; border:1px solid {BORDER}; border-radius:10px; }}"
        )
        v = QVBoxLayout(grp)

        max_rev = max(r for _, r, _ in REVENUE_DATA)
        for month, rev, _ in REVENUE_DATA:
            row = QHBoxLayout()
            row.addWidget(make_label(month, 11, color="#64748b"))
            bar_w = int((rev / max_rev) * 200)
            bar = QFrame()
            bar.setFixedSize(bar_w, 14)
            bar.setStyleSheet(f"background:{PRIMARY}; border-radius:3px;")
            row.addWidget(bar)
            row.addWidget(make_label(f"Rp{rev // 1000}rb", 11))
            row.addStretch()
            v.addLayout(row)

        return grp

    def _category_chart(self) -> QGroupBox:
        grp = QGroupBox("Penjualan per Kategori")
        grp.setStyleSheet(
            f"QGroupBox {{ background:{BG_SURFACE}; border:1px solid {BORDER}; border-radius:10px; }}"
        )
        v = QVBoxLayout(grp)

        cats = [
            ("Office Supplies",   35, PRIMARY),
            ("Electronics",       25, SUCCESS),
            ("Health & Safety",   20, WARNING),
            ("Cleaning Supplies", 20, PINK),
        ]
        for name, pct, color in cats:
            section = QVBoxLayout()
            hdr = QHBoxLayout()
            hdr.addWidget(make_label(name, 11))
            hdr.addStretch()
            hdr.addWidget(make_label(f"{pct}%", 11, bold=True))
            section.addLayout(hdr)

            bar = QProgressBar()
            bar.setValue(pct)
            bar.setFixedHeight(8)
            bar.setStyleSheet(
                f"QProgressBar {{ background:#e2e8f0; border-radius:4px; border:none; }}"
                f"QProgressBar::chunk {{ background:{color}; border-radius:4px; }}"
            )
            section.addWidget(bar)
            v.addLayout(section)
            v.addSpacing(4)

        return grp

    def _build_orders_chart(self) -> QGroupBox:
        grp = QGroupBox("Pesanan per Bulan")
        grp.setStyleSheet(
            f"QGroupBox {{ background:{BG_SURFACE}; border:1px solid {BORDER}; border-radius:10px; }}"
        )
        h = QHBoxLayout(grp)

        max_ord = max(o for _, _, o in REVENUE_DATA)
        for month, _, orders in REVENUE_DATA:
            col = QVBoxLayout()
            col.setAlignment(Qt.AlignmentFlag.AlignBottom)
            col.addStretch()

            bar_h = max(4, int((orders / max_ord) * 80))
            bar = QFrame()
            bar.setFixedSize(32, bar_h)
            bar.setStyleSheet(f"background:{SUCCESS}; border-radius:4px;")
            col.addWidget(bar, alignment=Qt.AlignmentFlag.AlignHCenter)
            col.addWidget(make_label(str(orders), 10, color="#64748b"), alignment=Qt.AlignmentFlag.AlignHCenter)
            col.addWidget(make_label(month, 10, color="#94a3b8"), alignment=Qt.AlignmentFlag.AlignHCenter)
            h.addLayout(col)

        return grp

    def _recent_transactions(self) -> QGroupBox:
        grp = QGroupBox("Transaksi Terbaru")
        grp.setStyleSheet(
            f"QGroupBox {{ background:{BG_SURFACE}; border:1px solid {BORDER}; border-radius:10px; }}"
        )
        v = QVBoxLayout(grp)

        for t in TRANSACTIONS[:5]:
            row = QHBoxLayout()
            left = QVBoxLayout()
            left.addWidget(make_label(t["id"], 12, bold=True))
            left.addWidget(make_label(f"{t['date']}  {t['time']}", 11, color="#64748b"))
            row.addLayout(left)
            row.addStretch()
            right = QVBoxLayout()
            right.addWidget(
                make_label(f"Rp {t['total']:,.0f}", 12, bold=True),
                alignment=Qt.AlignmentFlag.AlignRight,
            )
            right.addWidget(
                make_label(t["payment"].capitalize(), 11, color="#64748b"),
                alignment=Qt.AlignmentFlag.AlignRight,
            )
            row.addLayout(right)
            v.addLayout(row)
            v.addWidget(h_line())

        return grp

    def _top_customers(self) -> QGroupBox:
        grp = QGroupBox("Pelanggan Teratas")
        grp.setStyleSheet(
            f"QGroupBox {{ background:{BG_SURFACE}; border:1px solid {BORDER}; border-radius:10px; }}"
        )
        v = QVBoxLayout(grp)

        for c in sorted(CUSTOMERS, key=lambda c: c["spent"], reverse=True)[:5]:
            row = QHBoxLayout()

            initials = "".join(n[0] for n in c["name"].split())
            avatar = QLabel(initials)
            avatar.setFixedSize(36, 36)
            avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            avatar.setStyleSheet(
                f"background:#ede9fe; color:{PRIMARY}; border-radius:18px; font-weight:bold;"
            )
            row.addWidget(avatar)

            info = QVBoxLayout()
            info.addWidget(make_label(c["name"], 12, bold=True))
            info.addWidget(make_label(f"{c['visits']} kunjungan", 11, color="#64748b"))
            row.addLayout(info)
            row.addStretch()

            right = QVBoxLayout()
            right.addWidget(
                make_label(f"Rp {c['spent']:,.0f}", 12, bold=True),
                alignment=Qt.AlignmentFlag.AlignRight,
            )
            right.addWidget(
                make_label(f"{c['points']} pts", 11, color="#64748b"),
                alignment=Qt.AlignmentFlag.AlignRight,
            )
            row.addLayout(right)

            v.addLayout(row)
            v.addWidget(h_line())

        return grp
