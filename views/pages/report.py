# ─────────────────────────────────────────────────────────────────────────────
# views/pages/report.py
# ─────────────────────────────────────────────────────────────────────────────

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QComboBox, QGroupBox, QGridLayout, QTreeWidget,
    QTreeWidgetItem, QHeaderView, QFileDialog, QCheckBox,
    QDialog, QFormLayout, QLabel
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor, QPdfWriter, QTextDocument, QPageSize

import csv
import openpyxl

from views.styles.theme_manager import make_label, card_style
from views.styles.palettes import DANGER_FG, WARNING_FG, SUCCESS_FG, BG_SURFACE, BORDER
from models import kasir as backend

# Foreground colour per transaction status
_STATUS_FG = {
    "completed": SUCCESS_FG,
    "refunded": DANGER_FG,
    "pending": WARNING_FG,
}


class ReportsPage(QWidget):
    """Report builder: filter transactions, view summary KPIs, export."""

    status_msg = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        lay = QVBoxLayout(self)
        lay.setSpacing(16)
        lay.setContentsMargins(0, 0, 0, 0)

        lay.addWidget(make_label("Laporan", 18, bold=True))
        lay.addWidget(make_label("Buat dan ekspor laporan bisnis", 12, color="#64748b"))

        lay.addWidget(self._build_filter_card())

        # Summary stat cards (rebuilt on every filter change)
        self.stats_row = QHBoxLayout()
        lay.addLayout(self.stats_row)

        self.select_all_cb = QCheckBox("Pilih Semua Transaksi")
        self.select_all_cb.stateChanged.connect(self._toggle_select_all)
        lay.addWidget(self.select_all_cb)

        lay.addWidget(self._build_table())

        self._refresh()

    def refresh_data(self) -> None:
        """Refresh report contents from transaction storage."""
        self._refresh()

    # ── Builder helpers ───────────────────────────────────────────────────────

    def _build_filter_card(self) -> QGroupBox:
        grp = QGroupBox("Pembuat Laporan")
        grp.setStyleSheet(
            f"QGroupBox {{ background:{BG_SURFACE}; border:1px solid {BORDER}; border-radius:10px; }}"
        )
        fl = QGridLayout(grp)

        # Location
        fl.addWidget(make_label("Lokasi", 11, color="#64748b"), 0, 0)
        self.loc_combo = QComboBox()
        self.loc_combo.addItems(["Semua Lokasi"])
        self.loc_combo.currentTextChanged.connect(self._refresh)
        fl.addWidget(self.loc_combo, 1, 0)

        # Payment method
        fl.addWidget(make_label("Metode Pembayaran", 11, color="#64748b"), 0, 1)
        self.pay_combo = QComboBox()
        self.pay_combo.addItems(["Semua Metode", "card", "cash", "mobile"])
        self.pay_combo.currentTextChanged.connect(self._refresh)
        fl.addWidget(self.pay_combo, 1, 1)

        # Status
        fl.addWidget(make_label("Status", 11, color="#64748b"), 0, 2)
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Semua Status", "completed", "refunded", "pending"])
        self.status_combo.currentTextChanged.connect(self._refresh)
        fl.addWidget(self.status_combo, 1, 2)

        # Export buttons
        export_row = QHBoxLayout()

        btn_pdf = QPushButton("⬇  PDF")
        btn_pdf.setObjectName("btnOutline")
        btn_pdf.clicked.connect(self._export_pdf)
        export_row.addWidget(btn_pdf)

        btn_csv = QPushButton("⬇  CSV")
        btn_csv.setObjectName("btnOutline")
        btn_csv.clicked.connect(self._export_csv)
        export_row.addWidget(btn_csv)

        btn_excel = QPushButton("⬇  Excel")
        btn_excel.setObjectName("btnOutline")
        btn_excel.clicked.connect(self._export_excel)
        export_row.addWidget(btn_excel)

        export_row.addStretch()
        fl.addLayout(export_row, 2, 0, 1, 3)

        return grp

    def _build_table(self) -> QTreeWidget:
        self.table = QTreeWidget()
        self.table.setColumnCount(6)
        self.table.setHeaderLabels(
            ["ID Transaksi", "Date", "Time", "Total", "Payment", "Status"]
        )
        self.table.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(False)
        self.table.itemDoubleClicked.connect(self._show_transaction_detail)
        return self.table

    # ── Data ─────────────────────────────────────────────────────────────────

    def _toggle_select_all(self, state: int) -> None:
        check_state = Qt.CheckState.Checked if state else Qt.CheckState.Unchecked
        for i in range(self.table.topLevelItemCount()):
            item = self.table.topLevelItem(i)
            if item:
                item.setCheckState(0, check_state)

    def _refresh(self) -> None:
        loc = self.loc_combo.currentText()
        pay = self.pay_combo.currentText()
        st = self.status_combo.currentText()

        db_transactions = backend.load_json(backend.FILE_TRANSAKSI)

        rows = []
        for transaction_id, txn in db_transactions.items():
            txn_status = str(txn.get("status", "")).lower()
            txn_payment = str(txn.get("payment_method", txn.get("payment", ""))).lower()
            txn_location = str(txn.get("location", "Semua Lokasi"))

            if loc != "Semua Lokasi" and txn_location != loc:
                continue
            if pay != "Semua Metode" and txn_payment != pay.lower():
                continue
            if st != "Semua Status" and txn_status != st.lower():
                continue

            rows.append({
                "id": transaction_id,
                "date": txn.get("timestamp", "").split(" ")[0],
                "time": txn.get("timestamp", "").split(" ")[1] if " " in txn.get("timestamp", "") else "",
                "total": float(txn.get("total_amount", txn.get("total", 0))),
                "payment": txn_payment,
                "status": txn_status,
                "items": txn.get("items", [])
            })

        self._rebuild_stats(rows)
        self._populate_table(rows)

    def _rebuild_stats(self, rows: list[dict]) -> None:
        # Clear previous stat cards
        while self.stats_row.count():
            item = self.stats_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        total_rev = sum(t["total"] for t in rows)
        avg = total_rev / len(rows) if rows else 0.0

        for title, val in [
            ("Total Revenue", f"Rp{total_rev:,.0f}"),
            ("Transactions", str(len(rows))),
            ("Avg Order", f"Rp{avg:,.0f}"),
        ]:
            card = QWidget()
            card.setStyleSheet(card_style() + " min-width:140px;")
            cv = QVBoxLayout(card)
            cv.addWidget(make_label(title, 11, color="#64748b"))
            cv.addWidget(make_label(val, 18, bold=True))
            self.stats_row.addWidget(card)

        self.stats_row.addStretch()

    def _populate_table(self, rows: list[dict]) -> None:
        self.table.clear()
        for t in rows:
            parent = QTreeWidgetItem(self.table)
            parent.setText(0, t["id"])
            parent.setCheckState(0, Qt.CheckState.Unchecked)
            parent.setText(1, t["date"])
            parent.setText(2, t["time"])
            parent.setText(3, f"Rp{t['total']:,.0f}")
            parent.setText(4, t["payment"].capitalize())

            fg = _STATUS_FG.get(t["status"], "#0f172a")
            parent.setText(5, t["status"].capitalize())
            parent.setForeground(5, QColor(fg))

            # Store the full transaction data in the item
            parent.setData(0, Qt.ItemDataRole.UserRole, t)

    def _show_transaction_detail(self, item: QTreeWidgetItem, column: int) -> None:
        trx = item.data(0, Qt.ItemDataRole.UserRole)
        if not trx:
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Transaction: {trx['id']}")
        dlg.setFixedWidth(400)

        lay = QVBoxLayout(dlg)
        lay.setSpacing(16)
        lay.setContentsMargins(24, 24, 24, 24)

        icon = QLabel("🛒")
        icon.setFixedSize(56, 56)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("background:#e0e7ff; color:#4f46e5; border-radius:28px; font-size:24px;")

        lay.addWidget(icon, alignment=Qt.AlignmentFlag.AlignHCenter)
        lay.addWidget(make_label(trx["id"], 16, bold=True), alignment=Qt.AlignmentFlag.AlignHCenter)

        status_lbl = QLabel(trx["status"].capitalize())
        fg = _STATUS_FG.get(trx["status"], "#0f172a")
        status_lbl.setStyleSheet(
            f"background:#f1f5f9; color:{fg}; border-radius:6px; padding:4px 12px; font-weight:bold;")
        status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(status_lbl, alignment=Qt.AlignmentFlag.AlignHCenter)

        line = QWidget()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background:{BORDER};")
        lay.addWidget(line)

        form = QFormLayout()
        form.addRow(make_label("Date", 11, color="#64748b"), make_label(f"{trx['date']} {trx['time']}", 12))
        form.addRow(make_label("Payment", 11, color="#64748b"), make_label(trx["payment"].capitalize(), 12))
        form.addRow(make_label("Total", 11, color="#64748b"), make_label(f"Rp{trx['total']:,.0f}", 12, bold=True))
        lay.addLayout(form)

        lay.addWidget(make_label("Items Purchased", 12, bold=True))

        items_lay = QVBoxLayout()
        items_lay.setContentsMargins(12, 12, 12, 12)
        for i in trx.get("items", []):
            item_row = QHBoxLayout()
            item_row.addWidget(make_label(f"{i.get('qty', 1)}x", 11, bold=True))
            item_row.addWidget(make_label(i.get('name', 'Unknown'), 11))
            item_row.addStretch()
            item_row.addWidget(make_label(f"Rp{i.get('subtotal', 0):,.0f}", 11))
            items_lay.addLayout(item_row)

        items_container = QWidget()
        items_container.setStyleSheet(f"background:{BG_SURFACE}; border:1px solid {BORDER}; border-radius:8px;")
        items_container.setLayout(items_lay)
        lay.addWidget(items_container)

        close_btn = QPushButton("Tutup")
        close_btn.setStyleSheet(
            f"QPushButton {{ background:transparent; border:1px solid {BORDER}; border-radius:8px; padding:7px 16px; font-size:12px;}} QPushButton:hover {{ background:#f1f5f9; }}")
        close_btn.clicked.connect(dlg.accept)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        lay.addLayout(btn_row)

        dlg.exec()

    def _get_selected_transactions(self) -> list[dict]:
        """Helper to get checked transactions from the tree."""
        selected = []
        for i in range(self.table.topLevelItemCount()):
            item = self.table.topLevelItem(i)
            if item.checkState(0) == Qt.CheckState.Checked:
                trx = item.data(0, Qt.ItemDataRole.UserRole)
                if trx:
                    selected.append(trx)
        return selected

    def _export_csv(self) -> None:
        selected = self._get_selected_transactions()
        if not selected:
            self.status_msg.emit("Please select at least one transaction to export.")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Save CSV", "", "CSV Files (*.csv)")
        if not path:
            return
        if not path.lower().endswith('.csv'):
            path += '.csv'

        try:
            with open(path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["ID Transaksi", "Date", "Time", "Payment", "Status", "Total", "Item Name", "Item Qty",
                                 "Item Subtotal"])
                for trx in selected:
                    if not trx["items"]:
                        writer.writerow(
                            [trx["id"], trx["date"], trx["time"], trx["payment"], trx["status"], trx["total"], "", "",
                             ""])
                    else:
                        for idx, item in enumerate(trx["items"]):
                            if idx == 0:
                                writer.writerow(
                                    [trx["id"], trx["date"], trx["time"], trx["payment"], trx["status"], trx["total"],
                                     item["name"], item["qty"], item["subtotal"]])
                            else:
                                writer.writerow(["", "", "", "", "", "", item["name"], item["qty"], item["subtotal"]])
            self.status_msg.emit("Successfully exported CSV!")
        except Exception as e:
            self.status_msg.emit(f"Error exporting CSV: {e}")

    def _export_excel(self) -> None:
        selected = self._get_selected_transactions()
        if not selected:
            self.status_msg.emit("Please select at least one transaction to export.")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Save Excel", "", "Excel Files (*.xlsx)")
        if not path:
            return
        if not path.lower().endswith('.xlsx'):
            path += '.xlsx'

        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Transactions"
            ws.append(["ID Transaksi", "Date", "Time", "Payment", "Status", "Total", "Item Name", "Item Qty",
                       "Item Subtotal"])

            for trx in selected:
                if not trx["items"]:
                    ws.append(
                        [trx["id"], trx["date"], trx["time"], trx["payment"], trx["status"], trx["total"], "", "", ""])
                else:
                    for idx, item in enumerate(trx["items"]):
                        if idx == 0:
                            ws.append([trx["id"], trx["date"], trx["time"], trx["payment"], trx["status"], trx["total"],
                                       item["name"], item["qty"], item["subtotal"]])
                        else:
                            ws.append(["", "", "", "", "", "", item["name"], item["qty"], item["subtotal"]])

            wb.save(path)
            self.status_msg.emit("Successfully exported Excel!")
        except Exception as e:
            self.status_msg.emit(f"Error exporting Excel: {e}")

    def _export_pdf(self) -> None:
        selected = self._get_selected_transactions()
        if not selected:
            self.status_msg.emit("Please select at least one transaction to export.")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Save PDF", "", "PDF Files (*.pdf)")
        if not path:
            return
        if not path.lower().endswith('.pdf'):
            path += '.pdf'

        try:
            html = "<h1>Transaction Report</h1>"
            html += "<table border='1' cellspacing='0' cellpadding='5' width='100%'>"
            html += "<tr><th>ID</th><th>Date</th><th>Total</th><th>Payment</th><th>Status</th></tr>"

            for trx in selected:
                html += f"<tr><td><b>{trx['id']}</b></td><td>{trx['date']} {trx['time']}</td>"
                html += f"<td>{trx['total']}</td><td>{trx['payment']}</td><td>{trx['status']}</td></tr>"
                if trx["items"]:
                    html += "<tr><td colspan='5'>"
                    html += "<ul>"
                    for item in trx["items"]:
                        html += f"<li>{item['name']} - {item['qty']} - {item['subtotal']}</li>"
                    html += "</ul></td></tr>"

            html += "</table>"

            doc = QTextDocument()
            doc.setHtml(html)

            printer = QPdfWriter(path)
            printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
            doc.print(printer)
            self.status_msg.emit("Successfully exported PDF!")
        except Exception as e:
            self.status_msg.emit(f"Error exporting PDF: {e}")
