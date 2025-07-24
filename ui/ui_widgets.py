from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import QRect, QTimer, QTranslator, QSize, QSettings,QEvent,QEventLoop
from PySide6.QtGui import QRegion
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