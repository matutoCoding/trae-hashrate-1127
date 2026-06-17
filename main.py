import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QIcon
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("设备租赁管理系统")

    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)

    app.setStyleSheet("""
        QWidget {
            font-family: "Microsoft YaHei", "PingFang SC", "SimHei", sans-serif;
        }
        QToolTip {
            background-color: #333;
            color: white;
            padding: 4px 8px;
            border-radius: 3px;
        }
    """)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
