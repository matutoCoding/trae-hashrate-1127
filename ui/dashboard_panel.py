from datetime import date
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout,
                               QFrame, QTableWidget, QTableWidgetItem, QHeaderView)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from services.equipment_service import EquipmentService
from services.rental_service import RentalService
from services.billing_service import BillingService
from utils.helpers import status_text, parse_datetime


class StatCard(QFrame):
    def __init__(self, title, value, subtitle="", color="#1976D2", parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 8px;
                border-left: 4px solid {color};
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(6)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: #7F8C8D; font-size: 13px;")
        layout.addWidget(title_lbl)

        value_lbl = QLabel(str(value))
        value_lbl.setStyleSheet(f"color: {color}; font-size: 28px; font-weight: bold;")
        layout.addWidget(value_lbl)

        if subtitle:
            sub_lbl = QLabel(subtitle)
            sub_lbl.setStyleSheet("color: #95A5A6; font-size: 11px;")
            layout.addWidget(sub_lbl)


class DashboardPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        stats_grid = QGridLayout()
        stats_grid.setSpacing(16)

        self.card_total = StatCard("设备总数", 0, "全部登记设备", "#1976D2")
        self.card_available = StatCard("可租数量", 0, "当前可出租设备", "#4CAF50")
        self.card_rented = StatCard("租赁中", 0, "已租出设备", "#FF9800")
        self.card_expired = StatCard("已过期", 0, "锁定不可出租", "#F44336")

        stats_grid.addWidget(self.card_total, 0, 0)
        stats_grid.addWidget(self.card_available, 0, 1)
        stats_grid.addWidget(self.card_rented, 0, 2)
        stats_grid.addWidget(self.card_expired, 0, 3)

        layout.addLayout(stats_grid)

        warnings_frame = QFrame()
        warnings_frame.setStyleSheet("background-color: white; border-radius: 8px;")
        w_layout = QVBoxLayout(warnings_frame)
        w_layout.setContentsMargins(20, 16, 20, 16)

        w_title = QLabel("⚠️  临期与过期预警")
        w_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #2C3E50;")
        w_layout.addWidget(w_title)

        self.warning_table = QTableWidget()
        self.warning_table.setColumnCount(6)
        self.warning_table.setHorizontalHeaderLabels(["批次号", "设备类型", "总数", "剩余天数", "状态", "可用数量"])
        self.warning_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.warning_table.verticalHeader().setVisible(False)
        self.warning_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.warning_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.warning_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                gridline-color: #EEE;
            }
            QHeaderView::section {
                background-color: #F8F9FA;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #E0E0E0;
                font-weight: bold;
                color: #2C3E50;
            }
        """)
        w_layout.addWidget(self.warning_table)
        layout.addWidget(warnings_frame, 1)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(16)

        overdue_frame = QFrame()
        overdue_frame.setStyleSheet("background-color: white; border-radius: 8px;")
        o_layout = QVBoxLayout(overdue_frame)
        o_layout.setContentsMargins(20, 16, 20, 16)
        o_title = QLabel("⏰ 租期超期订单")
        o_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #2C3E50;")
        o_layout.addWidget(o_title)

        self.overdue_table = QTableWidget()
        self.overdue_table.setColumnCount(5)
        self.overdue_table.setHorizontalHeaderLabels(["订单号", "客户", "设备", "应还时间", "超期(小时)"])
        self.overdue_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.overdue_table.verticalHeader().setVisible(False)
        self.overdue_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.overdue_table.setStyleSheet(self.warning_table.styleSheet())
        o_layout.addWidget(self.overdue_table)

        rate_frame = QFrame()
        rate_frame.setStyleSheet("background-color: white; border-radius: 8px;")
        r_layout = QVBoxLayout(rate_frame)
        r_layout.setContentsMargins(20, 16, 20, 16)
        r_title = QLabel("💹 当前费率表")
        r_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #2C3E50;")
        r_layout.addWidget(r_title)

        self.rate_table = QTableWidget()
        self.rate_table.setColumnCount(4)
        self.rate_table.setHorizontalHeaderLabels(["时段名称", "开始", "结束", "费率(元/小时)"])
        self.rate_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.rate_table.verticalHeader().setVisible(False)
        self.rate_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.rate_table.setStyleSheet(self.warning_table.styleSheet())
        r_layout.addWidget(self.rate_table)

        bottom_row.addWidget(overdue_frame, 1)
        bottom_row.addWidget(rate_frame, 1)
        layout.addLayout(bottom_row, 1)

    def refresh_data(self):
        EquipmentService.check_and_lock_expired()
        stats = EquipmentService.get_type_stats()
        total = sum(s["total"] or 0 for s in stats)
        available = sum(s["available"] or 0 for s in stats)
        rented = sum(s["rented"] or 0 for s in stats)
        expired = sum(s["expired"] or 0 for s in stats)

        for card, val in [(self.card_total, total), (self.card_available, available),
                           (self.card_rented, rented), (self.card_expired, expired)]:
            labels = card.findChildren(QLabel)
            if len(labels) >= 2:
                labels[1].setText(str(val))

        warnings = EquipmentService.get_warning_batches()
        self.warning_table.setRowCount(len(warnings))
        for row, b in enumerate(warnings):
            self._set_table_item(self.warning_table, row, 0, b["batch_no"])
            self._set_table_item(self.warning_table, row, 1, b["type_name"])
            self._set_table_item(self.warning_table, row, 2, str(b["quantity"]))
            days_text = f"{b['days_left']}天" if b["days_left"] >= 0 else f"过期{abs(b['days_left'])}天"
            self._set_table_item(self.warning_table, row, 3, days_text)
            self._set_table_item(self.warning_table, row, 4, b["status_text"])
            self._set_table_item(self.warning_table, row, 5, str(b["available_count"]))
            if b["status"] == "expired":
                for col in range(6):
                    item = self.warning_table.item(row, col)
                    if item:
                        item.setForeground(QColor("#F44336"))
            elif b["status"] == "warning":
                for col in range(6):
                    item = self.warning_table.item(row, col)
                    if item:
                        item.setForeground(QColor("#FF9800"))

        overdue = RentalService.check_overdue_orders()
        self.overdue_table.setRowCount(len(overdue))
        for row, o in enumerate(overdue):
            self._set_table_item(self.overdue_table, row, 0, o["order_no"])
            self._set_table_item(self.overdue_table, row, 1, o.get("customer_name", ""))
            self._set_table_item(self.overdue_table, row, 2, f"{o['type_name']} - {o['item_code']}")
            self._set_table_item(self.overdue_table, row, 3, o["rent_end"])
            self._set_table_item(self.overdue_table, row, 4, str(o["hours_overdue"]))
            for col in range(5):
                item = self.overdue_table.item(row, col)
                if item:
                    item.setForeground(QColor("#F44336"))

        rates = BillingService.get_rates_sorted()
        self.rate_table.setRowCount(len(rates))
        for row, r in enumerate(rates):
            self._set_table_item(self.rate_table, row, 0, r.name)
            self._set_table_item(self.rate_table, row, 1, f"{r.start_hour:02d}:00")
            self._set_table_item(self.rate_table, row, 2, f"{r.end_hour:02d}:00")
            self._set_table_item(self.rate_table, row, 3, f"¥{r.rate_per_hour:.2f}")
            if r.is_peak:
                for col in range(4):
                    item = self.rate_table.item(row, col)
                    if item:
                        item.setForeground(QColor("#FF5722"))

    def _set_table_item(self, table, row, col, text):
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        table.setItem(row, col, item)
