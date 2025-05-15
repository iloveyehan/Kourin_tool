# coding:utf-8
import ctypes
from functools import partial
import os
import platform
import sys
import bpy
from time import time
from PySide6.QtCore import Qt, QTimer, QTranslator, QSize, QSettings
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel,QHBoxLayout,QCompleter,QSizeGrip
from PySide6.QtGui import QWindow,QKeyEvent,QIcon
from PySide6.QtWidgets import QApplication
from PySide6 import QtWidgets
from ctypes import wintypes
from pathlib import Path
from .ui_widgets import  Item, ItemDelegate, ListModel, ListView, icon_from_dat,MenuButton, refocus_blender_window
from ..common.class_loader.auto_load import ClassAutoloader
ui_vrc_panel=ClassAutoloader(Path(__file__))

def reg_ui_vrc_panel():
    ui_vrc_panel.init()
    ui_vrc_panel.register()
    bpy.types.TOPBAR_MT_editor_menus.append(menu_func)
    bpy.app.handlers.load_post.append(load_post_handler)
    # register_sculpt_warning_handler()
    register_msgbus()
def unreg_ui_vrc_panel():
    unregister_msgbus()
    ui_vrc_panel.unregister()
    bpy.types.TOPBAR_MT_editor_menus.remove(menu_func)
    # unregister_sculpt_warning_handler()
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


def register_msgbus():
     # 监听“激活物体”变化：使用 LayerObjects.active 而非 WindowManager.active_object :contentReference[oaicite:0]{index=0}
    bpy.msgbus.subscribe_rna(
        key=(bpy.types.LayerObjects, "active"),
        owner=__name__,
        args=(),
        notify=on_active_or_mode_change,
        options={'PERSISTENT'}
    )
    # 监听所有 Object 实例的 mode 属性变化 :contentReference[oaicite:1]{index=1}
    bpy.msgbus.subscribe_rna(
        key=(bpy.types.Object, "mode"),
        owner=__name__,
        args=(),
        notify=mirror_x_changed,
        options={'PERSISTENT'}
    )
    bpy.msgbus.subscribe_rna(
        key=(bpy.types.Object, "use_mesh_mirror_x"),
        owner=__name__,
        args=(),
        notify=mirror_x_changed,
        options={'PERSISTENT'},
    )
    bpy.msgbus.subscribe_rna(
        key=(bpy.types.Object, "active_shape_key_index"),
        owner=__name__,
        args=(),
        notify=on_shape_key_index_change,
        options={'PERSISTENT'},
    )
    print("消息总线订阅已注册。")
def on_shape_key_index_change(*args):
    global qt_window
    obj = bpy.context.view_layer.objects.active
    
    if qt_window is not None:
        index=qt_window.model.index((obj.active_shape_key_index))
        qt_window.list_view.setCurrentIndex(index)
def on_active_or_mode_change():
    print('触发回调')
    if qt_window is not None:
        obj=bpy.context.view_layer.objects.active
        qt_window.obj = obj
        if obj.type=='MESH':
            
            col=obj.mio3sksync.syncs
            print('激活物体',qt_window.obj)
            if obj.data.shape_keys :
                s_ks= obj.data.shape_keys.key_blocks
                
                qt_window.s_ks=s_ks
                qt_window.update_shape_keys(s_ks)
            else:
                qt_window.s_ks=[]
                qt_window.update_shape_keys([])
            if col is None:
                qt_window.sync_col_combox.setCurrentIndex(-1)

            else:
                
                qt_window.sync_col_combox.setCurrentText(f"{col.name}")  # 通过文本设置选中项
            # qt_window.obj=obj
            qt_window.delegate.obj=obj
        else:
            qt_window.s_ks=[]
            qt_window.update_shape_keys([])


  
def on_mode_change():
    obj = bpy.context.active_object
    print("[模式变更] 当前模式为：", obj.mode if obj else "无物体")
def mirror_x_changed(*args):
    if qt_window is not None:
        obj = bpy.context.view_layer.objects.active
        print(f"当前物体 {obj.name} 的 use_mesh_mirror_x = {obj.use_mesh_mirror_x}")
        if (obj.mode in  ['SCULPT','EDIT']):
            print('模式',obj.mode)
            if not getattr(obj, 'use_mesh_mirror_x', True):
                # print('进入雕刻模式')
                # if QApplication.instance() is None:
                #     qt_app = QApplication(sys.argv)
                # else:
                #     qt_app = QApplication.instance()

                # 只创建一次 toast
                warning_window = MirrorWarningWindow("打开镜像!!",parent=qt_window, duration=3000)
                warning_window.show_centered_on_blender()
                refocus_blender_window()
def unregister_msgbus():
    bpy.msgbus.clear_by_owner(__name__)
    print("[Kourin]消息总线订阅已移除。")
