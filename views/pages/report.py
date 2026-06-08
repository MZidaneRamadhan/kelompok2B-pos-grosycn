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
from database import TransactionRepository


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

        self.select_all_cb = QCheckBox("Select All Transactions")
        self.select_all_cb.stateChanged.connect(self._toggle_select_all)
        lay.addWidget(self.select_all_cb)

        lay.addWidget(self._build_table())

        self._refresh()

    def refresh_data(self) -> None:
        """Refresh report contents from SQLite."""
        self._refresh()

    # ── Builder helpers ───────────────────────────────────────────────────────

    def _build_filter_card(self) -> QGroupBox:
        grp = QGroupBox("Pembuat Laporan")
        grp.setStyleSheet(
            f"QGroupBox {{ background:{BG_SURFACE}; border:1px solid {BORDER}; border-radius:10px; }}"
        )
        fl = QGridLayout(grp)

        # Payment method
        fl.addWidget(make_label("Payment Method", 11, color="#64748b"), 0, 0)
        self.pay_combo = QComboBox()
        self.pay_combo.addItems(["All Methods", "card", "cash", "mobile", "qris", "transfer"])
        self.pay_combo.currentTextChanged.connect(self._refresh)
        fl.addWidget(self.pay_combo, 1, 0)

        # Member filter
        fl.addWidget(make_label("Customer Type", 11, color="#64748b"), 0, 1)
        self.member_combo = QComboBox()
        self.member_combo.addItems(["All", "Member", "Non-Member"])
        self.member_combo.currentTextChanged.connect(self._refresh)
        fl.addWidget(self.member_combo, 1, 1)

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
        fl.addLayout(export_row, 2, 0, 1, 2)

        return grp

    def _build_table(self) -> QTreeWidget:
        self.table = QTreeWidget()
        self.table.setColumnCount(6)
        self.table.setHeaderLabels(
            ["Transaction ID", "Date", "Time", "Total", "Payment","Member"]
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
        pay    = self.pay_combo.currentText()
        member = self.member_combo.currentText()

        # Ambil semua transaksi dari SQLite via TransactionRepository
        db_rows = TransactionRepository.get_all()

        rows = []
        for row in db_rows:
            txn = dict(row)

            txn_transaction_id = str(txn.get("id", "")).lower()
            txn_payment = str(txn.get("payment_method", "")).lower()
            txn_is_member = bool(txn.get("is_member", 0))

            # Filter payment method
            if pay != "All Methods" and txn_payment != pay.lower():
                continue

            # Filter member/non-member
            if member == "Member" and not txn_is_member:
                continue
            if member == "Non-Member" and txn_is_member:
                continue

            # Pisah tanggal dan waktu dari order_date
            order_date = str(txn.get("order_date", ""))
            date_part = order_date.split(" ")[0] if " " in order_date else order_date
            time_part = order_date.split(" ")[1] if " " in order_date else ""

            rows.append({
                "db_id":         txn.get("id"),          # PK integer untuk lazy-fetch items
                "id":            txn_transaction_id,
                "order_id":      txn.get("order_id", ""),
                "date":          date_part,
                "time":          time_part,
                "customer_name": txn.get("customer_name") or "-",
                "total":         float(txn.get("total", 0)),
                "payment":       txn_payment,
                "is_member":     txn_is_member,
                "cashier":       txn.get("cashier", ""),
                "items":         [],  # diisi lazy saat double-click / export
            })

        self._rebuild_stats(rows)
        self._populate_table(rows)

    def _rebuild_stats(self, rows: list[dict]) -> None:
        # Bersihkan stat cards sebelumnya
        while self.stats_row.count():
            item = self.stats_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        total_rev = sum(t["total"] for t in rows)
        avg       = total_rev / len(rows) if rows else 0.0
        members   = sum(bool(t["is_member"])
                    for t in rows)

        for title, val in [
            ("Total Revenue",  f"Rp{total_rev:,.0f}"),
            ("Transactions",   str(len(rows))),
            ("Avg Order",      f"Rp{avg:,.0f}"),
            ("Member Trx",     str(members)),
        ]:
            card = QWidget()
            card.setStyleSheet(f"{card_style()} min-width:140px;")
            cv = QVBoxLayout(card)
            cv.addWidget(make_label(title, 11, color="#64748b"))
            cv.addWidget(make_label(val, 18, bold=True))
            self.stats_row.addWidget(card)

        self.stats_row.addStretch()

    def _populate_table(self, rows: list[dict]) -> None:
        self.table.clear()
        for t in rows:
            top = QTreeWidgetItem([
                t.get("order_id", str(t["id"])),
                t["date"],
                t["time"],
                f"Rp{t['total']:,.0f}",
                t["payment"].capitalize(),
                "Member" if t["is_member"] else "Umum",
            ])
            top.setFlags(top.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            top.setCheckState(0, Qt.CheckState.Unchecked)
            # Simpan db_id (integer PK) — items di-fetch lazy saat double-click
            top.setData(0, Qt.ItemDataRole.UserRole, t["db_id"])
            # Simpan full trx dict untuk export (termasuk items nanti)
            top.setData(1, Qt.ItemDataRole.UserRole, t)
            self.table.addTopLevelItem(top)

    def _show_transaction_detail(self, item: QTreeWidgetItem, column: int) -> None:
        trx_id = item.data(0, Qt.ItemDataRole.UserRole)
        if not trx_id:
            return
 
        # Fetch header + items dari SQLite
        from models import kasir as backend
        trx = backend.get_transaction(trx_id)
        if not trx:
            return
 
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Transaksi: {trx.get('order_id', trx_id)}")
        dlg.setFixedWidth(440)
 
        lay = QVBoxLayout(dlg)
        lay.setSpacing(16)
        lay.setContentsMargins(24, 24, 24, 24)
 
        icon = QLabel("🛒")
        icon.setFixedSize(56, 56)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(
            "background:#e0e7ff; color:#4f46e5; border-radius:28px; font-size:24px;"
        )
        lay.addWidget(icon, alignment=Qt.AlignmentFlag.AlignHCenter)
        lay.addWidget(
            make_label(trx.get("order_id", str(trx_id)), 16, bold=True),
            alignment=Qt.AlignmentFlag.AlignHCenter,
        )
 
        sep = QWidget(); sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{BORDER};")
        lay.addWidget(sep)
 
        form = QFormLayout()
        order_date = trx.get("order_date", "")
        date_part  = order_date[:10] if order_date else "-"
        time_part  = order_date[11:16] if len(order_date) > 10 else "-"
        form.addRow(
            make_label("Tanggal", 11, color="#64748b"),
            make_label(f"{date_part}  {time_part}", 12),
        )
        form.addRow(
            make_label("Pembayaran", 11, color="#64748b"),
            make_label(str(trx.get("payment_method", "-")).capitalize(), 12),
        )
        form.addRow(
            make_label("Pelanggan", 11, color="#64748b"),
            make_label(trx.get("customer_name") or "Umum", 12),
        )
        form.addRow(
            make_label("Total", 11, color="#64748b"),
            make_label(f"Rp{trx.get('total', 0):,.0f}", 12, bold=True),
        )
        lay.addLayout(form)
 
        lay.addWidget(make_label("Item yang Dibeli", 12, bold=True))
 
        items_lay = QVBoxLayout()
        items_lay.setContentsMargins(12, 12, 12, 12)
        items_lay.setSpacing(6)
 
        db_items = trx.get("items", [])
        if db_items:
            for i in db_items:
                # Kolom SQLite: product_name, quantity, subtotal
                name     = i.get("product_name") or i.get("name", "Unknown")
                qty      = i.get("quantity") or i.get("qty", 1)
                subtotal = i.get("subtotal", 0)
 
                row_lay = QHBoxLayout()
                row_lay.addWidget(make_label(f"{qty}×", 11, bold=True))
                row_lay.addWidget(make_label(name, 11))
                row_lay.addStretch()
                row_lay.addWidget(make_label(f"Rp{subtotal:,.0f}", 11))
                items_lay.addLayout(row_lay)
        else:
            items_lay.addWidget(make_label("Tidak ada data item.", 11, color="#94a3b8"))
 
        items_container = QWidget()
        items_container.setObjectName("itemsContainer")
        items_container.setStyleSheet(
            "QWidget#itemsContainer {"
            f" background:{BG_SURFACE}; border:1px solid {BORDER}; border-radius:8px; }}"
        )
        items_container.setLayout(items_lay)
        lay.addWidget(items_container)
 
        close_btn = QPushButton("Tutup")
        close_btn.setStyleSheet(
            f"QPushButton {{ background:transparent; border:1px solid {BORDER};"
            f" border-radius:8px; padding:7px 16px; font-size:12px; }}"
            f"QPushButton:hover {{ background:#f1f5f9; }}"
        )
        close_btn.clicked.connect(dlg.accept)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        lay.addLayout(btn_row)
 
        dlg.exec()

    def _get_selected_transactions(self) -> list[dict]:
        """Ambil transaksi yang dicentang, lengkap dengan items dari SQLite."""
        from models import kasir as backend
        selected = []
        for i in range(self.table.topLevelItemCount()):
            item = self.table.topLevelItem(i)
            if item and item.checkState(0) == Qt.CheckState.Checked:
                db_id = item.data(0, Qt.ItemDataRole.UserRole)
                if db_id:
                    trx = backend.get_transaction(db_id)
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
                writer.writerow(["Transaction ID", "Date", "Time", "Payment", "Total", "Item Name", "Item Qty", "Item Subtotal"])
                for trx in selected:
                    if not trx["items"]:
                        writer.writerow([trx["id"], trx["date"], trx["time"], trx["payment"], trx["total"], "", "", ""])
                    else:
                        for idx, item in enumerate(trx["items"]):
                            name = item.get("product_name") or item.get("name", "-")
                            qty  = item.get("quantity") or item.get("qty", 1)
                            if idx == 0:
                                writer.writerow([trx.get("order_id", trx.get("id")), trx.get("order_date","")[:10], trx.get("order_date","")[11:16], trx.get("payment_method", trx.get("payment","")), trx.get("total", 0), name, qty, item.get("subtotal", 0)])
                            else:
                                writer.writerow(["", "", "", "", "", name, qty, item.get("subtotal", 0)])
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
            self._extracted_from__export_excel_14(selected, path)
        except Exception as e:
            self.status_msg.emit(f"Error exporting Excel: {e}")

    # TODO Rename this here and in `_export_excel`
    def _extracted_from__export_excel_14(self, selected, path):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Transactions"
        ws.append(["Transaction ID", "Date", "Time", "Payment",  "Total", "Item Name", "Item Qty", "Item Subtotal"])

        for trx in selected:
            order_id  = trx.get("order_id", str(trx.get("id", "")))
            date_str  = str(trx.get("order_date", ""))
            date_part = date_str[:10]
            time_part = date_str[11:16]
            payment   = trx.get("payment_method", trx.get("payment", ""))
            total     = trx.get("total", 0)
            if not trx["items"]:
                ws.append([order_id, date_part, time_part, payment, total, "", "", ""])
            else:
                for idx, item in enumerate(trx["items"]):
                    name = item.get("product_name") or item.get("name", "-")
                    qty  = item.get("quantity") or item.get("qty", 1)
                    if idx == 0:
                        ws.append([order_id, date_part, time_part, payment, total, name, qty, item.get("subtotal", 0)])
                    else:
                        ws.append(["", "", "", "", "", name, qty, item.get("subtotal", 0)])

        wb.save(path)
        self.status_msg.emit("Successfully exported Excel!")

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
            html += "<tr><th>ID</th><th>Date</th><th>Total</th><th>Payment</th></tr>"

            for trx in selected:
                html += f"<tr><td><b>{trx['id']}</b></td><td>{trx['date']} {trx['time']}</td>"
                html += f"<td>{trx['total']}</td><td>{trx['payment']}</td></tr>"
                if trx["items"]:
                    html += "<tr><td colspan='4'>"
                    html += "<ul>"
                    for item in trx["items"]:
                        name = item.get("product_name") or item.get("name", "-")
                        qty  = item.get("quantity") or item.get("qty", 1)
                        html += f"<li>{name} - {qty} - Rp{item.get('subtotal', 0):,.0f}</li>"
                    html += "</ul></td></tr>"

            html += "</table>"

            # FIX: QPdfWriter di PyQt6 memerlukan QPainter agar rendering bisa
            # berjalan, dan PDF baru benar-benar di-flush ke disk setelah
            # painter.end() dipanggil. Tanpa painter.end(), file kosong/tidak tersimpan.
            from PyQt6.QtGui import QPainter

            writer = QPdfWriter(path)
            writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
            writer.setResolution(96)

            doc = QTextDocument()
            doc.setPageSize(
                writer.pageLayout().paintRectPixels(writer.resolution()).size().toSizeF()
            )
            doc.setHtml(html)

            painter = QPainter()
            if not painter.begin(writer):
                self.status_msg.emit("Error: tidak bisa membuka file PDF untuk ditulis.")
                return

            doc.drawContents(painter)
            painter.end()   # ← flush & simpan PDF ke disk

            self.status_msg.emit("Successfully exported PDF!")
        except Exception as e:
            self.status_msg.emit(f"Error exporting PDF: {e}")