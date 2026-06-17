from datetime import datetime, timedelta
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
                               QTableWidgetItem, QHeaderView, QDialog, QFormLayout, QLineEdit,
                               QDoubleSpinBox, QDialogButtonBox, QMessageBox, QFrame, QDateTimeEdit,
                               QComboBox, QTabWidget, QGroupBox, QSizePolicy)
from PySide6.QtCore import Qt, Signal, QDateTime
from PySide6.QtGui import QColor
from services.rental_service import RentalService
from services.equipment_service import EquipmentService
from services.billing_service import BillingService
from utils.helpers import format_datetime, parse_datetime, generate_order_no


class RentDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设备租赁出库")
        self.setMinimumWidth(520)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        form = QFormLayout()
        form.setSpacing(12)

        self.customer_combo = QComboBox()
        self.customer_combo.setStyleSheet("padding: 6px;")
        self.customer_combo.addItem("（新客户，下方填写）", None)
        for c in RentalService.get_all_customers():
            self.customer_combo.addItem(f"{c.customer_name} - {c.phone or '无电话'}", c.id)
        form.addRow("选择客户:", self.customer_combo)

        self.customer_name = QLineEdit()
        self.customer_name.setPlaceholderText("新客户姓名")
        self.customer_name.setStyleSheet("padding: 6px 8px; border: 1px solid #CCC; border-radius: 4px;")
        form.addRow("客户姓名*:", self.customer_name)

        self.customer_phone = QLineEdit()
        self.customer_phone.setPlaceholderText("联系电话")
        self.customer_phone.setStyleSheet("padding: 6px 8px; border: 1px solid #CCC; border-radius: 4px;")
        form.addRow("电话:", self.customer_phone)

        self.type_combo = QComboBox()
        self.type_combo.setStyleSheet("padding: 6px;")
        self.stats = EquipmentService.get_type_stats()
        for s in self.stats:
            self.type_combo.addItem(
                f"{s['type_code']} - {s['type_name']}  (可租: {s['available'] or 0}台)",
                s["id"]
            )
        self.type_combo.currentIndexChanged.connect(self._update_preview)
        form.addRow("设备类型*:", self.type_combo)

        now = datetime.now()
        self.start_edit = QDateTimeEdit(QDateTime(now.year, now.month, now.day, now.hour, now.minute))
        self.start_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.start_edit.setCalendarPopup(True)
        self.start_edit.setStyleSheet("padding: 6px;")
        self.start_edit.dateTimeChanged.connect(self._update_preview)
        form.addRow("起租时间*:", self.start_edit)

        default_end = now + timedelta(hours=24)
        self.end_edit = QDateTimeEdit(QDateTime(default_end.year, default_end.month, default_end.day,
                                                 default_end.hour, default_end.minute))
        self.end_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.end_edit.setCalendarPopup(True)
        self.end_edit.setStyleSheet("padding: 6px;")
        self.end_edit.dateTimeChanged.connect(self._update_preview)
        form.addRow("预计归还*:", self.end_edit)

        self.deposit_spin = QDoubleSpinBox()
        self.deposit_spin.setRange(0, 100000)
        self.deposit_spin.setDecimals(2)
        self.deposit_spin.setPrefix("¥ ")
        self.deposit_spin.setValue(200)
        self.deposit_spin.setStyleSheet("padding: 6px;")
        form.addRow("押金:", self.deposit_spin)

        layout.addLayout(form)

        self.preview_box = QGroupBox("📊 费用预览")
        self.preview_box.setStyleSheet("""
            QGroupBox {
                border: 2px solid #E3F2FD;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 12px;
                font-weight: bold;
                color: #1976D2;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 6px; }
        """)
        preview_layout = QVBoxLayout(self.preview_box)
        self.preview_label = QLabel("请选择设备类型和时间...")
        self.preview_label.setStyleSheet("font-size: 13px; color: #555;")
        self.preview_label.setWordWrap(True)
        preview_layout.addWidget(self.preview_label)
        layout.addWidget(self.preview_box)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.button(QDialogButtonBox.Ok).setText("✅ 确认租出")
        btn_box.button(QDialogButtonBox.Cancel).setText("取消")
        btn_box.button(QDialogButtonBox.Ok).setStyleSheet("""
            QPushButton { background-color: #4CAF50; color: white; padding: 10px 24px; 
                          border: none; border-radius: 4px; font-weight: bold; font-size: 14px; }
            QPushButton:hover { background-color: #388E3C; }
        """)
        btn_box.button(QDialogButtonBox.Cancel).setStyleSheet("""
            QPushButton { background-color: #E0E0E0; color: #333; padding: 10px 24px; 
                          border: none; border-radius: 4px; }
        """)
        btn_box.accepted.connect(self._on_accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        self._update_preview()

    def _update_preview(self):
        type_id = self.type_combo.currentData()
        start_str = self.start_edit.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        end_str = self.end_edit.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        result = BillingService.calculate_rental_cost(start_str, end_str)
        type_name = self.type_combo.currentText()
        html = f"""
        <p><b>设备:</b> {type_name}</p>
        <p><b>租期:</b> {start_str} ~ {end_str}</p>
        <p><b>总时长:</b> {result['total_hours']:.2f} 小时</p>
        <p><b>分段明细:</b> {"  ".join([f"{s['rate_name']}({s['hours']:.1f}h×¥{s['rate']:.0f}=¥{s['segment_amount']:.0f})" for s in result['segments']]) or '-'}</p>
        <p style="font-size: 20px; color: #FF5722; font-weight: bold; margin-top: 8px;">
           预估租金: ¥{result['total']:.2f}
        </p>
        """
        self.preview_label.setText(html)

    def _on_accept(self):
        if not self.customer_name.text().strip() and not self.customer_combo.currentData():
            QMessageBox.warning(self, "提示", "请选择或填写客户姓名")
            return
        if self.start_edit.dateTime() >= self.end_edit.dateTime():
            QMessageBox.warning(self, "提示", "归还时间必须晚于起租时间")
            return
        type_id = self.type_combo.currentData()
        available = EquipmentService.get_available_count_by_type(type_id)
        if available <= 0:
            QMessageBox.warning(self, "提示", "该类型设备无可租设备")
            return
        self.accept()

    def get_data(self):
        customer_id = self.customer_combo.currentData()
        if not customer_id:
            customer_id = RentalService.create_customer(
                self.customer_name.text().strip(),
                self.customer_phone.text().strip()
            )
        return {
            "customer_id": customer_id,
            "type_id": self.type_combo.currentData(),
            "rent_start": self.start_edit.dateTime().toString("yyyy-MM-dd HH:mm:ss"),
            "rent_end": self.end_edit.dateTime().toString("yyyy-MM-dd HH:mm:ss"),
            "deposit": self.deposit_spin.value()
        }


class ReturnDialog(QDialog):
    def __init__(self, order_info, parent=None):
        super().__init__(parent)
        self.order_info = order_info
        self.setWindowTitle("设备归还")
        self.setMinimumWidth(480)
        self._setup_ui()
        self._update_bill()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        info = QLabel(f"订单: {self.order_info['order_no']} | 客户: {self.order_info.get('customer_name','')} | "
                      f"设备: {self.order_info['type_name']} - {self.order_info['item_code']}")
        info.setStyleSheet("font-size: 13px; color: #555; padding: 8px; background: #F5F7FA; border-radius: 4px;")
        layout.addWidget(info)

        form = QFormLayout()
        form.setSpacing(10)

        now = datetime.now()
        self.return_edit = QDateTimeEdit(QDateTime(now.year, now.month, now.day, now.hour, now.minute))
        self.return_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.return_edit.setCalendarPopup(True)
        self.return_edit.setStyleSheet("padding: 6px;")
        self.return_edit.dateTimeChanged.connect(self._update_bill)
        form.addRow("实际归还时间:", self.return_edit)

        self.pay_spin = QDoubleSpinBox()
        self.pay_spin.setRange(0, 100000)
        self.pay_spin.setDecimals(2)
        self.pay_spin.setPrefix("¥ ")
        self.pay_spin.setStyleSheet("padding: 6px;")
        form.addRow("本次支付:", self.pay_spin)
        layout.addLayout(form)

        self.bill_box = QGroupBox("💰 账单明细")
        self.bill_box.setStyleSheet("""
            QGroupBox {
                border: 2px solid #FFF3E0;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 12px;
                font-weight: bold;
                color: #FF9800;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 6px; }
        """)
        bill_layout = QVBoxLayout(self.bill_box)
        self.bill_label = QLabel()
        self.bill_label.setWordWrap(True)
        self.bill_label.setStyleSheet("font-size: 13px;")
        bill_layout.addWidget(self.bill_label)
        layout.addWidget(self.bill_box, 1)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.button(QDialogButtonBox.Ok).setText("✅ 确认归还并结算")
        btn_box.button(QDialogButtonBox.Cancel).setText("取消")
        btn_box.button(QDialogButtonBox.Ok).setStyleSheet("""
            QPushButton { background-color: #4CAF50; color: white; padding: 10px 24px; 
                          border: none; border-radius: 4px; font-weight: bold; font-size: 14px; }
        """)
        btn_box.button(QDialogButtonBox.Cancel).setStyleSheet("""
            QPushButton { background-color: #E0E0E0; color: #333; padding: 10px 24px; 
                          border: none; border-radius: 4px; }
        """)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _update_bill(self):
        return_str = self.return_edit.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        result = BillingService.calculate_full_bill(
            self.order_info["rent_start"],
            self.order_info["rent_end"],
            return_str
        )
        segments_html = ""
        for s in result["segments"]:
            color = "#F44336" if s.get("is_overtime") else "#1976D2"
            segments_html += (f'<tr><td style="padding:3px;">{s["rate_name"]}</td>'
                              f'<td style="padding:3px;text-align:center;">{s["hours"]:.2f}h</td>'
                              f'<td style="padding:3px;text-align:right;">¥{s["rate"]:.2f}</td>'
                              f'<td style="padding:3px;text-align:right;color:{color};font-weight:bold;">¥{s["segment_amount"]:.2f}</td></tr>')
        html = f"""
        <table style="width:100%;">
          <tr><td style="padding:3px;">起租:</td><td style="padding:3px;">{self.order_info['rent_start']}</td></tr>
          <tr><td style="padding:3px;">应还:</td><td style="padding:3px;">{self.order_info['rent_end']}</td></tr>
          <tr><td style="padding:3px;">实还:</td><td style="padding:3px;">{return_str}</td></tr>
          <tr><td style="padding:3px;">总时长:</td><td style="padding:3px;">{result['total_hours']:.2f}小时</td></tr>
        </table>
        <hr style="border:1px solid #EEE;">
        <table style="width:100%;font-size:12px;">
          <tr style="background:#F5F7FA;"><th style="padding:4px;text-align:left;">时段</th>
          <th style="padding:4px;">时长</th><th style="padding:4px;">费率</th>
          <th style="padding:4px;text-align:right;">金额</th></tr>
          {segments_html}
        </table>
        <hr style="border:1px solid #EEE;">
        <p style="margin:2px 0;">基础租金: <b>¥{result['base_amount']:.2f}</b></p>
        <p style="margin:2px 0;color:#F44336;">超期罚金(x1.5): <b>¥{result['overtime_amount']:.2f}</b> (超期{result['overtime_hours']:.2f}小时)</p>
        <p style="font-size:20px;color:#FF5722;font-weight:bold;text-align:right;margin-top:8px;">
          应付总额: ¥{result['total']:.2f}
        </p>
        """
        self.bill_label.setText(html)
        self.pay_spin.setValue(result["total"])

    def get_data(self):
        return {
            "actual_return": self.return_edit.dateTime().toString("yyyy-MM-dd HH:mm:ss"),
            "pay_amount": self.pay_spin.value()
        }


class RentalPanel(QWidget):
    order_created = Signal()
    order_returned = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        stats = QHBoxLayout()
        stats.setSpacing(16)

        self.active_card = self._make_card("租赁中订单", "0", "#1976D2")
        self.overdue_card = self._make_card("超期订单", "0", "#F44336")
        self.available_card = self._make_card("可租设备", "0", "#4CAF50")

        stats.addWidget(self.active_card, 1)
        stats.addWidget(self.overdue_card, 1)
        stats.addWidget(self.available_card, 1)
        layout.addLayout(stats)

        top = QHBoxLayout()
        info = QLabel("📌 设备按FIFO先进先出顺序自动发放，过期设备已锁定")
        info.setStyleSheet("color: #555; font-size: 13px;")
        top.addWidget(info)
        top.addStretch()

        self.rent_btn = QPushButton("➕ 新建租赁")
        self.rent_btn.setStyleSheet("""
            QPushButton { background-color: #4CAF50; color: white; padding: 10px 20px; 
                          border: none; border-radius: 4px; font-weight: bold; font-size: 14px; }
            QPushButton:hover { background-color: #388E3C; }
        """)
        self.rent_btn.clicked.connect(self._create_rental)
        top.addWidget(self.rent_btn)
        layout.addLayout(top)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #E0E0E0; border-radius: 8px; background: white; }
            QTabBar::tab { background: #F5F7FA; padding: 10px 20px; border: 1px solid #E0E0E0; 
                           border-bottom: none; border-top-left-radius: 6px; border-top-right-radius: 6px;
                           font-weight: bold; color: #555; }
            QTabBar::tab:selected { background: white; color: #1976D2; }
        """)

        self.active_widget = QWidget()
        self._setup_table(self.active_widget, "active")
        self.history_widget = QWidget()
        self._setup_table(self.history_widget, "history")

        self.tabs.addTab(self.active_widget, "🔵 租赁中")
        self.tabs.addTab(self.history_widget, "📜 历史订单")
        layout.addWidget(self.tabs, 1)

    def _make_card(self, title, value, color):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{ background-color: white; border-radius: 8px; border-left: 4px solid {color}; }}
        """)
        l = QVBoxLayout(card)
        l.setContentsMargins(20, 14, 20, 14)
        t = QLabel(title)
        t.setStyleSheet("color: #7F8C8D; font-size: 13px;")
        l.addWidget(t)
        v = QLabel(value)
        v.setStyleSheet(f"color: {color}; font-size: 26px; font-weight: bold;")
        l.addWidget(v)
        return card

    def _setup_table(self, widget, mode):
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        table = QTableWidget()
        columns = ["订单号", "客户", "电话", "设备类型", "设备编码", "批次",
                   "起租时间", "应还时间", "实还时间", "押金", "租金", "超期罚金", "状态", "操作"]
        if mode == "active":
            columns.remove("实还时间")
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setStyleSheet("""
            QTableWidget { border: 1px solid #E0E0E0; border-radius: 4px; gridline-color: #EEE; }
            QHeaderView::section { background-color: #F8F9FA; padding: 8px; border: none;
                                   border-bottom: 1px solid #E0E0E0; font-weight: bold; color: #2C3E50; }
        """)
        layout.addWidget(table)
        if mode == "active":
            self.active_table = table
        else:
            self.history_table = table

    def refresh_data(self):
        EquipmentService.check_and_lock_expired()

        active = RentalService.get_active_orders()
        overdue = RentalService.check_overdue_orders()
        self._update_card(self.active_card, str(len(active)))
        self._update_card(self.overdue_card, str(len(overdue)))

        type_stats = EquipmentService.get_type_stats()
        total_available = sum(s["available"] or 0 for s in type_stats)
        self._update_card(self.available_card, str(total_available))

        self._populate_table(self.active_table, active, "active")

        all_orders = RentalService.get_all_orders()
        closed = [o for o in all_orders if o["status"] == "closed"]
        self._populate_table(self.history_table, closed, "history")

    def _update_card(self, card, value):
        labels = card.findChildren(QLabel)
        if len(labels) >= 2:
            labels[1].setText(value)

    def _populate_table(self, table, orders, mode):
        table.setRowCount(len(orders))
        for row, o in enumerate(orders):
            self._set_item(table, row, 0, o["order_no"])
            self._set_item(table, row, 1, o.get("customer_name", ""))
            self._set_item(table, row, 2, o.get("phone", ""))
            self._set_item(table, row, 3, o["type_name"])
            self._set_item(table, row, 4, o["item_code"])
            self._set_item(table, row, 5, o["batch_no"])
            self._set_item(table, row, 6, o["rent_start"])
            self._set_item(table, row, 7, o["rent_end"])
            col_offset = 0
            if mode == "history":
                self._set_item(table, row, 8, o.get("actual_return", ""))
                col_offset = 1
            self._set_item(table, row, 8 + col_offset, f"¥{o['deposit']:.2f}")
            self._set_item(table, row, 9 + col_offset, f"¥{o['base_amount']:.2f}")
            self._set_item(table, row, 10 + col_offset, f"¥{o['overtime_amount']:.2f}")

            status_text_map = {"active": "租赁中", "closed": "已归还"}
            st = status_text_map.get(o["status"], o["status"])
            is_overdue = False
            if o["status"] == "active":
                rent_end = parse_datetime(o["rent_end"])
                if rent_end and rent_end < datetime.now():
                    st = "超期未还"
                    is_overdue = True
            self._set_item(table, row, 11 + col_offset, st)
            if is_overdue:
                for c in range(table.columnCount()):
                    it = table.item(row, c)
                    if it:
                        it.setForeground(QColor("#F44336"))

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(6)
            btn_layout.addStretch()
            if o["status"] == "active":
                return_btn = QPushButton("归还结算")
                return_btn.setStyleSheet("""
                    QPushButton { background-color: #4CAF50; color: white; padding: 4px 12px; 
                                  border: none; border-radius: 3px; font-size: 12px; }
                    QPushButton:hover { background-color: #388E3C; }
                """)
                return_btn.clicked.connect(lambda _, ord=o: self._return_equipment(ord))
                btn_layout.addWidget(return_btn)
            bill_btn = QPushButton("账单")
            bill_btn.setStyleSheet("""
                QPushButton { background-color: #FF9800; color: white; padding: 4px 12px; 
                              border: none; border-radius: 3px; font-size: 12px; }
                QPushButton:hover { background-color: #F57C00; }
            """)
            bill_btn.clicked.connect(lambda _, ord=o: self._show_bill(ord))
            btn_layout.addWidget(bill_btn)
            btn_layout.addStretch()
            table.setCellWidget(row, 12 + col_offset, btn_widget)
        table.verticalHeader().setDefaultSectionSize(38)

    def _set_item(self, table, row, col, text):
        item = QTableWidgetItem(str(text))
        item.setTextAlignment(Qt.AlignCenter)
        table.setItem(row, col, item)

    def _create_rental(self):
        dlg = RentDialog(self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            order_id, msg_or_no = RentalService.create_rental(**data)
            if order_id:
                QMessageBox.information(self, "成功", f"租赁成功！\n订单号: {msg_or_no}")
                self.refresh_data()
                self.order_created.emit()
            else:
                QMessageBox.warning(self, "失败", msg_or_no)

    def _return_equipment(self, order_info):
        dlg = ReturnDialog(order_info, self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            result, err = RentalService.return_equipment(order_info["id"], data["actual_return"])
            if result:
                if data["pay_amount"] > 0:
                    RentalService.pay_order(order_info["id"], data["pay_amount"])
                QMessageBox.information(self, "成功",
                    f"归还成功！\n"
                    f"基础租金: ¥{result['base_amount']:.2f}\n"
                    f"超期罚金: ¥{result['overtime_amount']:.2f}\n"
                    f"合计: ¥{result['total']:.2f}")
                self.refresh_data()
                self.order_returned.emit()
            else:
                QMessageBox.warning(self, "失败", err)

    def _show_bill(self, order_info):
        from ui.billing_panel import BillDetailDialog
        dlg = BillDetailDialog(order_info["id"], self)
        dlg.exec()
