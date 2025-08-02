from ctypes import wintypes
import ctypes
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel,QHBoxLayout
from PySide6.QtCore import Qt, QTimer, QTranslator, QSize, QSettings,QEvent,QPoint
class ToastWindow(QWidget):
    def __init__(self, message="操作已完成", duration=700, parent=None,):
        super().__init__(parent)
        self.parent_wg=parent
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
                background-color: rgba(0, 0, 0, 160);
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
        # QTimer.singleShot(duration, self.close)
        QTimer.singleShot(duration, self.close_self_and_ops)
    def close_self_and_ops(self):
        self.close()
        if hasattr(self.parent_wg,'ops') and self.parent_wg.ops is not None:
            if hasattr(self.parent_wg.ops,'auto_close'):
                self.parent_wg.ops.auto_close=True
                
                

    def show_at_center_of(self):
        x,y=self.get_mouse_pos()
        self.move(self.get_mouse(x+100,y))
        self.show()
    def get_mouse_pos(self):
        pt = wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        return pt.x, pt.y
    def get_mouse(self, gx, gy):
        """直接用屏幕全局坐标更新射线位置。"""
        pt = QPoint(int(gx), int(gy))
        # 把屏幕坐标映射到本控件的局部坐标
        self.mouse_pos = self.mapFromGlobal(pt)
        return self.mouse_pos
