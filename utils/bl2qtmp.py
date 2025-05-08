from PySide6.QtCore import Qt
import bpy

def blender_key_to_qt(blender_key):
    """
    将 Blender 的键值（字符串）映射为 Qt 的按键代码。
    
    参数:
        blender_key (str): Blender 事件中的 key 类型，例如 "A", "ESC", "SPACE", "LEFT_ARROW" 等。
        
    返回:
        int: 对应的 Qt 按键代码，如果没有找到对应的映射，则返回 Qt.Key_unknown。
    """
    # 定义 Blender 按键到 Qt 按键的映射字典
    mapping = {
        # 字母键（Blender 通常以大写传递）
        "A": Qt.Key_A,
        "B": Qt.Key_B,
        "C": Qt.Key_C,
        "D": Qt.Key_D,
        "E": Qt.Key_E,
        "F": Qt.Key_F,
        "G": Qt.Key_G,
        "H": Qt.Key_H,
        "I": Qt.Key_I,
        "J": Qt.Key_J,
        "K": Qt.Key_K,
        "L": Qt.Key_L,
        "M": Qt.Key_M,
        "N": Qt.Key_N,
        "O": Qt.Key_O,
        "P": Qt.Key_P,
        "Q": Qt.Key_Q,
        "R": Qt.Key_R,
        "S": Qt.Key_S,
        "T": Qt.Key_T,
        "U": Qt.Key_U,
        "V": Qt.Key_V,
        "W": Qt.Key_W,
        "X": Qt.Key_X,
        "Y": Qt.Key_Y,
        "Z": Qt.Key_Z,
        
        # 数字键（这里用的是英文单词，也有可能 Blender 返回实际数字字符，根据实际情况调整）
        "ZERO": Qt.Key_0,
        "ONE": Qt.Key_1,
        "TWO": Qt.Key_2,
        "THREE": Qt.Key_3,
        "FOUR": Qt.Key_4,
        "FIVE": Qt.Key_5,
        "SIX": Qt.Key_6,
        "SEVEN": Qt.Key_7,
        "EIGHT": Qt.Key_8,
        "NINE": Qt.Key_9,
        
        # 特殊功能键
        "ESC": Qt.Key_Escape,
        "SPACE": Qt.Key_Space,
        "TAB": Qt.Key_Tab,
        "ENTER": Qt.Key_Return,
        "RET": Qt.Key_Return,
        "NUMPAD_ENTER": Qt.Key_Enter,
        "BACK_SPACE": Qt.Key_Backspace,
        "DEL": Qt.Key_Delete,
        "INSERT": Qt.Key_Insert,
        
        # 方向键
        "LEFT_ARROW": Qt.Key_Left,
        "RIGHT_ARROW": Qt.Key_Right,
        "UP_ARROW": Qt.Key_Up,
        "DOWN_ARROW": Qt.Key_Down,
        
        # 页面控制
        "PAGE_UP": Qt.Key_PageUp,
        "PAGE_DOWN": Qt.Key_PageDown,
        "HOME": Qt.Key_Home,
        "END": Qt.Key_End,
        
        # 功能键 F1 - F12
        "F1": Qt.Key_F1,
        "F2": Qt.Key_F2,
        "F3": Qt.Key_F3,
        "F4": Qt.Key_F4,
        "F5": Qt.Key_F5,
        "F6": Qt.Key_F6,
        "F7": Qt.Key_F7,
        "F8": Qt.Key_F8,
        "F9": Qt.Key_F9,
        "F10": Qt.Key_F10,
        "F11": Qt.Key_F11,
        "F12": Qt.Key_F12,
    }
    
    # 将传入的按键字符串转为大写进行查找
    return mapping.get(blender_key.upper(), Qt.Key_unknown)
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

# def forward_key_event_to_qt(self, blender_event):
#     # 假设 embedded_widget 是你嵌入的 Qt 控件
#     widget = self.customColorPicker  # 或者其他你希望接收事件的控件

#     # 这里需要写个映射函数：blender_key_to_qt(blender_event.type)
#     qt_key = blender_key_to_qt(blender_event.type)
#     if blender_event.ascii != '' and self.l.hasFocus():
#         self.l.insert(blender_event.ascii)
#     # 修饰符也要映射，简单示例：
#     modifiers = Qt.NoModifier
#     if blender_event.shift:
#         modifiers |= Qt.ShiftModifier
#     if blender_event.ctrl:
#         modifiers |= Qt.ControlModifier
#     if blender_event.alt:
#         modifiers |= Qt.AltModifier
#     # print(blender_event.type)
#     # 根据 Blender 事件的值区分按下还是释放：
#     if blender_event.value == 'PRESS':
#         qt_event = QKeyEvent(QEvent.KeyPress, qt_key, modifiers, blender_event.type)
#     elif blender_event.value == 'RELEASE':
#         qt_event = QKeyEvent(QEvent.KeyRelease, qt_key, modifiers, '')
#     else:
#         return

#     # 发送事件到嵌入的 Qt 控件
#     QApplication.sendEvent(widget, qt_event)
def forward_key_event_to_qt(self, blender_event):
    # 优先处理文本输入（支持输入法）
    if blender_event.ascii != '' and self.l.hasFocus():
        # 直接插入字符（支持输入法生成的最终字符）
        self.l.insert(blender_event.ascii)
        
        # 阻止后续按键事件处理（避免重复）
        return True

    # 映射Blender按键到Qt
    qt_key = blender_key_to_qt(blender_event.type)
    
    # 过滤无意义事件（单独修饰键）
    if qt_key in [Qt.Key_Shift, Qt.Key_Control, Qt.Key_Alt, Qt.Key_Meta]:
        return

    # 修饰符处理
    modifiers = Qt.NoModifier
    if blender_event.shift:
        modifiers |= Qt.ShiftModifier
    if blender_event.ctrl:
        modifiers |= Qt.ControlModifier
    if blender_event.alt:
        modifiers |= Qt.AltModifier

    # 特殊按键处理
    text = ''
    if qt_key == Qt.Key_Backspace:
        text = '\b'  # 退格特殊处理
    elif qt_key == Qt.Key_Enter or qt_key == Qt.Key_Return:
        text = '\n'

    # 构造事件
    if blender_event.value == 'PRESS':
        qt_event = QKeyEvent(
            QEvent.KeyPress,
            qt_key,
            modifiers,
            text
        )
    elif blender_event.value == 'RELEASE':
        qt_event = QKeyEvent(
            QEvent.KeyRelease,
            qt_key,
            modifiers,
            ''
        )
    else:
        return

    # 发送到当前焦点控件（而不是固定控件）
    focused_widget = QApplication.focusWidget()
    if focused_widget:
        QApplication.sendEvent(focused_widget, qt_event)
    # 发送事件后强制处理Qt事件队列
    QApplication.processEvents()
    # 阻止Blender处理该事件（避免快捷键冲突）
    return True
