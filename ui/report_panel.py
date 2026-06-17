from datetime import date
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
                               QTableWidgetItem, QHeaderView, QDialog, QFormLayout, QLineEdit,
                               QMessageBox, QFrame, QComboBox, QDateEdit, QFileDialog)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor
from services.report_service import ReportService
from services.rental_service import RentalService
from models.equipment import EquipmentType


class ReportPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("📊 收入统计报表")
        title.setStyleSheet("font-size: 17px; font-weight: bold; color: #2C3E50;")
        layout.addWidget(title)

        filter_frame = QFrame()
        filter_frame.setStyleSheet("background-color: white; border-radius: 8px;")
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(16, 12, 16, 12)
        filter_layout.setSpacing(12)

        today = date.today()
        first_day = date(today.year, today.month, 1)

        filter_layout.addWidget(QLabel("起始日期:"))
        self.start_date = QDateEdit(QDate(first_day.year, first_day.month, first_day.day))
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        self.start_date.setCalendarPopup(True)
        self.start_date.setStyleSheet("padding: 6px;")
        filter_layout.addWidget(self.start_date)

        filter_layout.addWidget(QLabel("结束日期:"))
        self.end_date = QDateEdit(QDate(today.year, today.month, today.day))
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        self.end_date.setCalendarPopup(True)
        self.end_date.setStyleSheet("padding: 6px;")
        filter_layout.addWidget(self.end_date)

        filter_layout.addWidget(QLabel("设备类型:"))
        self.type_combo = QComboBox()
        self.type_combo.addItem("全部类型", None)
        types = EquipmentType.get_all()
        for t in types:
            self.type_combo.addItem(f"{t.type_code} - {t.type_name}", t.id)
        self.type_combo.setStyleSheet("padding: 6px;")
        filter_layout.addWidget(self.type_combo)

        filter_layout.addWidget(QLabel("客户:"))
        self.customer_combo = QComboBox()
        self.customer_combo.addItem("全部客户", None)
        customers = RentalService.get_all_customers()
        for c in customers:
            name = c.customer_name if hasattr(c, 'customer_name') else c.get('customer_name', '')
            phone = c.phone if hasattr(c, 'phone') else c.get('phone', '')
            cid = c.id if hasattr(c, 'id') else c.get('id')
            self.customer_combo.addItem(f"{name} ({phone})", cid)
        self.customer_combo.setStyleSheet("padding: 6px;")
        filter_layout.addWidget(self.customer_combo)

        self.query_btn = QPushButton("🔍 查询")
        self.query_btn.setStyleSheet("""
            QPushButton { background-color: #1976D2; color: white; padding: 8px 18px; 
                          border: none; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #1565C0; }
        """)
        self.query_btn.clicked.connect(self._do_query)
        filter_layout.addWidget(self.query_btn)

        self.export_btn = QPushButton("📥 导出CSV")
        self.export_btn.setStyleSheet("""
            QPushButton { background-color: #4CAF50; color: white; padding: 8px 18px; 
                          border: none; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #388E3C; }
        """)
        self.export_btn.clicked.connect(self._export_csv)
        filter_layout.addWidget(self.export_btn)

        filter_layout.addStretch()
        layout.addWidget(filter_frame)

        summary_frame = QFrame()
        summary_frame.setStyleSheet("background-color: white; border-radius: 8px;")
        summary_layout = QHBoxLayout(summary_frame)
        summary_layout.setContentsMargins(16, 12, 16, 12)
        summary_layout.setSpacing(20)

        self.summary_base = self._make_summary_card("基础租金", "0.00", "#2196F3")
        self.summary_overtime = self._make_summary_card("超期罚金", "0.00", "#F44336")
        self.summary_total = self._make_summary_card("总收入", "0.00", "#4CAF50")
        self.summary_paid = self._make_summary_card("已收款", "0.00", "#8BC34A")
        self.summary_unpaid = self._make_summary_card("未收款", "0.00", "#FF9800")

        summary_layout.addLayout(self.summary_base["layout"])
        summary_layout.addLayout(self.summary_overtime["layout"])
        summary_layout.addLayout(self.summary_total["layout"])
        summary_layout.addLayout(self.summary_paid["layout"])
        summary_layout.addLayout(self.summary_unpaid["layout"])
        summary_layout.addStretch()
        layout.addWidget(summary_frame)

        table_frame = QFrame()
        table_frame.setStyleSheet("background-color: white; border-radius: 8px;")
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(16, 12, 16, 12)
        table_layout.setSpacing(8)

        table_title = QLabel("明细列表")
        table_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #2C3E50;")
        table_layout.addWidget(table_title)

        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "订单号", "客户", "设备类型", "起租时间", "归还时间",
            "基础租金", "超期罚金", "已收金额", "未收金额"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setStyleSheet("""
            QTableWidget { border: 1px solid #E0E0E0; border-radius: 4px; gridline-color: #EEE; }
            QHeaderView::section { background-color: #F8F9FA; padding: 8px; border: none;
                                   border-bottom: 1px solid #E0E0E0; font-weight: bold; color: #2C3E50; }
        """)
        table_layout.addWidget(self.table, 1)
        layout.addWidget(table_frame, 1)

        self._do_query()

    def _make_summary_card(self, label, value, color):
        layout = QVBoxLayout()
        layout.setSpacing(4)
        lbl = QLabel(label)
        lbl.setStyleSheet("font-size: 12px; color: #666;")
        layout.addWidget(lbl)
        val = QLabel(f"¥{value}")
        val.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {color};")
        val.setAlignment(Qt.AlignCenter)
        layout.addWidget(val)
        return {"layout": layout, "value": val}

    def _do_query(self):
        start = self.start_date.date().toString("yyyy-MM-dd")
        end = self.end_date.date().toString("yyyy-MM-dd")
        type_id = self.type_combo.currentData()
        customer_id = self.customer_combo.currentData()

        summary, records = ReportService.get_report_by_date_range(
            start, end, type_id=type_id, customer_id=customer_id
        )

        self.summary_base["value"].setText(f"¥{summary['base_amount']:.2f}")
        self.summary_overtime["value"].setText(f"¥{summary['overtime_amount']:.2f}")
        self.summary_total["value"].setText(f"¥{summary['total_amount']:.2f}")
        self.summary_paid["value"].setText(f"¥{summary['paid_amount']:.2f}")
        self.summary_unpaid["value"].setText(f"¥{summary['unpaid_amount']:.2f}")

        self.current_records = records
        self._populate_table(records)

    def _populate_table(self, records):
        self.table.setRowCount(len(records))
        for row, r in enumerate(records):
            self._set_item(self.table, row, 0, r["order_no"])
            self._set_item(self.table, row, 1, r.get("customer_name", ""))
            self._set_item(self.table, row, 2, r.get("type_name", ""))
            self._set_item(self.table, row, 3, r.get("rent_start", ""))
            self._set_item(self.table, row, 4, r.get("actual_return", ""))
            self._set_item(self.table, row, 5, f"¥{r['base_amount']:.2f}")
            self._set_item(self.table, row, 6, f"¥{r['overtime_amount']:.2f}")
            self._set_item(self.table, row, 7, f"¥{r['paid_amount']:.2f}")
            unpaid = r["total_amount"] - r["paid_amount"]
            self._set_item(self.table, row, 8, f"¥{unpaid:.2f}")
            if unpaid > 0:
                self.table.item(row, 8).setForeground(QColor("#F44336"))
        self.table.verticalHeader().setDefaultSectionSize(36)

    def _set_item(self, table, row, col, text):
        item = QTableWidgetItem(str(text))
        item.setTextAlignment(Qt.AlignCenter)
        table.setItem(row, col, item)

    def _export_csv(self):
        if not hasattr(self, 'current_records') or not self.current_records:
            QMessageBox.warning(self, "提示", "没有数据可导出")
            return
        file_name, _ = QFileDialog.getSaveFileName(
            self, "导出报表",
            f"收入报表_{date.today().strftime('%Y%m%d')}.csv",
            "CSV文件 (*.csv)"
        )
        if not file_name:
            return
        try:
            ok, msg = ReportService.export_to_csv_file(file_name, self.current_records)
            if ok:
                QMessageBox.information(self, "成功", f"导出成功！\n文件: {file_name}")
            else:
                QMessageBox.warning(self, "失败", msg)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
