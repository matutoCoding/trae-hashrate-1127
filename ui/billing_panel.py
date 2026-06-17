from datetime import datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
                               QTableWidgetItem, QHeaderView, QDialog, QMessageBox, QFrame,
                               QComboBox, QLineEdit, QDateEdit, QFormLayout, QDoubleSpinBox,
                               QDialogButtonBox, QTextEdit)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor
from services.rental_service import RentalService
from services.billing_service import BillingService
from utils.helpers import parse_datetime


class BillDetailDialog(QDialog):
    def __init__(self, order_id, parent=None):
        super().__init__(parent)
        self.order_id = order_id
        self.setWindowTitle("账单详情")
        self.setMinimumWidth(560)
        self.setMinimumHeight(500)
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        self.info_label = QLabel()
        self.info_label.setStyleSheet("""
            QLabel { background: #F5F7FA; padding: 12px; border-radius: 6px; font-size: 13px; }
        """)
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        segments_title = QLabel("📋 分段计费明细")
        segments_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #2C3E50;")
        layout.addWidget(segments_title)

        self.segments_table = QTableWidget()
        self.segments_table.setColumnCount(5)
        self.segments_table.setHorizontalHeaderLabels(["时段", "开始", "结束", "时长(h)", "金额"])
        self.segments_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.segments_table.verticalHeader().setVisible(False)
        self.segments_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.segments_table.setStyleSheet("""
            QTableWidget { border: 1px solid #E0E0E0; border-radius: 4px; gridline-color: #EEE; }
            QHeaderView::section { background-color: #F8F9FA; padding: 8px; border: none;
                                   border-bottom: 1px solid #E0E0E0; font-weight: bold; color: #2C3E50; }
        """)
        layout.addWidget(self.segments_table, 1)

        self.summary_label = QLabel()
        self.summary_label.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FFF3E0, stop:1 #FFE0B2);
                padding: 16px; border-radius: 6px; font-size: 13px;
            }
        """)
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        pay_layout = QHBoxLayout()
        pay_layout.setSpacing(8)

        self.pay_spin = QDoubleSpinBox()
        self.pay_spin.setRange(0, 1000000)
        self.pay_spin.setDecimals(2)
        self.pay_spin.setPrefix("¥ ")
        self.pay_spin.setStyleSheet("padding: 6px;")
        pay_layout.addWidget(QLabel("支付金额:"))
        pay_layout.addWidget(self.pay_spin, 1)

        self.pay_btn = QPushButton("💳 确认支付")
        self.pay_btn.setStyleSheet("""
            QPushButton { background-color: #4CAF50; color: white; padding: 8px 20px; 
                          border: none; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #388E3C; }
        """)
        self.pay_btn.clicked.connect(self._on_pay)
        pay_layout.addWidget(self.pay_btn)
        layout.addLayout(pay_layout)

        close_btn = QPushButton("关闭")
        close_btn.setStyleSheet("""
            QPushButton { background-color: #E0E0E0; color: #333; padding: 8px 24px; 
                          border: none; border-radius: 4px; }
            QPushButton:hover { background-color: #BDBDBD; }
        """)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _load_data(self):
        bill = RentalService.get_order_bill(self.order_id)
        if not bill:
            return
        order = bill["order"]

        self.info_label.setText(f"""
        <b>订单号:</b> {order.order_no} &nbsp;&nbsp;
        <b>状态:</b> {'已归还' if order.status == 'closed' else '租赁中'}<br>
        <b>起租:</b> {order.rent_start} &nbsp;&nbsp;
        <b>应还:</b> {order.rent_end}<br>
        <b>实还:</b> {order.actual_return or '-'} &nbsp;&nbsp;
        <b>押金:</b> ¥{order.deposit:.2f}<br>
        <b>已付:</b> ¥{order.paid_amount:.2f} &nbsp;&nbsp;
        <b>未付:</b> <span style='color:#F44336;font-weight:bold;'>¥{(order.total_amount - order.paid_amount):.2f}</span>
        """)

        segments = bill["segments"]
        self.segments_table.setRowCount(len(segments))
        for row, s in enumerate(segments):
            self._set_item(self.segments_table, row, 0, s["rate_name"])
            start_str = s["segment_start"] if isinstance(s["segment_start"], str) else str(s["segment_start"])
            end_str = s["segment_end"] if isinstance(s["segment_end"], str) else str(s["segment_end"])
            start_str = start_str.replace("T", " ")[:19]
            end_str = end_str.replace("T", " ")[:19]
            self._set_item(self.segments_table, row, 1, start_str)
            self._set_item(self.segments_table, row, 2, end_str)
            self._set_item(self.segments_table, row, 3, f"{s['hours']:.2f}")
            self._set_item(self.segments_table, row, 4, f"¥{s['segment_amount']:.2f}")
            if "超期" in s["rate_name"]:
                for c in range(5):
                    it = self.segments_table.item(row, c)
                    if it:
                        it.setForeground(QColor("#F44336"))
        self.segments_table.verticalHeader().setDefaultSectionSize(32)

        self.summary_label.setText(f"""
        <table width='100%'>
          <tr><td style='padding:4px;'>基础租金:</td><td style='padding:4px;text-align:right;'>¥{bill['base_amount']:.2f}</td></tr>
          <tr><td style='padding:4px;color:#F44336;'>超期罚金 (x1.5):</td><td style='padding:4px;text-align:right;color:#F44336;'>¥{bill['overtime_amount']:.2f}</td></tr>
          <tr><td style='padding:4px;'>总时长:</td><td style='padding:4px;text-align:right;'>{bill['total_hours']:.2f} 小时</td></tr>
          <tr><td style='padding:4px;'>已付金额:</td><td style='padding:4px;text-align:right;'>¥{order.paid_amount:.2f}</td></tr>
          <tr style='font-size:18px;'><td style='padding:8px 4px;font-weight:bold;'>应付总额:</td>
          <td style='padding:8px 4px;text-align:right;color:#FF5722;font-weight:bold;'>¥{bill['total_amount']:.2f}</td></tr>
        </table>
        """)

        unpaid = max(0, order.total_amount - order.paid_amount)
        self.pay_spin.setValue(unpaid)
        self.pay_btn.setEnabled(unpaid > 0)

    def _set_item(self, table, row, col, text):
        item = QTableWidgetItem(str(text))
        item.setTextAlignment(Qt.AlignCenter)
        table.setItem(row, col, item)

    def _on_pay(self):
        amount = self.pay_spin.value()
        if amount <= 0:
            QMessageBox.warning(self, "提示", "请输入支付金额")
            return
        ok, msg = RentalService.pay_order(self.order_id, amount)
        if ok:
            QMessageBox.information(self, "成功", f"支付成功 ¥{amount:.2f}")
            self._load_data()
        else:
            QMessageBox.warning(self, "失败", msg)


class BillingPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        filter_bar = QFrame()
        filter_bar.setStyleSheet("background-color: white; border-radius: 8px;")
        f_layout = QHBoxLayout(filter_bar)
        f_layout.setContentsMargins(16, 12, 16, 12)
        f_layout.setSpacing(12)

        f_layout.addWidget(QLabel("状态:"))
        self.status_combo = QComboBox()
        self.status_combo.addItem("全部", "all")
        self.status_combo.addItem("租赁中", "active")
        self.status_combo.addItem("已归还", "closed")
        self.status_combo.setStyleSheet("padding: 6px;")
        self.status_combo.currentIndexChanged.connect(self._apply_filter)
        f_layout.addWidget(self.status_combo)

        f_layout.addWidget(QLabel("订单号:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入订单号搜索...")
        self.search_edit.setStyleSheet("padding: 6px 8px; border: 1px solid #CCC; border-radius: 4px;")
        self.search_edit.textChanged.connect(self._apply_filter)
        f_layout.addWidget(self.search_edit, 1)

        self.total_label = QLabel("")
        self.total_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #FF5722;")
        f_layout.addStretch()
        f_layout.addWidget(self.total_label)
        layout.addWidget(filter_bar)

        table_frame = QFrame()
        table_frame.setStyleSheet("background-color: white; border-radius: 8px;")
        t_layout = QVBoxLayout(table_frame)
        t_layout.setContentsMargins(12, 12, 12, 12)

        self.table = QTableWidget()
        self.table.setColumnCount(12)
        self.table.setHorizontalHeaderLabels([
            "订单号", "客户", "设备类型", "设备编码",
            "起租", "应还", "实还",
            "基础租金", "超期罚金", "总金额", "已付", "操作"
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
        t_layout.addWidget(self.table)
        layout.addWidget(table_frame, 1)

    def refresh_data(self):
        self._all_orders = RentalService.get_all_orders()
        self._apply_filter()

    def _apply_filter(self):
        status_filter = self.status_combo.currentData()
        search = self.search_edit.text().strip().lower()

        filtered = self._all_orders
        if status_filter != "all":
            filtered = [o for o in filtered if o["status"] == status_filter]
        if search:
            filtered = [o for o in filtered if search in o["order_no"].lower()]

        self.table.setRowCount(len(filtered))
        total = 0.0
        unpaid = 0.0
        for row, o in enumerate(filtered):
            self._set_item(self.table, row, 0, o["order_no"])
            self._set_item(self.table, row, 1, o.get("customer_name", ""))
            self._set_item(self.table, row, 2, o["type_name"])
            self._set_item(self.table, row, 3, o["item_code"])
            self._set_item(self.table, row, 4, o["rent_start"])
            self._set_item(self.table, row, 5, o["rent_end"])
            self._set_item(self.table, row, 6, o.get("actual_return", "-"))
            self._set_item(self.table, row, 7, f"¥{o['base_amount']:.2f}")
            self._set_item(self.table, row, 8, f"¥{o['overtime_amount']:.2f}")
            if o["overtime_amount"] > 0:
                self.table.item(row, 8).setForeground(QColor("#F44336"))
            self._set_item(self.table, row, 9, f"¥{o['total_amount']:.2f}")
            self.table.item(row, 9).setForeground(QColor("#FF5722"))
            self._set_item(self.table, row, 10, f"¥{o['paid_amount']:.2f} / ¥{o['total_amount']:.2f}")

            total += o["total_amount"]
            unpaid += max(0, o["total_amount"] - o["paid_amount"])

            if o["status"] == "active":
                rent_end = parse_datetime(o["rent_end"])
                if rent_end and rent_end < datetime.now():
                    for c in range(11):
                        it = self.table.item(row, c)
                        if it:
                            it.setForeground(QColor("#F44336"))

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(6)
            btn_layout.addStretch()
            view_btn = QPushButton("查看账单")
            view_btn.setStyleSheet("""
                QPushButton { background-color: #1976D2; color: white; padding: 4px 12px; 
                              border: none; border-radius: 3px; font-size: 12px; }
                QPushButton:hover { background-color: #1565C0; }
            """)
            view_btn.clicked.connect(lambda _, oid=o["id"]: self._view_bill(oid))
            btn_layout.addWidget(view_btn)
            btn_layout.addStretch()
            self.table.setCellWidget(row, 11, btn_widget)
        self.table.verticalHeader().setDefaultSectionSize(38)

        self.total_label.setText(f"总金额: ¥{total:.2f}  |  未收: ¥{unpaid:.2f}")

    def _set_item(self, table, row, col, text):
        item = QTableWidgetItem(str(text))
        item.setTextAlignment(Qt.AlignCenter)
        table.setItem(row, col, item)

    def _view_bill(self, order_id):
        dlg = BillDetailDialog(order_id, self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh_data()
