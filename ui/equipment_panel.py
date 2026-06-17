from datetime import date, timedelta
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
                               QTableWidgetItem, QHeaderView, QDialog, QFormLayout, QLineEdit,
                               QSpinBox, QDialogButtonBox, QMessageBox, QFrame, QDateEdit,
                               QComboBox, QTabWidget, QTextEdit, QSizePolicy)
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtGui import QColor, QBrush
from models.equipment import EquipmentType, EquipmentBatch, EquipmentItem
from services.equipment_service import EquipmentService
from utils.helpers import generate_batch_no, status_text


class TypeEditDialog(QDialog):
    def __init__(self, type_obj=None, parent=None):
        super().__init__(parent)
        self.type_obj = type_obj
        self.setWindowTitle("编辑设备类型" if type_obj else "新增设备类型")
        self.setMinimumWidth(380)
        self._setup_ui()
        if type_obj:
            self._load_data()

    def _setup_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        self.code_edit = QLineEdit()
        self.code_edit.setStyleSheet("padding: 6px 8px; border: 1px solid #CCC; border-radius: 4px;")
        layout.addRow("类型编码:", self.code_edit)

        self.name_edit = QLineEdit()
        self.name_edit.setStyleSheet("padding: 6px 8px; border: 1px solid #CCC; border-radius: 4px;")
        layout.addRow("类型名称:", self.name_edit)

        self.desc_edit = QTextEdit()
        self.desc_edit.setFixedHeight(60)
        self.desc_edit.setStyleSheet("border: 1px solid #CCC; border-radius: 4px;")
        layout.addRow("描述:", self.desc_edit)

        self.warn_spin = QSpinBox()
        self.warn_spin.setRange(1, 3650)
        self.warn_spin.setSuffix(" 天")
        self.warn_spin.setValue(30)
        self.warn_spin.setStyleSheet("padding: 6px;")
        layout.addRow("临期预警天数:", self.warn_spin)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.button(QDialogButtonBox.Ok).setText("保存")
        btn_box.button(QDialogButtonBox.Cancel).setText("取消")
        btn_box.button(QDialogButtonBox.Ok).setStyleSheet("""
            QPushButton { background-color: #1976D2; color: white; padding: 8px 20px; 
                          border: none; border-radius: 4px; font-weight: bold; }
        """)
        btn_box.button(QDialogButtonBox.Cancel).setStyleSheet("""
            QPushButton { background-color: #E0E0E0; color: #333; padding: 8px 20px; 
                          border: none; border-radius: 4px; }
        """)
        btn_box.accepted.connect(self._on_accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def _load_data(self):
        self.code_edit.setText(self.type_obj.type_code)
        self.name_edit.setText(self.type_obj.type_name)
        self.desc_edit.setPlainText(self.type_obj.description)
        self.warn_spin.setValue(self.type_obj.warn_days)

    def _on_accept(self):
        if not self.code_edit.text().strip() or not self.name_edit.text().strip():
            QMessageBox.warning(self, "提示", "请填写编码和名称")
            return
        self.accept()

    def get_data(self):
        return {
            "type_code": self.code_edit.text().strip(),
            "type_name": self.name_edit.text().strip(),
            "description": self.desc_edit.toPlainText().strip(),
            "warn_days": self.warn_spin.value()
        }


class BatchEditDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新增设备批次")
        self.setMinimumWidth(400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        self.batch_edit = QLineEdit(generate_batch_no())
        self.batch_edit.setStyleSheet("padding: 6px 8px; border: 1px solid #CCC; border-radius: 4px;")
        layout.addRow("批次号:", self.batch_edit)

        self.type_combo = QComboBox()
        self.type_combo.setStyleSheet("padding: 6px;")
        for t in EquipmentType.get_all():
            self.type_combo.addItem(f"{t.type_code} - {t.type_name}", t.id)
        layout.addRow("设备类型:", self.type_combo)

        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(1, 1000)
        self.qty_spin.setValue(1)
        self.qty_spin.setStyleSheet("padding: 6px;")
        layout.addRow("入库数量:", self.qty_spin)

        today = date.today()
        self.in_date = QDateEdit(QDate(today.year, today.month, today.day))
        self.in_date.setCalendarPopup(True)
        self.in_date.setDisplayFormat("yyyy-MM-dd")
        self.in_date.setStyleSheet("padding: 6px;")
        layout.addRow("入库日期:", self.in_date)

        default_expire = today + timedelta(days=365)
        self.expire_date = QDateEdit(QDate(default_expire.year, default_expire.month, default_expire.day))
        self.expire_date.setCalendarPopup(True)
        self.expire_date.setDisplayFormat("yyyy-MM-dd")
        self.expire_date.setStyleSheet("padding: 6px;")
        layout.addRow("失效日期:", self.expire_date)

        self.remark_edit = QLineEdit()
        self.remark_edit.setStyleSheet("padding: 6px 8px; border: 1px solid #CCC; border-radius: 4px;")
        layout.addRow("备注:", self.remark_edit)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.button(QDialogButtonBox.Ok).setText("登记入库")
        btn_box.button(QDialogButtonBox.Cancel).setText("取消")
        btn_box.button(QDialogButtonBox.Ok).setStyleSheet("""
            QPushButton { background-color: #4CAF50; color: white; padding: 8px 20px; 
                          border: none; border-radius: 4px; font-weight: bold; }
        """)
        btn_box.button(QDialogButtonBox.Cancel).setStyleSheet("""
            QPushButton { background-color: #E0E0E0; color: #333; padding: 8px 20px; 
                          border: none; border-radius: 4px; }
        """)
        btn_box.accepted.connect(self._on_accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def _on_accept(self):
        if not self.batch_edit.text().strip():
            QMessageBox.warning(self, "提示", "请输入批次号")
            return
        if self.expire_date.date() < self.in_date.date():
            QMessageBox.warning(self, "提示", "失效日期不能早于入库日期")
            return
        self.accept()

    def get_data(self):
        return {
            "batch_no": self.batch_edit.text().strip(),
            "type_id": self.type_combo.currentData(),
            "quantity": self.qty_spin.value(),
            "in_date": self.in_date.date().toString("yyyy-MM-dd"),
            "expire_date": self.expire_date.date().toString("yyyy-MM-dd"),
            "remark": self.remark_edit.text().strip()
        }


class EquipmentPanel(QWidget):
    data_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #E0E0E0; border-radius: 8px; background: white; }
            QTabBar::tab { background: #F5F7FA; padding: 10px 24px; border: 1px solid #E0E0E0; 
                           border-bottom: none; border-top-left-radius: 6px; border-top-right-radius: 6px;
                           margin-right: 2px; font-weight: bold; color: #555; }
            QTabBar::tab:selected { background: white; color: #1976D2; }
        """)

        self.batch_tab = QWidget()
        self._setup_batch_tab()
        self.item_tab = QWidget()
        self._setup_item_tab()
        self.type_tab = QWidget()
        self._setup_type_tab()

        self.tabs.addTab(self.batch_tab, "📦 批次管理")
        self.tabs.addTab(self.item_tab, "🔧 设备明细")
        self.tabs.addTab(self.type_tab, "📋 设备类型")
        self.tabs.currentChanged.connect(lambda _: self.refresh_data())
        layout.addWidget(self.tabs)

    def _setup_batch_tab(self):
        layout = QVBoxLayout(self.batch_tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        top = QHBoxLayout()
        info = QLabel("设备按批次和效期管理，租出时先进先出(FIFO)发放")
        info.setStyleSheet("color: #555; font-size: 13px;")
        top.addWidget(info)
        top.addStretch()

        self.add_batch_btn = QPushButton("➕ 登记入库")
        self.add_batch_btn.setStyleSheet("""
            QPushButton { background-color: #4CAF50; color: white; padding: 8px 16px; 
                          border: none; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #388E3C; }
        """)
        self.add_batch_btn.clicked.connect(self._add_batch)
        top.addWidget(self.add_batch_btn)
        layout.addLayout(top)

        self.batch_table = QTableWidget()
        self.batch_table.setColumnCount(10)
        self.batch_table.setHorizontalHeaderLabels([
            "批次号", "设备类型", "入库日期", "失效日期", "状态",
            "剩余天数", "总数", "可租", "已租", "操作"
        ])
        self.batch_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.batch_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.batch_table.verticalHeader().setVisible(False)
        self.batch_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.batch_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.batch_table.setStyleSheet("""
            QTableWidget { border: 1px solid #E0E0E0; border-radius: 4px; gridline-color: #EEE; }
            QHeaderView::section { background-color: #F8F9FA; padding: 8px; border: none;
                                   border-bottom: 1px solid #E0E0E0; font-weight: bold; color: #2C3E50; }
        """)
        layout.addWidget(self.batch_table)

    def _setup_item_tab(self):
        layout = QVBoxLayout(self.item_tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        info = QLabel("设备明细：自动按FIFO排序，过期设备自动锁定不可租")
        info.setStyleSheet("color: #555; font-size: 13px;")
        layout.addWidget(info)

        self.item_table = QTableWidget()
        self.item_table.setColumnCount(7)
        self.item_table.setHorizontalHeaderLabels([
            "设备编码", "所属批次", "设备类型", "失效日期", "剩余天数", "状态", "备注"
        ])
        self.item_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.item_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.item_table.verticalHeader().setVisible(False)
        self.item_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.item_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.item_table.setStyleSheet(self.batch_table.styleSheet())
        layout.addWidget(self.item_table)

    def _setup_type_tab(self):
        layout = QVBoxLayout(self.type_tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        top = QHBoxLayout()
        top.addStretch()
        self.add_type_btn = QPushButton("➕ 新增类型")
        self.add_type_btn.setStyleSheet("""
            QPushButton { background-color: #1976D2; color: white; padding: 8px 16px; 
                          border: none; border-radius: 4px; font-weight: bold; }
        """)
        self.add_type_btn.clicked.connect(self._add_type)
        top.addWidget(self.add_type_btn)
        layout.addLayout(top)

        self.type_table = QTableWidget()
        self.type_table.setColumnCount(6)
        self.type_table.setHorizontalHeaderLabels(["ID", "编码", "名称", "描述", "预警天数", "操作"])
        self.type_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.type_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.type_table.verticalHeader().setVisible(False)
        self.type_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.type_table.setStyleSheet(self.batch_table.styleSheet())
        layout.addWidget(self.type_table)

    def refresh_data(self):
        EquipmentService.check_and_lock_expired()
        batches = EquipmentService.get_all_batches_with_status()
        self.batch_table.setRowCount(len(batches))
        for row, b in enumerate(batches):
            self._set_item(self.batch_table, row, 0, b["batch_no"])
            self._set_item(self.batch_table, row, 1, f"{b['type_code']} {b['type_name']}")
            self._set_item(self.batch_table, row, 2, b["in_date"])
            self._set_item(self.batch_table, row, 3, b["expire_date"])
            self._set_item(self.batch_table, row, 4, b["status_text"])
            days_text = f"{b['days_left']}天" if b["days_left"] >= 0 else f"过期{abs(b['days_left'])}天"
            self._set_item(self.batch_table, row, 5, days_text)
            self._set_item(self.batch_table, row, 6, str(b["quantity"]))
            self._set_item(self.batch_table, row, 7, str(b["available_count"]))
            self._set_item(self.batch_table, row, 8, str(b["rented_count"]))

            color_map = {"expired": "#F44336", "warning": "#FF9800", "normal": "#4CAF50"}
            c = color_map.get(b["status"], "#000")
            for col in range(9):
                item = self.batch_table.item(row, col)
                if item:
                    item.setForeground(QColor(c))

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(6)
            del_btn = QPushButton("删除")
            del_btn.setStyleSheet("""
                QPushButton { background-color: #F44336; color: white; padding: 4px 12px; 
                              border: none; border-radius: 3px; font-size: 12px; }
                QPushButton:hover { background-color: #D32F2F; }
            """)
            del_btn.clicked.connect(lambda _, bid=b["id"]: self._delete_batch(bid))
            btn_layout.addStretch()
            btn_layout.addWidget(del_btn)
            btn_layout.addStretch()
            self.batch_table.setCellWidget(row, 9, btn_widget)
        self.batch_table.verticalHeader().setDefaultSectionSize(40)

        items = EquipmentService.get_all_items_with_status()
        self.item_table.setRowCount(len(items))
        for row, it in enumerate(items):
            self._set_item(self.item_table, row, 0, it["item_code"])
            self._set_item(self.item_table, row, 1, it["batch_no"])
            self._set_item(self.item_table, row, 2, f"{it['type_code']} {it['type_name']}")
            self._set_item(self.item_table, row, 3, it["expire_date"])
            days_text = f"{it['days_left']}天" if it['days_left'] >= 0 else f"过期{abs(it['days_left'])}天"
            self._set_item(self.item_table, row, 4, days_text)
            self._set_item(self.item_table, row, 5, it["status_text"])
            self._set_item(self.item_table, row, 6, "FIFO优先出库" if it["status"] == "available" and it["days_left"] >= 0 else "")

            if it["status"] == "expired":
                for col in range(7):
                    item = self.item_table.item(row, col)
                    if item:
                        item.setForeground(QColor("#F44336"))
            elif it["status"] == "available" and it["days_left"] <= 30 and it["days_left"] >= 0:
                for col in range(7):
                    item = self.item_table.item(row, col)
                    if item:
                        item.setForeground(QColor("#FF9800"))
            elif it["status"] == "rented":
                for col in range(7):
                    item = self.item_table.item(row, col)
                    if item:
                        item.setForeground(QColor("#2196F3"))
        self.item_table.verticalHeader().setDefaultSectionSize(36)

        types = EquipmentType.get_all()
        self.type_table.setRowCount(len(types))
        for row, t in enumerate(types):
            self._set_item(self.type_table, row, 0, str(t.id))
            self._set_item(self.type_table, row, 1, t.type_code)
            self._set_item(self.type_table, row, 2, t.type_name)
            self._set_item(self.type_table, row, 3, t.description)
            self._set_item(self.type_table, row, 4, f"{t.warn_days}天")

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(6)
            edit_btn = QPushButton("编辑")
            edit_btn.setStyleSheet("""
                QPushButton { background-color: #FF9800; color: white; padding: 4px 12px; 
                              border: none; border-radius: 3px; font-size: 12px; }
            """)
            edit_btn.clicked.connect(lambda _, tid=t.id: self._edit_type(tid))
            del_btn = QPushButton("删除")
            del_btn.setStyleSheet("""
                QPushButton { background-color: #F44336; color: white; padding: 4px 12px; 
                              border: none; border-radius: 3px; font-size: 12px; }
            """)
            del_btn.clicked.connect(lambda _, tid=t.id: self._delete_type(tid))
            btn_layout.addStretch()
            btn_layout.addWidget(edit_btn)
            btn_layout.addWidget(del_btn)
            btn_layout.addStretch()
            self.type_table.setCellWidget(row, 5, btn_widget)
        self.type_table.verticalHeader().setDefaultSectionSize(40)

    def _set_item(self, table, row, col, text):
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        table.setItem(row, col, item)

    def _add_batch(self):
        dlg = BatchEditDialog(self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            EquipmentService.create_batch(**data)
            self.refresh_data()
            self.data_changed.emit()

    def _delete_batch(self, batch_id):
        reply = QMessageBox.question(self, "确认", "删除批次将同时删除该批次所有设备，确定？",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            EquipmentBatch.delete(batch_id)
            self.refresh_data()
            self.data_changed.emit()

    def _add_type(self):
        dlg = TypeEditDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            EquipmentService.create_type(**data)
            self.refresh_data()

    def _edit_type(self, type_id):
        t = EquipmentType.get_by_id(type_id)
        if not t:
            return
        dlg = TypeEditDialog(type_obj=t, parent=self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            t.type_code = data["type_code"]
            t.type_name = data["type_name"]
            t.description = data["description"]
            t.warn_days = data["warn_days"]
            t.save()
            self.refresh_data()

    def _delete_type(self, type_id):
        reply = QMessageBox.question(self, "确认", "确定删除该设备类型吗？",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            EquipmentType.delete(type_id)
            self.refresh_data()
