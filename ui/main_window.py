from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QStackedWidget, QLabel, QFrame
from PySide6.QtGui import QFont, QIcon
from PySide6.QtCore import Qt, Signal
from ui.rate_panel import RatePanel
from ui.equipment_panel import EquipmentPanel
from ui.rental_panel import RentalPanel
from ui.billing_panel import BillingPanel
from ui.dashboard_panel import DashboardPanel


class NavButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setMinimumHeight(50)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self._update_style(False)

    def set_active(self, active):
        self.setChecked(active)
        self._update_style(active)

    def _update_style(self, active):
        if active:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #1976D2;
                    color: white;
                    border: none;
                    border-left: 4px solid #FFC107;
                    font-size: 15px;
                    font-weight: bold;
                    padding-left: 16px;
                    text-align: left;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #2C3E50;
                    color: #BDC3C7;
                    border: none;
                    border-left: 4px solid transparent;
                    font-size: 15px;
                    padding-left: 20px;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: #34495E;
                    color: white;
                }
            """)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("设备租赁管理系统")
        self.setMinimumSize(1200, 750)
        self._setup_ui()
        self._connect_signals()
        self.nav_buttons[0].set_active(True)
        self.dashboard_panel.refresh_data()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet("background-color: #2C3E50;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        title_label = QLabel("设备租赁站")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                background-color: #1A252F;
                color: #FFC107;
                font-size: 20px;
                font-weight: bold;
                padding: 24px 12px;
                border-bottom: 1px solid #34495E;
            }
        """)
        sidebar_layout.addWidget(title_label)

        nav_items = [
            ("📊 概览", 0),
            ("⏰ 时段费率", 1),
            ("🔧 设备批次", 2),
            ("📦 租赁出库", 3),
            ("💰 账单管理", 4),
        ]
        self.nav_buttons = []
        for text, idx in nav_items:
            btn = NavButton(text)
            btn.clicked.connect(lambda checked, i=idx, b=btn: self._on_nav_clicked(i, b))
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append(btn)
        sidebar_layout.addStretch()

        version_label = QLabel("v1.0.0")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet("color: #7F8C8D; padding: 12px; font-size: 11px;")
        sidebar_layout.addWidget(version_label)

        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)

        header_bar = QFrame()
        header_bar.setFixedHeight(56)
        header_bar.setStyleSheet("""
            QFrame {
                background-color: white;
                border-bottom: 1px solid #E0E0E0;
            }
        """)
        header_layout = QHBoxLayout(header_bar)
        header_layout.setContentsMargins(24, 0, 24, 0)
        self.header_title = QLabel("概览")
        self.header_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2C3E50;")
        header_layout.addWidget(self.header_title)
        header_layout.addStretch()
        self.header_subtitle = QLabel("")
        self.header_subtitle.setStyleSheet("color: #7F8C8D; font-size: 13px;")
        header_layout.addWidget(self.header_subtitle)

        content_layout.addWidget(header_bar)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet("QStackedWidget { background-color: #F5F7FA; }")

        self.dashboard_panel = DashboardPanel()
        self.rate_panel = RatePanel()
        self.equipment_panel = EquipmentPanel()
        self.rental_panel = RentalPanel()
        self.billing_panel = BillingPanel()

        self.stack.addWidget(self.dashboard_panel)
        self.stack.addWidget(self.rate_panel)
        self.stack.addWidget(self.equipment_panel)
        self.stack.addWidget(self.rental_panel)
        self.stack.addWidget(self.billing_panel)

        content_layout.addWidget(self.stack)

        main_layout.addWidget(sidebar)
        main_layout.addWidget(content_area)

    def _connect_signals(self):
        self.rental_panel.order_created.connect(self._on_data_changed)
        self.rental_panel.order_returned.connect(self._on_data_changed)
        self.equipment_panel.data_changed.connect(self._on_data_changed)
        self.rate_panel.data_changed.connect(self._on_data_changed)

    def _on_data_changed(self):
        self.dashboard_panel.refresh_data()

    def _on_nav_clicked(self, index, button):
        for btn in self.nav_buttons:
            btn.set_active(False)
        button.set_active(True)
        self.stack.setCurrentIndex(index)
        titles = ["概览", "时段费率管理", "设备批次管理", "租赁出库管理", "账单管理"]
        subtitles = [
            "系统运行状态总览",
            "分时段费率配置与计费测试",
            "设备批次登记、效期管理与临期预警",
            "FIFO先进先出库与租期登记",
            "分段计费明细、超期罚金与账单查看",
        ]
        self.header_title.setText(titles[index])
        self.header_subtitle.setText(subtitles[index])
        if index == 2:
            self.equipment_panel.refresh_data()
        elif index == 3:
            self.rental_panel.refresh_data()
        elif index == 4:
            self.billing_panel.refresh_data()
        elif index == 1:
            self.rate_panel.refresh_data()
