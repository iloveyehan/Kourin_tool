from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel,QHBoxLayout
from PySide6.QtCore import Qt, QTimer, QTranslator, QSize, QSettings,QEvent,QEventLoop
class ToastWindow(QWidget):
    def __init__(self, message="操作已完成", duration=3000, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.X11BypassWindowManagerHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        # 布局和文本
        layout = QVBoxLayout(self)
        self.label = QLabel(message)
        self.label.setStyleSheet("""
            QLabel {
                color: white;
                background-color: rgba(0, 0, 0, 20);
                padding: 10px;
                border-radius: 10px;
                font-size: 16px;
            }
        """)
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self.adjustSize()

        # 自动关闭
        QTimer.singleShot(duration, self.close)

    def show_at_center_of(self, parent_widget):
        parent_center = parent_widget.geometry().center()
        self.move(parent_center - self.rect().center())
        self.show()
