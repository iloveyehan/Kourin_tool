# coding:utf-8
import ctypes
import os
import platform
import sys
import bpy
from PySide6.QtCore import Qt, QTimer, QTranslator, QSize, QSettings
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel,QHBoxLayout,QCompleter
from PySide6.QtGui import QWindow,QKeyEvent,QIcon
from PySide6.QtWidgets import QApplication
from PySide6 import QtWidgets
from ctypes import wintypes
from pathlib import Path
from .ui_widgets import  Item, ItemDelegate, ListModel, ListView
from ..common.class_loader.auto_load import ClassAutoloader
ui_vrc_panel=ClassAutoloader(Path(__file__))

def reg_ui_vrc_panel():
    ui_vrc_panel.init()
    ui_vrc_panel.register()
    bpy.types.TOPBAR_MT_editor_menus.append(menu_func)
    bpy.app.handlers.load_post.append(load_post_handler)
    register_sculpt_warning_handler()
def unreg_ui_vrc_panel():
    ui_vrc_panel.unregister()
    bpy.types.TOPBAR_MT_editor_menus.remove(menu_func)
    unregister_sculpt_warning_handler()
    if load_post_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_post_handler)

# ========= WinAPI 常量 & 原型 ===========
HWND_TOPMOST    = -1
HWND_NOTOPMOST = -2
SWP_NOSIZE      = 0x0001
SWP_NOMOVE      = 0x0002
SWP_SHOWWINDOW  = 0x0040
SWP_NOACTIVATE  = 0x0010

ctypes.windll.user32.SetWindowPos.argtypes = [
    wintypes.HWND, wintypes.HWND,
    wintypes.INT, wintypes.INT,
    wintypes.INT, wintypes.INT,
    wintypes.UINT
]

# ========= 全局引用 ===========
qt_app    = None
qt_window = None
last_window_pos=None
def state_handlers(scene, depsgraph):
    obj = bpy.context.active_object
    if obj.data.shape_keys :
        s_ks= obj.data.shape_keys.key_blocks
        print('s_ks',s_ks is None)
    if  obj is not None and  obj.type =='MESH':
        #切换物体
        print(f"选中的物体: {obj.name}")
        print(f"选中的物体: {obj.mio3sksync}")

        if qt_window is not None:
            col=obj.mio3sksync.syncs
            # qt_window.s_ks=s_ks
            qt_window.update_shape_keys(s_ks)
            if col is None:
                qt_window.sync_col_combox.setCurrentIndex(-1)

            else:
                
                qt_window.sync_col_combox.setCurrentText(f"{col.name}")  # 通过文本设置选中项
            qt_window.obj=obj
            qt_window.delegate.obj=obj
        #镜像提醒
        if (obj.mode in  ['SCULPT','EDIT']):
            print('模式',obj.mode)
            if not getattr(obj, 'use_mesh_mirror_x', True):
                # print('进入雕刻模式')
                if QApplication.instance() is None:
                    qt_app = QApplication(sys.argv)
                else:
                    qt_app = QApplication.instance()

                # 只创建一次 toast
                warning_window = MirrorWarningWindow("打开镜像!!",parent=qt_window, duration=3000)
                warning_window.show_centered_on_blender()
                refocus_blender_window()
    
def refocus_blender_window():
    blender_hwnd = ctypes.windll.user32.FindWindowW("GHOST_WindowClass", None)
    if blender_hwnd:
        # 强制将焦点切回 Blender
        ctypes.windll.user32.SetForegroundWindow(blender_hwnd)
        # 可选：确保允许设置前台窗口（对一些权限受限的情况）
        ctypes.windll.user32.AllowSetForegroundWindow(-1)

def register_sculpt_warning_handler():
    if state_handlers not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(state_handlers)
def unregister_sculpt_warning_handler():
    if state_handlers in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(state_handlers)
# 每次打开新文件时重新注册
from bpy.app.handlers import persistent
@persistent
def load_post_handler(dummy):
    register_sculpt_warning_handler()

