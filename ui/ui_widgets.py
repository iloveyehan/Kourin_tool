from functools import partial
from PySide6.QtWidgets import QPushButton,QWidget
from PySide6.QtCore import QRect, QTimer, QTranslator, QSize, QSettings,QEvent,QEventLoop
from PySide6.QtGui import QRegion
import bpy

from .qt_toastwindow import ToastWindow
from .qt_load_icon import icon_from_dat
from .qt_global import GlobalProperty as GP
class Button(QPushButton):
    def __init__(self,text,icon_path=None,size=(20,20),parent=None):
        super().__init__(parent)
        self.setText(f"{text}")
        self.setStyleSheet("""
            Button:pressed {
                background-color: #bbbbbb;
            }
            Button:focus {
                outline: none;
            }
        """)
        if icon_path is not None:
            my_icon = icon_from_dat(icon_path)
            self.setIcon(my_icon)
            self.setIconSize(QSize(*size))
            self.setFixedSize(*size)
    def update_button_state(self,prop):
        if prop in ['vg_left','vg_right']:
            condition=GP.get().vg_middle or GP.get().vg_mul
        elif prop in ['vg_select']:
            condition=GP.get().vg_mul
        else:
            if getattr(GP.get(),prop):
                self.setStyleSheet("""
                QPushButton {
                    background-color: #4772b3;  /* 点击后常亮的颜色 */
                    color: white;
                }
                """)
            else:
                self.setStyleSheet("""
                    QPushButton {
                        background-color: #444444;  /* 恢复正常状态 */
                        color: black;
                    }
                """)
            return
        if condition and getattr(GP.get(),prop):
            
            # self.setEnabled(True)
            # if checked:
            self.setStyleSheet("""
            QPushButton {
                background-color: #4772b3;  /* 点击后常亮的颜色 */
                color: white;
            }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: none;  /* 恢复正常状态 */
                    color: black;
                }
            """)
        # else:
            # self.setEnabled(False)

class BaseWidget(QWidget):
    def __init__(self,ops=None):
        super().__init__()
        self.ops=ops
        self.setStyleSheet("""
            QPushButton {
                color: white;
                border: 2px solid #1d1d1d;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #0077d1;
            }
            QPushButton:pressed {
                background-color: #003d7a;}
            QToolTip {
                background-color: #333333;
                color: #FFFFFF;
                border: 1px solid white;    }
            QPushButton:checked {
            background-color: #005fa0;
            border: 2px solid #004080;
                }
            QLabel{
                color: white;
                font-size: 15pt
            }
            QComboBox { color: white; }               
        """)
    def button_handler(self):
        self.msg='操作完成'
        name = self.sender().property('bt_name')
        func = getattr(self, f"handle_{name}")
        def wrapped_func():
            func()  # 原函数执行
            # 然后注册 toast 显示（下一帧）
            def show_toast():
                toast = ToastWindow(self.msg, parent=self)
                toast.show_at_center_of()
                return None  # 一次性定时器
            bpy.app.timers.register(show_toast)
            return None  # 一次性定时器
    def button_check_handler(self,checked):
        name = self.sender().property('bt_name')
        func = getattr(self, f"handle_{name}")
        bpy.app.timers.register(partial(func, checked))
  