# def register_sculpt_warning_handler():
#     if state_handlers not in bpy.app.handlers.depsgraph_update_post:
#         bpy.app.handlers.depsgraph_update_post.append(state_handlers)
# def unregister_sculpt_warning_handler():
#     if state_handlers in bpy.app.handlers.depsgraph_update_post:
#         bpy.app.handlers.depsgraph_update_post.remove(state_handlers)
# 每次打开新文件时重新注册
from bpy.app.handlers import persistent
@persistent
def load_post_handler(dummy):
    # register_sculpt_warning_handler()
    # 每次新文件加载完成后，重新执行消息总线订阅
    register_msgbus()
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
    # print('更新windows层级')
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
    def __init__(self,text,icon_path=None,size=(20,20)):
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
        if icon_path is not None:
            my_icon = icon_from_dat(icon_path)
            self.setIcon(my_icon)
            self.setIconSize(QSize(*size))
            self.setFixedSize(*size)



class MyQtWindow(QWidget):
    def __init__(self,last_pos=None):
        super().__init__()
        self.obj=None
        self.s_ks=None
        self.b=0
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
        self.button = Button("","brush_data.svg")
        self.button2 = Button("")
        self.button.setToolTip("选中骨架,移除所有没有权重的骨骼")
        # self.button.setStyleSheet("""
        #     QPushButton:pressed {
        #         background-color: #bbbbbb;
        #     }
        # """)
        my_icon = icon_from_dat("brush_data.svg")
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
        self.show_only_sk = Button('','solo_off.svg')
        self.show_only_sk.setProperty('bt_name','show_only_sk')
        self.show_only_sk.setCheckable(True)
        self.show_only_sk.toggled.connect(self.button_check_handler)  # 监听状态变化
        self.use_sk_edit = Button('','editmode_hlt.svg')
        self.use_sk_edit.setProperty('bt_name','use_sk_edit')
        self.use_sk_edit.setCheckable(True)
        self.use_sk_edit.toggled.connect(self.button_check_handler)  # 监听状态变化
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
        sync_col_layout.addWidget(self.show_only_sk)
        sync_col_layout.addWidget(self.use_sk_edit)
        sync_col_layout.addWidget(self.sync_col_combox)



        items=[]
        # 初始化组件
        self.list_view = ListView()
        # self.list_view.viewport().setMouseTracking(True)
        self.model = ListModel(items)
        self.delegate = ItemDelegate(self.list_view,self)
        # 将 QSizeGrip 绑定到 list_view 所在窗口（或直接 parent），并对齐右下角
        self.size_grip = QSizeGrip(self)
        self.size_grip.setStyleSheet("""
            QSizeGrip {
                background-color: rgba(1d1d1d);  /* 半透明红色背景 */

            }
        """)
        # row_h = self.list_view.sizeHintForRow(0) or 20
        # self.resize(300, row_h * 5 + 4)  # +4 为上下边距预留
        # 设置视图属性
        self.list_view.setModel(self.model)
        self.list_view.setItemDelegate(self.delegate)
        self.list_view.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked)
        # 连接 clicked 信号到槽函数
        self.list_view.clicked.connect(self.on_item_clicked)
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
        shapekey_bt_layout=QVBoxLayout()
        shapekey_bt_layout.setSpacing(0)
        shapekey_bt_layout.setContentsMargins(0, 0, 0, 0)
        self.button11 = Button("","add.svg",)
        self.button11.setProperty('bt_name','add_shape_key')
        self.button11.clicked.connect(self.button_handler)
        self.button12 = Button("","plus.svg",)
        self.button12.setProperty('bt_name','add_shape_key_here')
        self.button12.clicked.connect(self.button_handler)
        self.button13 = Button("","remove.svg",)
        self.button13.setProperty('bt_name','rm_shape_key')
        self.button13.clicked.connect(self.button_handler)

        self.sk_menu = MenuButton(self,"","downarrow_hlt.svg",)
        self.sk_menu.setStyleSheet("""
            QPushButton {
                background-color: #1d1d1d;  
                color: white;               /* 文本颜色 */
            }
            QMenu {
                background-color: #333333;  /* 背景颜色 */
                color: white;               /* 文本颜色 */
            }
            QMenu::item:selected {
                background-color: #555555;  /* 选中项的背景颜色 */
            }                    
        """)

        self.button14 = Button("","tria_up.svg",)
        self.button14.setProperty('bt_name','up_shape_key')
        self.button14.clicked.connect(self.button_handler)
        self.button15 = Button("","tria_down.svg",)
        self.button15.setProperty('bt_name','dm_shape_key')
        self.button15.clicked.connect(self.button_handler)
        self.button16 = Button("","panel_close.svg",)
        self.button16.setProperty('bt_name','set_0')
        self.button16.clicked.connect(self.button_handler)
        # for btn in (self.button11, self.button12, self.button13,
        #     self.sk_menu, self.button14, self.button15, self.button16):
        #     btn.setContentsMargins(0, 0, 0, 0)
        #     btn.setStyleSheet("margin:0px; padding:0px;")
        shapekey_bt_layout.addWidget(self.button11)
        shapekey_bt_layout.addWidget(self.button12)
        shapekey_bt_layout.addWidget(self.button13)
        shapekey_bt_layout.addWidget(self.sk_menu)
        shapekey_bt_layout.addWidget(self.button14)
        shapekey_bt_layout.addWidget(self.button15)
        shapekey_bt_layout.addWidget(self.button16)
        shapekey_bt_layout.addStretch()
        shapekey_col_layout=QVBoxLayout()
        shapekey_col_layout.addLayout(sync_col_layout)
        shapekey_col_layout.addWidget(self.list_view)
        shapekey_col_layout.addWidget(self.size_grip, 0, Qt.AlignRight | Qt.AlignBottom)
        # row_h = self.list_view.sizeHintForRow(0) or 200
        # self.resize(300, row_h * 5 + 4)  # +4 为上下边距预留
        # 初始尺寸，让它能显示约 5 行（根据你的 delegate/字体大小微调）
        mio_layout=QHBoxLayout()
        layout.addLayout(top_layout)
        layout.addLayout(main_layout)
        layout.addLayout(self.horizontalLayout_2)
        layout.addLayout(mio_layout)
        mio_layout.setSpacing(0)
        mio_layout.setContentsMargins(0, 0, 0, 0)
        mio_layout.addLayout(shapekey_col_layout)
        mio_layout.addLayout(shapekey_bt_layout)
        self.setLayout(layout)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)

        # 用持久化 QTimer 取代 singleShot
        self._timer = QTimer(self)
        self._timer.timeout.connect(update_window_state)
        self._timer.start(20)

        # 用于记录鼠标拖动时的初始位置
        self.dragging = False
        self.offset = QPoint()
    def handle_show_only_sk(self,checked):
        bpy.context.object.show_only_shape_key = checked
        if checked:
            self.show_only_sk.setStyleSheet("""
                QPushButton {
                    background-color: #4772b3;  /* 点击后常亮的颜色 */
                    color: white;
                }
            """)
        else:
            self.show_only_sk.setStyleSheet("""
                QPushButton {
                    background-color: none;  /* 恢复正常状态 */
                    color: black;
                }
            """)
    def handle_use_sk_edit(self,checked):
        bpy.context.object.use_shape_key_edit_mode = checked
        if checked:
            self.use_sk_edit.setStyleSheet("""
                QPushButton {
                    background-color: #4772b3;  /* 点击后常亮的颜色 */
                    color: white;
                }
            """)
        else:
            self.use_sk_edit.setStyleSheet("""
                QPushButton {
                    background-color: none;  /* 恢复正常状态 */
                    color: black;
                }
            """)
    def handle_add_shape_key(self):
        bpy.ops.object.shape_key_add(from_mix=False)
        self.update_shape_keys()
    def handle_add_shape_key_here(self):
        bpy.ops.mio3sk.add_key_current()
        self.update_shape_keys()
    def handle_rm_shape_key(self):
        bpy.ops.object.shape_key_remove(all=False)
        self.update_shape_keys()
    def handle_up_shape_key(self):
        bpy.ops.object.shape_key_move(type='UP')
        self.update_shape_keys()
    def handle_dm_shape_key(self):
        bpy.ops.object.shape_key_move(type='DOWN')
        self.update_shape_keys()
    def handle_set_0(self):
        bpy.ops.object.shape_key_clear()
        self.update_shape_keys()
    def button_handler(self):
        name = self.sender().property('bt_name')
        # print(f'dianjiele {name}')
        # 动态找到处理函数或从映射里取
        func = getattr(self, f"handle_{name}")
        bpy.app.timers.register(func)
    def button_check_handler(self,checked):
        name = self.sender().property('bt_name')
        # print(f'dianjiele {name}')
        # 动态找到处理函数或从映射里取
        func = getattr(self, f"handle_{name}")
        bpy.app.timers.register(partial(func, checked))
    def on_item_clicked(self, index):
        import time
        a=time.time()
        item_text = self.model.data(index, Qt.DisplayRole)
        print(f"点击了项: {item_text}")
        # 查找形态键的索引
        index = self.obj.data.shape_keys.key_blocks.find(item_text)
        # 设置激活的形态键
        if index != -1:
            self.obj.active_shape_key_index = index
        print('点击选中item耗时',time.time()-a)
    def on_combobox_changed(self, index):
        print('更换同步集合')
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
    def update_shape_keys(self, new_sks=None):
        print('触发更新shapekey',self.obj)

        import time
        a=time.time()
        if self.obj.type=="MESH":
            
            if self.obj.data.shape_keys is not None:
                self.s_ks = self.obj.data.shape_keys.key_blocks
                print(len(self.s_ks))
   
                new_items = [Item(f"{sk.name}", sk.value) for sk in self.s_ks]
 
                print(len(self.obj.data.shape_keys.key_blocks))
            else:
                new_items=[]
        else:
            new_items=[]
        self.model.beginResetModel()
        self.model._items = new_items
        self.model.endResetModel()
        print('刷新形态键耗时',time.time()-a)
        
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
        obj = bpy.context.view_layer.objects.active
        bpy.context.view_layer.objects.active=None
        bpy.context.view_layer.objects.active=obj
        return {'FINISHED'}


def menu_func(self, context):
    self.layout.operator(ShowQtPanelOperator.bl_idname, text="VRC", icon='WINDOW')
    