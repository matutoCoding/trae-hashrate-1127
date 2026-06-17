from datetime import date, datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
                               QTableWidgetItem, QHeaderView, QDialog, QFormLayout, QLineEdit,
                               QDialogButtonBox, QMessageBox, QFrame, QComboBox, QTabWidget,
                               QSpinBox, QDateEdit, QTextEdit, QSplitter)
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtGui import QColor
from services.stock_check_service import StockCheckService
from services.equipment_service import EquipmentService
from models.equipment import EquipmentType, EquipmentBatch
from models.stock_check import StockCheck, StockCheckItem


class StockCheckPanel(QWidget):
    data_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.refresh_list()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        top = QHBoxLayout()
        title = QLabel("📦 库存盘点")
        title.setStyleSheet("font-size: 17px; font-weight: bold; color: #2C3E50;")
        top.addWidget(title)
        top.addStretch()

        self.new_type_btn = QPushButton("➕ 按类型盘点")
        self.new_type_btn.setStyleSheet("""
            QPushButton { background-color: #1976D2; color: white; padding: 8px 16px; 
                          border: none; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #1565C0; }
        """)
        self.new_type_btn.clicked.connect(self._new_type_check)
        top.addWidget(self.new_type_btn)

        self.new_batch_btn = QPushButton("➕ 按批次盘点")
        self.new_batch_btn.setStyleSheet("""
            QPushButton { background-color: #009688; color: white; padding: 8px 16px; 
                          border: none; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #00796B; }
        """)
        self.new_batch_btn.clicked.connect(self._new_batch_check)
        top.addWidget(self.new_batch_btn)
        layout.addLayout(top)

        splitter = QSplitter(Qt.Vertical)

        list_frame = QFrame()
        list_frame.setStyleSheet("background-color: white; border-radius: 8px;")
        list_layout = QVBoxLayout(list_frame)
        list_layout.setContentsMargins(16, 12, 16, 12)
        list_layout.setSpacing(8)

        list_title = QLabel("盘点记录")
        list_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #2C3E50;")
        list_layout.addWidget(list_title)

        self.list_table = QTableWidget()
        self.list_table.setColumnCount(7)
        self.list_table.setHorizontalHeaderLabels(["盘点单号", "类型", "盘点日期", "系统数", "实盘数", "盘盈/盘亏", "状态"])
        self.list_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.list_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.list_table.verticalHeader().setVisible(False)
        self.list_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.list_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.list_table.setStyleSheet("""
            QTableWidget { border: 1px solid #E0E0E0; border-radius: 4px; gridline-color: #EEE; }
            QHeaderView::section { background-color: #F8F9FA; padding: 8px; border: none;
                                   border-bottom: 1px solid #E0E0E0; font-weight: bold; color: #2C3E50; }
        """)
        self.list_table.itemSelectionChanged.connect(self._on_select_check)
        list_layout.addWidget(self.list_table, 1)
        splitter.addWidget(list_frame)

        detail_frame = QFrame()
        detail_frame.setStyleSheet("background-color: white; border-radius: 8px;")
        detail_layout = QVBoxLayout(detail_frame)
        detail_layout.setContentsMargins(16, 12, 16, 12)
        detail_layout.setSpacing(8)

        detail_top = QHBoxLayout()
        self.detail_title = QLabel("盘点明细")
        self.detail_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #2C3E50;")
        detail_top.addWidget(self.detail_title)
        detail_top.addStretch()

        self.confirm_btn = QPushButton("✅ 确认盘点")
        self.confirm_btn.setStyleSheet("""
            QPushButton { background-color: #4CAF50; color: white; padding: 6px 14px; 
                          border: none; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #388E3C; }
            QPushButton:disabled { background-color: #BDBDBD; }
        """)
        self.confirm_btn.clicked.connect(self._confirm_check)
        self.confirm_btn.setEnabled(False)
        detail_top.addWidget(self.confirm_btn)

        self.save_btn = QPushButton("💾 保存修改")
        self.save_btn.setStyleSheet("""
            QPushButton { background-color: #FF9800; color: white; padding: 6px 14px; 
                          border: none; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #F57C00; }
            QPushButton:disabled { background-color: #BDBDBD; }
        """)
        self.save_btn.clicked.connect(self._save_changes)
        self.save_btn.setEnabled(False)
        detail_top.addWidget(self.save_btn)

        detail_layout.addLayout(detail_top)

        self.detail_table = QTableWidget()
        self.detail_table.setColumnCount(7)
        self.detail_table.setHorizontalHeaderLabels(["设备类型/批次", "系统数量", "实盘数量", "盘盈", "盘亏", "备注", ""])
        self.detail_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.detail_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.detail_table.verticalHeader().setVisible(False)
        self.detail_table.setStyleSheet("""
            QTableWidget { border: 1px solid #E0E0E0; border-radius: 4px; gridline-color: #EEE; }
            QHeaderView::section { background-color: #F8F9FA; padding: 8px; border: none;
                                   border-bottom: 1px solid #E0E0E0; font-weight: bold; color: #2C3E50; }
        """)
        detail_layout.addWidget(self.detail_table, 1)

        splitter.addWidget(detail_frame)
        splitter.setSizes([300, 400])
        layout.addWidget(splitter, 1)

    def refresh_list(self):
        checks = StockCheckService.get_all_checks()
        self.list_table.setRowCount(len(checks))
        for row, c in enumerate(checks):
            self._set_item(self.list_table, row, 0, c.check_no)
            type_map = {"type": "按类型", "batch": "按批次"}
            self._set_item(self.list_table, row, 1, type_map.get(c.check_type, c.check_type))
            self._set_item(self.list_table, row, 2, c.check_date)
            self._set_item(self.list_table, row, 3, str(c.total_system))
            self._set_item(self.list_table, row, 4, str(c.total_actual))
            diff = c.total_profit - c.total_loss
            diff_text = f"盘盈 +{c.total_profit}" if c.total_profit > 0 else f"盘亏 -{c.total_loss}" if c.total_loss > 0 else "0"
            self._set_item(self.list_table, row, 5, diff_text)
            status_map = {"draft": "草稿", "confirmed": "已确认"}
            self._set_item(self.list_table, row, 6, status_map.get(c.status, c.status))
            if c.total_profit > 0:
                self.list_table.item(row, 5).setForeground(QColor("#4CAF50"))
            elif c.total_loss > 0:
                self.list_table.item(row, 5).setForeground(QColor("#F44336"))
            if c.status == "confirmed":
                for col in range(7):
                    self.list_table.item(row, col).setForeground(QColor("#9E9E9E"))
        self.list_table.verticalHeader().setDefaultSectionSize(36)

    def _on_select_check(self):
        selected = self.list_table.currentRow()
        if selected < 0:
            return
        check_no = self.list_table.item(selected, 0).text()
        checks = StockCheckService.get_all_checks()
        check_id = None
        for c in checks:
            if c.check_no == check_no:
                check_id = c.id
                self.current_status = c.status
                break
        if not check_id:
            return
        self.current_check_id = check_id
        detail = StockCheckService.get_check_detail(check_id)
        if not detail:
            return
        items = detail["items"]
        self.detail_table.setRowCount(len(items))
        for row, item in enumerate(items):
            name = item.get("type_name", "") or item.get("batch_no", "")
            sub = f" ({item.get('batch_no', '')})" if item.get("type_name") and item.get("batch_no") else ""
            self._set_item(self.detail_table, row, 0, f"{name}{sub}")
            self._set_item(self.detail_table, row, 1, str(item.get("system_qty", 0)))
            actual_spin = QSpinBox()
            actual_spin.setRange(0, 10000)
            actual_spin.setValue(item.get("actual_qty", 0))
            actual_spin.setStyleSheet("padding: 4px;")
            actual_spin.valueChanged.connect(lambda val, r=row, iid=item["id"]: self._on_actual_changed(r, iid, val))
            self.detail_table.setCellWidget(row, 2, actual_spin)
            profit = item.get("profit_qty", 0)
            loss = item.get("loss_qty", 0)
            self._set_item(self.detail_table, row, 3, f"+{profit}" if profit > 0 else "0")
            self._set_item(self.detail_table, row, 4, f"-{loss}" if loss > 0 else "0")
            if profit > 0:
                self.detail_table.item(row, 3).setForeground(QColor("#4CAF50"))
            if loss > 0:
                self.detail_table.item(row, 4).setForeground(QColor("#F44336"))
            self._set_item(self.detail_table, row, 5, item.get("remark", ""))
        self.detail_table.verticalHeader().setDefaultSectionSize(36)

        is_confirmed = self.current_status == "confirmed"
        self.confirm_btn.setEnabled(not is_confirmed)
        self.save_btn.setEnabled(not is_confirmed)
        for row in range(self.detail_table.rowCount()):
            widget = self.detail_table.cellWidget(row, 2)
            if widget:
                widget.setEnabled(not is_confirmed)

    def _on_actual_changed(self, row, item_id, value):
        system_qty = int(self.detail_table.item(row, 1).text())
        profit = max(0, value - system_qty)
        loss = max(0, system_qty - value)
        self.detail_table.item(row, 3).setText(f"+{profit}" if profit > 0 else "0")
        self.detail_table.item(row, 4).setText(f"-{loss}" if loss > 0 else "0")
        if profit > 0:
            self.detail_table.item(row, 3).setForeground(QColor("#4CAF50"))
        else:
            self.detail_table.item(row, 3).setForeground(QColor("#000"))
        if loss > 0:
            self.detail_table.item(row, 4).setForeground(QColor("#F44336"))
        else:
            self.detail_table.item(row, 4).setForeground(QColor("#000"))

    def _save_changes(self):
        if not hasattr(self, 'current_check_id'):
            return
        for row in range(self.detail_table.rowCount()):
            actual_spin = self.detail_table.cellWidget(row, 2)
            if actual_spin:
                remark_item = self.detail_table.item(row, 5)
                remark = remark_item.text() if remark_item else ""
                detail = StockCheckService.get_check_detail(self.current_check_id)
                if detail and row < len(detail["items"]):
                    item_id = detail["items"][row]["id"]
                    StockCheckService.update_item_actual(item_id, actual_spin.value(), remark)
        self.refresh_list()
        self._on_select_check()
        QMessageBox.information(self, "成功", "保存成功！")

    def _confirm_check(self):
        if not hasattr(self, 'current_check_id'):
            return
        reply = QMessageBox.question(self, "确认", "确认盘点后将无法修改，确定吗？",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        ok, msg = StockCheckService.confirm_check(self.current_check_id)
        if ok:
            QMessageBox.information(self, "成功", "盘点确认成功！")
            self.refresh_list()
            self._on_select_check()
            self.data_changed.emit()
        else:
            QMessageBox.warning(self, "失败", msg)

    def _new_type_check(self):
        dlg = NewCheckDialog("type", self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            check_id, check_no = StockCheckService.create_type_check(
                data.get("target_id"), data.get("operator", ""), data.get("remark", ""),
                data.get("check_date")
            )
            QMessageBox.information(self, "成功", f"盘点单已创建：{check_no}")
            self.refresh_list()
            self.data_changed.emit()

    def _new_batch_check(self):
        dlg = NewCheckDialog("batch", self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            check_id, check_no = StockCheckService.create_batch_check(
                data.get("target_id"), data.get("operator", ""), data.get("remark", ""),
                data.get("check_date")
            )
            QMessageBox.information(self, "成功", f"盘点单已创建：{check_no}")
            self.refresh_list()
            self.data_changed.emit()

    def _set_item(self, table, row, col, text):
        item = QTableWidgetItem(str(text))
        item.setTextAlignment(Qt.AlignCenter)
        table.setItem(row, col, item)


class NewCheckDialog(QDialog):
    def __init__(self, check_type, parent=None):
        super().__init__(parent)
        self.check_type = check_type
        self.setWindowTitle(f"新建{'按类型' if check_type == 'type' else '按批次'}盘点")
        self.setMinimumWidth(400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        self.target_combo = QComboBox()
        self.target_combo.setStyleSheet("padding: 6px;")
        if self.check_type == "type":
            types = EquipmentType.get_all()
            self.target_combo.addItem("全部类型", None)
            for t in types:
                self.target_combo.addItem(f"{t.type_code} - {t.type_name}", t.id)
            layout.addRow("盘点类型:", self.target_combo)
        else:
            batches = EquipmentBatch.get_all_with_info()
            self.target_combo.addItem("全部批次", None)
            for b in batches:
                self.target_combo.addItem(f"{b['batch_no']} - {b['type_name']}", b["id"])
            layout.addRow("盘点批次:", self.target_combo)

        today = date.today()
        self.date_edit = QDateEdit(QDate(today.year, today.month, today.day))
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setStyleSheet("padding: 6px;")
        layout.addRow("盘点日期:", self.date_edit)

        self.operator_edit = QLineEdit()
        self.operator_edit.setPlaceholderText("盘点人")
        self.operator_edit.setStyleSheet("padding: 6px 8px; border: 1px solid #CCC; border-radius: 4px;")
        layout.addRow("盘点人:", self.operator_edit)

        self.remark_edit = QTextEdit()
        self.remark_edit.setFixedHeight(60)
        self.remark_edit.setPlaceholderText("备注信息")
        self.remark_edit.setStyleSheet("border: 1px solid #CCC; border-radius: 4px;")
        layout.addRow("备注:", self.remark_edit)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.button(QDialogButtonBox.Ok).setText("创建")
        btn_box.button(QDialogButtonBox.Cancel).setText("取消")
        btn_box.button(QDialogButtonBox.Ok).setStyleSheet("""
            QPushButton { background-color: #1976D2; color: white; padding: 8px 20px; 
                          border: none; border-radius: 4px; font-weight: bold; }
        """)
        btn_box.button(QDialogButtonBox.Cancel).setStyleSheet("""
            QPushButton { background-color: #E0E0E0; color: #333; padding: 8px 20px; 
                          border: none; border-radius: 4px; }
        """)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def get_data(self):
        return {
            "target_id": self.target_combo.currentData(),
            "check_date": self.date_edit.date().toString("yyyy-MM-dd"),
            "operator": self.operator_edit.text().strip(),
            "remark": self.remark_edit.toPlainText().strip()
        }
