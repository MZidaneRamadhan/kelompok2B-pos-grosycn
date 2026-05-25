from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from views.styles.palettes import BG_SURFACE, BORDER, PINK, PRIMARY, SUCCESS, WARNING
from views.styles.theme_manager import h_line, make_label

BASE_DIR = Path(__file__).resolve().parents[2]
TRANSACTION_FILE = BASE_DIR / "database_transaksi.json"

CATEGORY_COLORS = [PRIMARY, SUCCESS, WARNING, PINK]
TIME_FILTERS = {
    0: 1,
    1: 7,
    2: 30,
    3: 365,
}


class PieChartWidget(QWidget):
    def __init__(self, categories: list[tuple[str, int, str]], parent=None) -> None:
        super().__init__(parent)
        self.categories = categories
        self.setMinimumHeight(180)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(20, 10, 140, 140)
        total = max(sum(value for _, value, _ in self.categories), 1)
        start_angle = 0

        for _, value, color in self.categories:
            span_angle = int((value / total) * 360 * 16)
            painter.setBrush(QColor(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPie(rect, start_angle, span_angle)
            start_angle += span_angle


class DashboardPage(QWidget):
    """Dashboard penjualan berbasis data transaksi aktual."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.current_period = 2
        self.transactions = []
        self.filtered_transactions = []

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(20)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.header_layout = self._build_header()
        self.main_layout.addLayout(self.header_layout)

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(20)
        self.main_layout.addWidget(self.content_widget)

        self._refresh_dashboard()

    def _build_header(self) -> QHBoxLayout:
        header_layout = QHBoxLayout()

        title_layout = QVBoxLayout()
        title_layout.addWidget(make_label("Dashboard", 20, bold=True))
        title_layout.addWidget(
            make_label("Overview operasional dan transaksi toko", 12, color="#64748b")
        )

        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        self.time_tabs = QTabWidget()
        self.time_tabs.setMaximumWidth(380)

        for label in ("Harian", "Mingguan", "Bulanan", "Tahunan"):
            self.time_tabs.addTab(QWidget(), label)

        self.time_tabs.setCurrentIndex(self.current_period)
        self.time_tabs.currentChanged.connect(self._refresh_dashboard)

        header_layout.addWidget(self.time_tabs)
        return header_layout

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

    def _build_kpi_row(self) -> QHBoxLayout:
        total_revenue = sum(
            transaction["total_amount"] for transaction in self.filtered_transactions
        )

        total_transactions = len(self.filtered_transactions)
        active_customers = len(
            {transaction["customer_name"] for transaction in self.filtered_transactions}
        )

        average_order = (
            total_revenue / total_transactions if total_transactions else 0
        )

        kpi_data = [
            ("Total Revenue", self._format_currency(total_revenue)),
            ("Jumlah Transaksi", str(total_transactions)),
            ("Pelanggan Aktif", str(active_customers)),
            ("Rata-rata Order", self._format_currency(average_order)),
        ]

        row_layout = QHBoxLayout()

        for title, value in kpi_data:
            row_layout.addWidget(self._kpi_card(title, value))

        return row_layout

    def _build_charts_row(self) -> QHBoxLayout:
        row_layout = QHBoxLayout()
        row_layout.addWidget(self._revenue_chart())
        row_layout.addWidget(self._category_chart())
        return row_layout

    def _build_activity_row(self) -> QHBoxLayout:
        row_layout = QHBoxLayout()
        row_layout.addWidget(self._recent_transactions())
        row_layout.addWidget(self._top_customers())
        return row_layout

    def _kpi_card(self, title: str, value: str) -> QWidget:
        widget = QWidget()
        widget.setStyleSheet(
            f"QWidget {{ background:{BG_SURFACE}; border:1px solid {BORDER}; "
            f"border-radius:10px; padding:16px; }}"
        )

        layout = QVBoxLayout(widget)
        layout.addWidget(make_label(title, 11, color="#64748b"))
        layout.addWidget(make_label(value, 20, bold=True))

        return widget

    def _revenue_chart(self) -> QGroupBox:
        group_box = QGroupBox("Tren Revenue")
        group_box.setStyleSheet(
            f"QGroupBox {{ background:{BG_SURFACE}; border:1px solid {BORDER}; border-radius:10px; }}"
        )

        layout = QVBoxLayout(group_box)
        monthly_revenue = defaultdict(int)

        for transaction in self.filtered_transactions:
            month = datetime.strptime(
                transaction["timestamp"], "%Y-%m-%d %H:%M:%S"
            ).strftime("%b")
            monthly_revenue[month] += transaction["total_amount"]

        max_revenue = max(monthly_revenue.values(), default=1)

        for month, revenue in monthly_revenue.items():
            row_layout = QHBoxLayout()
            row_layout.addWidget(make_label(month, 11, color="#64748b"))

            bar = QFrame()
            bar.setFixedSize(int((revenue / max_revenue) * 220), 14)
            bar.setStyleSheet(f"background:{PRIMARY}; border-radius:4px;")

            row_layout.addWidget(bar)
            row_layout.addWidget(make_label(self._format_currency(revenue), 11))
            row_layout.addStretch()

            layout.addLayout(row_layout)

        return group_box

    def _category_chart(self) -> QGroupBox:
        group_box = QGroupBox("Distribusi Penjualan")
        group_box.setStyleSheet(
            f"QGroupBox {{ background:{BG_SURFACE}; border:1px solid {BORDER}; border-radius:10px; }}"
        )

        layout = QVBoxLayout(group_box)
        categories = self._calculate_category_distribution()

        layout.addWidget(PieChartWidget(categories))

        for name, total, color in categories:
            row_layout = QHBoxLayout()

            indicator = QLabel()
            indicator.setFixedSize(12, 12)
            indicator.setStyleSheet(f"background:{color}; border-radius:6px;")

            row_layout.addWidget(indicator)
            row_layout.addWidget(make_label(name, 11))
            row_layout.addStretch()
            row_layout.addWidget(make_label(f"{total} item", 11, bold=True))

            layout.addLayout(row_layout)

        return group_box

    def _calculate_category_distribution(self) -> list[tuple[str, int, str]]:
        categories = defaultdict(int)

        for transaction in self.filtered_transactions:
            for item in transaction.get("items", []):
                product_name = item["name"].lower()

                if "minyak" in product_name or "gula" in product_name:
                    categories["Sembako"] += item["qty"]
                elif "sabun" in product_name or "clean" in product_name:
                    categories["Kebersihan"] += item["qty"]
                else:
                    categories["Lainnya"] += item["qty"]

        if not categories:
            categories["Belum Ada Data"] = 1

        result = []

        for index, (name, total) in enumerate(categories.items()):
            result.append((name, total, CATEGORY_COLORS[index % len(CATEGORY_COLORS)]))

        return result

    def _build_orders_chart(self) -> QGroupBox:
        group_box = QGroupBox("Jumlah Order per Bulan")
        group_box.setStyleSheet(
            f"QGroupBox {{ background:{BG_SURFACE}; border:1px solid {BORDER}; border-radius:10px; }}"
        )

        layout = QHBoxLayout(group_box)
        monthly_orders = defaultdict(int)

        for transaction in self.filtered_transactions:
            month = datetime.strptime(
                transaction["timestamp"], "%Y-%m-%d %H:%M:%S"
            ).strftime("%b")
            monthly_orders[month] += 1

        max_orders = max(monthly_orders.values(), default=1)

        for month, total_order in monthly_orders.items():
            column_layout = QVBoxLayout()
            column_layout.setAlignment(Qt.AlignmentFlag.AlignBottom)
            column_layout.addStretch()

            bar = QFrame()
            bar.setFixedSize(32, max(8, int((total_order / max_orders) * 80)))
            bar.setStyleSheet(f"background:{SUCCESS}; border-radius:4px;")

            column_layout.addWidget(bar, alignment=Qt.AlignmentFlag.AlignHCenter)
            column_layout.addWidget(
                make_label(str(total_order), 10, color="#64748b"),
                alignment=Qt.AlignmentFlag.AlignHCenter,
            )
            column_layout.addWidget(
                make_label(month, 10, color="#94a3b8"),
                alignment=Qt.AlignmentFlag.AlignHCenter,
            )

            layout.addLayout(column_layout)

        return group_box

    def _recent_transactions(self) -> QGroupBox:
        group_box = QGroupBox("Transaksi Terbaru")
        group_box.setStyleSheet(
            f"QGroupBox {{ background:{BG_SURFACE}; border:1px solid {BORDER}; border-radius:10px; }}"
        )

        layout = QVBoxLayout(group_box)

        for transaction in self.filtered_transactions[:5]:
            row_layout = QHBoxLayout()

            left_layout = QVBoxLayout()
            left_layout.addWidget(make_label(transaction["order_id"], 12, bold=True))
            left_layout.addWidget(
                make_label(transaction["timestamp"], 11, color="#64748b")
            )

            row_layout.addLayout(left_layout)
            row_layout.addStretch()

            right_layout = QVBoxLayout()
            right_layout.addWidget(
                make_label(
                    self._format_currency(transaction["total_amount"]),
                    12,
                    bold=True,
                ),
                alignment=Qt.AlignmentFlag.AlignRight,
            )
            right_layout.addWidget(
                make_label(transaction["payment_method"], 11, color="#64748b"),
                alignment=Qt.AlignmentFlag.AlignRight,
            )

            row_layout.addLayout(right_layout)
            layout.addLayout(row_layout)
            layout.addWidget(h_line())

        return group_box

    def _top_customers(self) -> QGroupBox:
        group_box = QGroupBox("Top Customer")
        group_box.setStyleSheet(
            f"QGroupBox {{ background:{BG_SURFACE}; border:1px solid {BORDER}; border-radius:10px; }}"
        )

        layout = QVBoxLayout(group_box)
        customer_data = defaultdict(lambda: {"spent": 0, "orders": 0})

        for transaction in self.filtered_transactions:
            customer_name = transaction["customer_name"]
            customer_data[customer_name]["spent"] += transaction["total_amount"]
            customer_data[customer_name]["orders"] += 1

        sorted_customers = sorted(
            customer_data.items(),
            key=lambda customer: customer[1]["spent"],
            reverse=True,
        )

        for customer_name, customer_info in sorted_customers[:5]:
            row_layout = QHBoxLayout()

            avatar = QLabel("".join(name[0] for name in customer_name.split()[:2]))
            avatar.setFixedSize(36, 36)
            avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            avatar.setStyleSheet(
                f"background:#ede9fe; color:{PRIMARY}; border-radius:18px; font-weight:bold;"
            )

            row_layout.addWidget(avatar)

            info_layout = QVBoxLayout()
            info_layout.addWidget(make_label(customer_name, 12, bold=True))
            info_layout.addWidget(
                make_label(
                    f"{customer_info['orders']} transaksi",
                    11,
                    color="#64748b",
                )
            )

            row_layout.addLayout(info_layout)
            row_layout.addStretch()

            row_layout.addWidget(
                make_label(
                    self._format_currency(customer_info["spent"]),
                    12,
                    bold=True,
                )
            )

            layout.addLayout(row_layout)
            layout.addWidget(h_line())

        return group_box

    @staticmethod
    def _format_currency(amount: float) -> str:
        return f"Rp {amount:,.0fa}".replace(",", ".")

    @staticmethod
    def _clear_layout(layout) -> None:
        while layout.count():
            item = layout.takeAt(0)

            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                DashboardPage._clear_layout(item.layout())