class MirrorWarningWindow(QWidget):
    def __init__(self, message="", duration=30000, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.Tool |
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.X11BypassWindowManagerHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        self.label = QLabel(message, self)
        self.label.setStyleSheet("""
            QLabel {
                color: white;
                background-color: rgba(0, 0, 0, 180);
                padding: 15px;
                border-radius: 12px;
                font-size: 40px;
            }
        """)
        self.label.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self.adjustSize()

        QTimer.singleShot(duration, self.close)
    def enable_mouse_click_through(self):
        hwnd = int(self.winId())
        GWL_EXSTYLE = -20
        WS_EX_LAYERED = 0x00080000
        WS_EX_TRANSPARENT = 0x00000020
        current_styles = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, current_styles | WS_EX_LAYERED | WS_EX_TRANSPARENT)

    def show_centered_on_blender(self):
        blender_hwnd = ctypes.windll.user32.FindWindowW("GHOST_WindowClass", None)
        rect = wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(blender_hwnd, ctypes.byref(rect))

        blender_x = rect.left
        blender_y = rect.top
        blender_w = rect.right - rect.left
        blender_h = rect.bottom - rect.top

        self.adjustSize()
        self.move(blender_x + (blender_w - self.width()) // 2,
                  blender_y + (blender_h - self.height()) // 5)

        self.show()
        self.raise_()
        self.activateWindow()
        print("提示窗口位置:", self.x(), self.y())
        print("窗口尺寸:", self.width(), self.height())
        self.enable_mouse_click_through()

# ========= 确保 PySide6 可用 ===========
def ensure_pyside6_importable():
    python_dir = sys.exec_prefix
    site_packages = os.path.join(
        python_dir, 'lib',
        f'python{sys.version_info.major}.{sys.version_info.minor}',
        'site-packages'
    )
    if site_packages not in sys.path:
        sys.path.append(site_packages)
ensure_pyside6_importable()


# ========= 更新窗口层级函数 ===========
def update_window_state():
    global qt_window

    # 取 Blender 前台句柄
    blender_hwnd = ctypes.windll.user32.FindWindowW("GHOST_WindowClass", None)
    fg_hwnd      = ctypes.windll.user32.GetForegroundWindow()
    qt_hwnd      = int(qt_window.winId())
    taskbar_hwnd = ctypes.windll.user32.FindWindowW("Shell_TrayWnd", None)

    if fg_hwnd == blender_hwnd:
        ctypes.windll.user32.SetWindowPos(
            qt_hwnd, taskbar_hwnd,
            0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW
        )
        
    else:
        # 其他应用激活时，保持 Qt 窗口正常层级
        ctypes.windll.user32.SetWindowPos(
            qt_hwnd, HWND_NOTOPMOST,
            0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW
        )
    # print(bpy.context.active_object)
    # QTimer.singleShot(10, update_window_state)
# 定义一个PySide6窗口
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,QSpacerItem,QSizePolicy,QGroupBox,QGridLayout,QComboBox
from PySide6.QtCore import QTimer, Qt, QPoint
from PySide6.QtGui import QKeyEvent, QCursor
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtCore import QByteArray
import os
class Button(QPushButton):
    def __init__(self,text):
        super().__init__()
        self.setText(f"{text}")
        self.setStyleSheet("""
            Button:pressed {
                background-color: #bbbbbb;
            }
            Button:focus {
                outline: none;
            }
        """)
def icon_from_dat(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"找不到文件: {file_path}")

    with open(file_path, 'rb') as f:
        data = f.read()

    pixmap = QPixmap()
    if not pixmap.loadFromData(QByteArray(data)):
        raise ValueError("无法从 .dat 文件中解析图像数据")

    return QIcon(pixmap)
class MyQtWindow(QWidget):
    def __init__(self,last_pos=None):
        super().__init__()
        self.obj=None
        self.s_ks=None
        self.setWindowTitle("vrc panel")
        pos = last_pos or QCursor.pos() - QPoint(100, 0)
        self.move(pos)
        # self.setGeometry(mouse_pos.x()-100, mouse_pos.y(), 0, 0)  # 将窗口移动到鼠标位置
        self.adjustSize() 
        # 主布局
        layout = QVBoxLayout()
        layout.setSpacing(3)
        layout.setContentsMargins(3, 3, 3, 3)
        


        self.close_button = Button("×")  # 关闭按钮
        self.close_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.close_button.setFixedSize(20, 20)  # 设置按钮大小
        self.close_button.clicked.connect(self.close)  # 绑定关闭事件

        # 顶部 close 按钮 layout
        top_layout = QHBoxLayout()
        # top_layout.setSpacing(0)
        # top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addStretch()
        top_layout.addWidget(self.close_button)

        main_layout = QHBoxLayout()
        # main_layout.setSpacing(0)
        # main_layout.setContentsMargins(0, 0, 0, 0)
        
        # layout.setStretch(0,1)
        # layout.setStretch(1,100)
        # 内容布局
        self.button = Button("")
        self.button2 = Button("")
        self.button.setToolTip("选中骨架,移除所有没有权重的骨骼")
        self.button.setStyleSheet("""
            QPushButton:pressed {
                background-color: #bbbbbb;
            }
        """)
        my_icon = icon_from_dat("icons/brush_data.svg")
        self.button.setIcon(my_icon)
        self.button.setIconSize(QSize(28, 28))
        self.button.setFixedSize(28, 28)
        self.button.clicked.connect(self.delete_unused_bones)
        main_layout.addWidget(self.button)
        main_layout.addWidget(self.button2)
        
        # self.label = QLabel("test")
        # main_layout.addWidget(self.label)
        self.horizontalLayout_2 = QHBoxLayout()
        # self.horizontalLayout_2.setSpacing(0)
        # self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.pushButton_2 = Button('')
        self.pushButton_2.setObjectName(u"pushButton_2")

        self.horizontalLayout_2.addWidget(self.pushButton_2)

        self.pushButton_3 = Button('')
        self.pushButton_3.setObjectName(u"pushButton_3")

        self.horizontalLayout_2.addWidget(self.pushButton_3)

        self.pushButton_4 = Button('')
        self.pushButton_4.setObjectName(u"pushButton_4")

        self.horizontalLayout_2.addWidget(self.pushButton_4)
        sync_col_layout=QHBoxLayout()
        def get_all_collections(collection):
            """递归获取所有集合"""
            all_collections = [collection]
            for child in collection.children:
                all_collections.extend(get_all_collections(child))
            return all_collections
        self.sync_col_label=QLabel('同步集合')
        self.sync_col_combox = QComboBox()
        root_collection = bpy.context.scene.collection
        all_collections = get_all_collections(root_collection)
        self.sync_col_combox.setEditable(True)  # 设置为可编辑
        self.sync_col_combox.setInsertPolicy(QComboBox.NoInsert)  # 禁止添加新项
        self.sync_col_combox.setCurrentIndex(-1)  # 设置占位文本
        self.sync_col_combox.setPlaceholderText("集合")  # 设置占位文本
        
        
        # 提取集合名称，排除根集合
        collection_names = [col.name for col in all_collections]
        for col_name in collection_names:
            if col_name=='Scene Collection':
                self.sync_col_combox.addItem('')
                continue
            self.sync_col_combox.addItem(col_name)
        # 设置 QCompleter
        completer = QCompleter(collection_names, self.sync_col_combox)
        completer.setFilterMode(Qt.MatchContains)  # 包含匹配
        completer.setCompletionMode(QCompleter.PopupCompletion)  # 弹出补全
        completer.setCaseSensitivity(Qt.CaseInsensitive)  # 设置匹配对大小写不敏感
        self.sync_col_combox.setCompleter(completer)
        # 连接槽函数
        self.sync_col_combox.currentIndexChanged.connect(self.on_combobox_changed)
  
        sync_col_layout.addWidget(self.sync_col_label)
        sync_col_layout.addWidget(self.sync_col_combox)


        # self.view = ListView()
        # self.view.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        # self.view.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        # self.view.setDefaultDropAction(Qt.MoveAction)
        
        # items = [Item(f"Item {i+1}", 0) for i in range(100)]
        items=[]
        # 初始化组件
        self.list_view = ListView()
        self.model = ListModel(items)
        self.delegate = ItemDelegate(self.list_view,self)
        
        # 设置视图属性
        self.list_view.setModel(self.model)
        self.list_view.setItemDelegate(self.delegate)
        self.list_view.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked)
        self.list_view.setStyleSheet("""
            QListView {
                font-size: 14px;
                background: #2d2d2d;
                color: white;
            }
            QLineEdit {
                background: #383838;
                color: white;
                border: 1px solid #606060;
                padding: 2px;
            }
        """)


        layout.addLayout(top_layout)
        layout.addLayout(main_layout)
        layout.addLayout(self.horizontalLayout_2)
        layout.addLayout(sync_col_layout)
        layout.addWidget(self.list_view)
        self.setLayout(layout)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)

        # 用持久化 QTimer 取代 singleShot
        self._timer = QTimer(self)
        self._timer.timeout.connect(update_window_state)
        self._timer.start(100)

        # 用于记录鼠标拖动时的初始位置
        self.dragging = False
        self.offset = QPoint()
    def on_combobox_changed(self, index):
        # 获取当前选中的文本
        selected_text = self.sync_col_combox.currentText()
        if selected_text !='':
            self.obj.mio3sksync.syncs=bpy.data.collections[f'{selected_text}']
        else:
            self.obj.mio3sksync.syncs=None
        # print(f"Selected item: {selected_text}")
    def mousePressEvent(self, event):
        # print(bpy.data.objects['Dress'].use_mesh_mirror_x)
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.offset = event.globalPosition().toPoint() - self.pos()
            event.accept()
        elif event.button() == Qt.RightButton:  # 右键点击关闭窗口
            self.close()
    def mouseMoveEvent(self, event):
        if self.dragging:
            self.move(event.globalPosition().toPoint() - self.offset)
            global last_window_pos
            last_window_pos = self.pos()
            # print(last_window_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
            event.accept()

    def keyPressEvent(self, event: QKeyEvent):
        # 按下 Esc 键或右键时关闭窗口
        if event.key() == Qt.Key_Escape:
            self.close()
        super().keyPressEvent(event)

    def delete_unused_bones(self):
        bpy.app.timers.register(self.del_unused_bones_call)
    def update_shape_keys(self, new_sks):
        self.s_ks = new_sks
        new_items = [Item(f"{sk.name}", sk.value) for sk in self.s_ks]
        self.model.beginResetModel()
        self.model._items = new_items
        self.model.endResetModel()
        
    def del_unused_bones_call(self):
        obj = bpy.context.active_object
        if not obj or obj.type != 'ARMATURE':
            toast = ToastWindow("请选择一个骨骼对象", parent=self)
            toast.show_at_center_of(self)
            return

        bpy.ops.armature.delete_unused_bones()
        
        # 显示提示窗口
        toast = ToastWindow("操作已完成", parent=self)
        toast.show_at_center_of(self)

        return None

    def closeEvent(self, event):
        global qt_window
        # 停止层级维护循环
        if hasattr(self, '_timer') and self._timer.isActive():
            self._timer.stop()
        # 清理全局引用
        qt_window = None
        # 退出 Qt 事件循环
        QApplication.quit()
        return super().closeEvent(event)

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
                background-color: rgba(0, 0, 0, 0);
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

# ========= Blender Operator ===========

class ShowQtPanelOperator(bpy.types.Operator):
    bl_idname = "wm.show_qt_panel"
    bl_label  = "显示 PySide6 面板"

    def execute(self, context):
        global qt_app, qt_window,last_window_pos


        if QApplication.instance() is None:
            qt_app = QApplication(sys.argv)
        else:
            qt_app = QApplication.instance()


        # 显示主窗口
        if not qt_window or not qt_window.isVisible():

            qt_window = MyQtWindow(last_window_pos)

            dark_stylesheet = """
                QWidget {
                    background-color: #2d2d2d;
                    color: #ffffff;
                }
                QPushButton {
                    background-color: #444;
                    color: white;
                    border: 1px solid #666;
                    padding: 5px;
                }
                QPushButton:hover {
                    background-color: #555;
                }
                QLabel {
                    color: white;
                }
            """
            qt_app.setStyleSheet(dark_stylesheet)
            qt_window.show()
        #刷新视图,更新deps
        mesh = bpy.data.meshes.new("TempMesh")
        bpy.data.meshes.remove(mesh)
        return {'FINISHED'}


def menu_func(self, context):
    self.layout.operator(ShowQtPanelOperator.bl_idname, text="VRC", icon='WINDOW')
    