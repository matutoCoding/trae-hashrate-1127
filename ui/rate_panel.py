from datetime import datetime, timedelta
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
                               QTableWidgetItem, QHeaderView, QDialog, QFormLayout, QLineEdit,
                               QDoubleSpinBox, QSpinBox, QDialogButtonBox, QMessageBox, QCheckBox,
                               QFrame, QDateTimeEdit, QTextEdit, QSizePolicy)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from models.time_rate import TimeRate
from services.billing_service import BillingService
from utils.helpers import format_datetime


class RateEditDialog(QDialog):
    def __init__(self, rate=None, parent=None):
        super().__init__(parent)
        self.rate = rate
        self.setWindowTitle("编辑费率" if rate else "新增费率")
        self.setMinimumWidth(380)
        self._setup_ui()
        if rate:
            self._load_data()

    def _setup_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        self.name_edit = QLineEdit()
        self.name_edit.setStyleSheet("padding: 6px 8px; border: 1px solid #CCC; border-radius: 4px;")
        layout.addRow("时段名称:", self.name_edit)

        time_layout = QHBoxLayout()
        self.start_spin = QSpinBox()
        self.start_spin.setRange(0, 23)
        self.start_spin.setSuffix(" 时")
        self.start_spin.setStyleSheet("padding: 6px;")
        self.end_spin = QSpinBox()
        self.end_spin.setRange(1, 24)
        self.end_spin.setSuffix(" 时")
        self.end_spin.setStyleSheet("padding: 6px;")
        time_layout.addWidget(QLabel("从"))
        time_layout.addWidget(self.start_spin)
        time_layout.addWidget(QLabel("到"))
        time_layout.addWidget(self.end_spin)
        time_layout.addStretch()
        layout.addRow("时段范围:", time_layout)

        self.rate_spin = QDoubleSpinBox()
        self.rate_spin.setRange(0, 1000)
        self.rate_spin.setDecimals(2)
        self.rate_spin.setPrefix("¥ ")
        self.rate_spin.setSuffix(" /小时")
        self.rate_spin.setStyleSheet("padding: 6px;")
        layout.addRow("小时费率:", self.rate_spin)

        self.peak_check = QCheckBox("标记为高峰时段")
        layout.addRow("", self.peak_check)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.button(QDialogButtonBox.Ok).setText("保存")
        btn_box.button(QDialogButtonBox.Cancel).setText("取消")
        btn_box.button(QDialogButtonBox.Ok).setStyleSheet("""
            QPushButton { background-color: #1976D2; color: white; padding: 8px 20px; 
                          border: none; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #1565C0; }
        """)
        btn_box.button(QDialogButtonBox.Cancel).setStyleSheet("""
            QPushButton { background-color: #E0E0E0; color: #333; padding: 8px 20px; 
                          border: none; border-radius: 4px; }
            QPushButton:hover { background-color: #BDBDBD; }
        """)
        btn_box.accepted.connect(self._on_accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def _load_data(self):
        self.name_edit.setText(self.rate.name)
        self.start_spin.setValue(self.rate.start_hour)
        self.end_spin.setValue(self.rate.end_hour)
        self.rate_spin.setValue(self.rate.rate_per_hour)
        self.peak_check.setChecked(bool(self.rate.is_peak))

    def _on_accept(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "提示", "请输入时段名称")
            return
        if self.start_spin.value() >= self.end_spin.value():
            QMessageBox.warning(self, "提示", "开始时间必须早于结束时间")
            return
        self.accept()

    def get_data(self):
        return {
            "name": self.name_edit.text().strip(),
            "start_hour": self.start_spin.value(),
            "end_hour": self.end_spin.value(),
            "rate_per_hour": self.rate_spin.value(),
            "is_peak": 1 if self.peak_check.isChecked() else 0
        }


class RatePanel(QWidget):
    data_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.refresh_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        top_bar = QHBoxLayout()
        title = QLabel("时段费率配置")
        title.setStyleSheet("font-size: 17px; font-weight: bold; color: #2C3E50;")
        top_bar.addWidget(title)

        self.validate_btn = QPushButton("✅ 检查费率连续性")
        self.validate_btn.setStyleSheet("""
            QPushButton { background-color: #009688; color: white; padding: 8px 16px; 
                          border: none; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #00796B; }
        """)
        self.validate_btn.clicked.connect(self._validate_rates)
        top_bar.addWidget(self.validate_btn)

        self.add_btn = QPushButton("➕ 新增时段")
        self.add_btn.setStyleSheet("""
            QPushButton { background-color: #1976D2; color: white; padding: 8px 16px; 
                          border: none; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #1565C0; }
        """)
        self.add_btn.clicked.connect(self._add_rate)
        top_bar.addWidget(self.add_btn)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        content = QHBoxLayout()
        content.setSpacing(16)

        left_frame = QFrame()
        left_frame.setStyleSheet("background-color: white; border-radius: 8px;")
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(16, 16, 16, 16)
        left_title = QLabel("费率列表")
        left_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #2C3E50; margin-bottom: 8px;")
        left_layout.addWidget(left_title)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["ID", "时段名称", "开始", "结束", "费率(元/小时)", "高峰", "操作"])
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
        left_layout.addWidget(self.table)
        content.addWidget(left_frame, 1)

        right_frame = QFrame()
        right_frame.setStyleSheet("background-color: white; border-radius: 8px;")
        right_frame.setFixedWidth(420)
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(10)

        right_title = QLabel("🧪 跨档计费测试")
        right_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #2C3E50;")
        right_layout.addWidget(right_title)

        now = datetime.now()
        self.start_edit = QDateTimeEdit(now)
        self.start_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.start_edit.setCalendarPopup(True)
        self.start_edit.setStyleSheet("padding: 6px;")
        right_layout.addWidget(QLabel("起租时间:"))
        right_layout.addWidget(self.start_edit)

        self.end_edit = QDateTimeEdit(now + timedelta(hours=12))
        self.end_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.end_edit.setCalendarPopup(True)
        self.end_edit.setStyleSheet("padding: 6px;")
        right_layout.addWidget(QLabel("预计归还时间:"))
        right_layout.addWidget(self.end_edit)

        self.calc_btn = QPushButton("💰 计算费用")
        self.calc_btn.setStyleSheet("""
            QPushButton { background-color: #FF5722; color: white; padding: 10px; 
                          border: none; border-radius: 4px; font-weight: bold; font-size: 14px; }
            QPushButton:hover { background-color: #E64A19; }
        """)
        self.calc_btn.clicked.connect(self._calculate_test)
        right_layout.addWidget(self.calc_btn)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet("""
            QTextEdit { border: 1px solid #E0E0E0; border-radius: 4px; padding: 10px; 
                        background-color: #FAFAFA; font-family: Consolas, monospace; }
        """)
        right_layout.addWidget(self.result_text, 1)

        content.addWidget(right_frame)
        layout.addLayout(content, 1)

    def refresh_data(self):
        rates = BillingService.get_rates_sorted()
        self.table.setRowCount(len(rates))
        for row, r in enumerate(rates):
            self._set_item(row, 0, str(r.id))
            self._set_item(row, 1, r.name)
            self._set_item(row, 2, f"{r.start_hour:02d}:00")
            self._set_item(row, 3, f"{r.end_hour:02d}:00")
            self._set_item(row, 4, f"¥{r.rate_per_hour:.2f}")
            self._set_item(row, 5, "是" if r.is_peak else "")
            if r.is_peak:
                self.table.item(row, 5).setForeground(QColor("#FF5722"))
                self.table.item(row, 4).setForeground(QColor("#FF5722"))

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(6)

            edit_btn = QPushButton("编辑")
            edit_btn.setStyleSheet("""
                QPushButton { background-color: #FF9800; color: white; padding: 4px 12px; 
                              border: none; border-radius: 3px; font-size: 12px; }
                QPushButton:hover { background-color: #F57C00; }
            """)
            edit_btn.clicked.connect(lambda _, rid=r.id: self._edit_rate(rid))

            del_btn = QPushButton("删除")
            del_btn.setStyleSheet("""
                QPushButton { background-color: #F44336; color: white; padding: 4px 12px; 
                              border: none; border-radius: 3px; font-size: 12px; }
                QPushButton:hover { background-color: #D32F2F; }
            """)
            del_btn.clicked.connect(lambda _, rid=r.id: self._delete_rate(rid))

            btn_layout.addStretch()
            btn_layout.addWidget(edit_btn)
            btn_layout.addWidget(del_btn)
            btn_layout.addStretch()
            self.table.setCellWidget(row, 6, btn_widget)
        self.table.verticalHeader().setDefaultSectionSize(40)

    def _set_item(self, row, col, text):
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row, col, item)

    def _add_rate(self):
        dlg = RateEditDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            TimeRate.create(**data)
            self.refresh_data()
            self.data_changed.emit()

    def _edit_rate(self, rate_id):
        rate = TimeRate.get_by_id(rate_id)
        if not rate:
            return
        dlg = RateEditDialog(rate=rate, parent=self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            rate.name = data["name"]
            rate.start_hour = data["start_hour"]
            rate.end_hour = data["end_hour"]
            rate.rate_per_hour = data["rate_per_hour"]
            rate.is_peak = data["is_peak"]
            rate.save()
            self.refresh_data()
            self.data_changed.emit()

    def _delete_rate(self, rate_id):
        reply = QMessageBox.question(self, "确认", "确定删除该时段费率吗？",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            TimeRate.delete(rate_id)
            self.refresh_data()
            self.data_changed.emit()

    def _validate_rates(self):
        ok, msg = BillingService.validate_rates()
        if ok:
            QMessageBox.information(self, "校验通过", msg)
        else:
            QMessageBox.warning(self, "校验不通过", msg)

    def _calculate_test(self):
        start_str = self.start_edit.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        end_str = self.end_edit.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        result = BillingService.calculate_rental_cost(start_str, end_str)
        if not result["segments"]:
            self.result_text.setHtml('<p style="color:#F44336;">无效时间范围</p>')
            return
        html = []
        html.append(f'<p style="font-size:14px;"><b>起租:</b> {start_str}</p>')
        html.append(f'<p style="font-size:14px;"><b>归还:</b> {end_str}</p>')
        html.append(f'<p style="font-size:14px;"><b>总时长:</b> {result["total_hours"]:.2f} 小时</p>')
        html.append('<hr style="border:1px solid #DDD;">')
        html.append('<table style="width:100%;font-size:13px;">')
        html.append('<tr style="background:#E3F2FD;"><th style="padding:6px;text-align:left;">时段</th>'
                    '<th style="padding:6px;">时长(h)</th>'
                    '<th style="padding:6px;">费率</th>'
                    '<th style="padding:6px;text-align:right;">金额</th></tr>')
        for i, seg in enumerate(result["segments"]):
            bg = "#FFF8E1" if i % 2 == 0 else "#FFFFFF"
            html.append(f'<tr style="background:{bg};">')
            html.append(f'<td style="padding:5px;">{seg["rate_name"]}<br>'
                        f'<span style="color:#888;font-size:11px;">'
                        f'{format_datetime(seg["segment_start"])} ~ {format_datetime(seg["segment_end"])}</span></td>')
            html.append(f'<td style="padding:5px;text-align:center;">{seg["hours"]:.2f}</td>')
            html.append(f'<td style="padding:5px;text-align:center;">¥{seg["rate"]:.2f}/h</td>')
            html.append(f'<td style="padding:5px;text-align:right;color:#1976D2;font-weight:bold;">¥{seg["segment_amount"]:.2f}</td>')
            html.append('</tr>')
        html.append('</table>')
        html.append('<hr style="border:1px solid #DDD;">')
        html.append(f'<p style="font-size:18px;color:#FF5722;font-weight:bold;text-align:right;">'
                    f'合计: ¥{result["total"]:.2f}</p>')
        self.result_text.setHtml("".join(html))
