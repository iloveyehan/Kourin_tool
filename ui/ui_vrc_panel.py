# coding:utf-8
import ctypes
from functools import partial
import os
import platform
import sys
import bpy
from time import time
from PySide6.QtCore import Qt, QTimer, QTranslator, QSize, QSettings,QEvent,QEventLoop
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout,QFrame, QPushButton, QLabel,QHBoxLayout,QCompleter,QSizeGrip,QToolBox
from PySide6.QtGui import QWindow,QKeyEvent,QIcon
from PySide6.QtWidgets import QApplication
from PySide6 import QtWidgets
from ctypes import wintypes
from pathlib import Path
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,QSpacerItem,QSizePolicy,QGroupBox,QGridLayout,QComboBox
from PySide6.QtCore import QTimer, Qt, QPoint
from PySide6.QtGui import QKeyEvent, QCursor
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtCore import QByteArray
import os

from ..translations import get_blender_language

from .qt_global import on_blendfile_loaded

from ..utils.object import obj_from_ptr

from .qt_check import CheckWidget

from ..utils.mio_sync_colsk import callback_show_only_shape_key, callback_update_shapekey, sync_active_shape_key

from .ui_widgets import Button
from .qt_load_icon import icon_from_dat
from .qt_utils import refocus_blender_window
from .qt_vertexgroup import QtVertexGroup
from .qt_toastwindow import ToastWindow
from .qt_preprocessing import PreprocesseWigdet

from .qt_toolbox import ToolBox
from .qt_shapekey import  Item, ItemDelegate, ListModel, ListView, Qt_shapekey, ResizableListView,MenuButton
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
# 全局状态



def register_msgbus():
     # 监听“激活物体”变化：使用 LayerObjects.active 而非 WindowManager.active_object :contentReference[oaicite:0]{index=0}
    bpy.msgbus.subscribe_rna(
        key=(bpy.types.LayerObjects, "active"),
        owner=__name__,
        args=(),
        notify=on_active_change,
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
    bpy.msgbus.subscribe_rna(
        key=(bpy.types.ShapeKey, "value"),
        owner=__name__,
        args=(),
        notify=callback_update_shapekey,
    )
    bpy.msgbus.subscribe_rna(
        key=(bpy.types.ShapeKey, "mute"),
        owner=__name__,
        args=(),
        notify=callback_update_shapekey,
    )
    bpy.msgbus.subscribe_rna(
        key=(bpy.types.Object, "show_only_shape_key"),
        owner=__name__,
        args=(),
        notify=callback_show_only_shape_key,
    )

    print("消息总线订阅已注册。")
def on_shape_key_index_change(qt_w=None):
    # print('刷新 sk index')
    # 如果外部没传进来，就用全局的 qt_window
    from .qt_global import GlobalProperty as GP
    gp = GP.get()
    global qt_window


    # 确保 obj_ptr 和 obj 都是最新的
    obj = bpy.context.view_layer.objects.active
    if obj is None:
        return
    gp.obj_ptr = obj.as_pointer()
    gp.get_obj()
    qt_window.obj_ptr = obj.as_pointer()
    qt_window.get_obj()
    print('形态键更新',qt_window.obj)
    # —— 核心：构造 index 并映射 —— #
    # 1. 拿到当前 active_shape_key_index
    idx = qt_window.obj.active_shape_key_index
    # 2. 在源模型里生成 QModelIndex （row, column）
    src_index = qt_window.qt_shapekey.model.index(idx, 0)
    # 3. 再通过代理转到视图上用的索引
    proxy_index = qt_window.qt_shapekey.proxy.mapFromSource(src_index)

    # 4. 把它设置到真正的 QListView 里
    lv = qt_window.qt_shapekey.list_view.list_view
    if proxy_index.isValid():
        lv.setCurrentIndex(proxy_index)
        # 可选：滚动到可视区中心
        # lv.scrollTo(proxy_index, QtWidgets.QAbstractItemView.PositionAtCenter)

    # —— 同步集合里的 shape key —— #
    
    if (qt_window.obj_ptr in gp.obj_sync_col and
            gp.obj_sync_col[qt_window.obj_ptr] is not None):
        sync_active_shape_key()

    return None


def on_active_change():
    from .qt_global import GlobalProperty as GP
    # print('qt_window',qt_window,'物体切换')
    obj=bpy.context.view_layer.objects.active
    gp =GP.get()
    if obj is not None:
        gp.obj_ptr=obj.as_pointer()
        gp.get_obj()
    if qt_window is not None:
        #sk过滤搜索词
        # 保存旧对象的搜索词
        print('旧')
        print(qt_window.obj)
        qt_window.get_obj()
        print('旧get_obj')
        print(qt_window.obj)
        if qt_window.obj and qt_window.qt_shapekey:
            search_text = qt_window.qt_shapekey.search_edit.text()
            gp._sk_search_map[qt_window.obj_ptr] = search_text
        #新地址
        obj=bpy.context.view_layer.objects.active
        if obj is None:
            return
        qt_window.obj_ptr=obj.as_pointer()
        qt_window.get_obj()
        print('新')
        print(qt_window.obj)
        
        # ptr_obj_new = obj.as_pointer()
        qt_window.qt_vertexgroup.refresh_vertex_groups()

        # 如果有保存过的搜索内容，则恢复
        if qt_window.obj_ptr in gp._sk_search_map:
            search_text = gp._sk_search_map[qt_window.obj_ptr]
            qt_window.qt_shapekey.search_edit.setText(search_text)
        else:
            qt_window.qt_shapekey.search_edit.setText("")

        if qt_window.obj.type=='MESH':
            try:
                col=gp.obj_sync_col[qt_window.obj_ptr]
            except:col=None
            # print('激活物体',qt_window.obj)
            if qt_window.obj.data.shape_keys :
                qt_window.qt_shapekey.show_only_sk.setChecked(qt_window.obj.show_only_shape_key)
                s_ks= qt_window.obj.data.shape_keys.key_blocks
                
                qt_window.s_ks=s_ks
                qt_window.qt_shapekey.update_shape_keys(s_ks)
            else:
                qt_window.qt_shapekey.show_only_sk.setChecked(False)
                qt_window.qt_shapekey.s_ks=[]
                qt_window.qt_shapekey.update_shape_keys()
            if col is None:
                qt_window.qt_shapekey.sync_col_combox.setCurrentIndex(-1)

            else:
                
                qt_window.qt_shapekey.sync_col_combox.setCurrentText(f"{col.name}")  # 通过文本设置选中项
            # qt_window.obj=obj
            qt_window.qt_shapekey.delegate.obj=obj
            qt_window.qt_shapekey.on_combobox_changed()
        else:
            qt_window.qt_shapekey.s_ks=[]
            qt_window.qt_shapekey.update_shape_keys()


  

def mirror_x_changed(*args):    
    # print('qt_window',qt_window,bpy.context.view_layer.objects.active.name)
    if qt_window is not None:
        obj = bpy.context.view_layer.objects.active
        if obj is None:
            return
        
        qt_window.obj_ptr=obj.as_pointer()
        qt_window.get_obj()
        # print(f"当前物体 {obj.name} 的 use_mesh_mirror_x = {obj.use_mesh_mirror_x}")
        if (obj.mode in  ['SCULPT','EDIT']):
            # print('模式',obj.mode)
            if not getattr(qt_window.obj, 'use_mesh_mirror_x', True):
  
                warning_window = MirrorWarningWindow("打开镜像!!",parent=qt_window, duration=3000)
                warning_window.show_centered_on_blender()
                refocus_blender_window()
    # on_active_change()


def unregister_msgbus():
    # stop_pose_bone_polling()
    bpy.msgbus.clear_by_owner(__name__)
    print("[Kourin]消息总线订阅已移除。")

# 每次打开新文件时重新注册
from bpy.app.handlers import persistent
@persistent
def load_post_handler(dummy):
    # register_sculpt_warning_handler()
    # 每次新文件加载完成后，重新执行消息总线订阅
    on_blendfile_loaded()
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

        self.label = QLabel(self.tr(message), self)
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

def update_window_layer():
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





class MyQtWindow(QWidget):
    def __init__(self,hwnd,last_pos=None,ops=None):
        super().__init__()
        self.ops=ops
        if bpy.context.view_layer.objects.active is not None:
            self.obj_ptr=bpy.context.view_layer.objects.active.as_pointer()
        self.obj_ptr=None
        self.obj=self.get_obj()
        self.s_ks=None
        self.b=0
        self.setWindowTitle("vrc panel")
        pos = last_pos or QCursor.pos() - QPoint(100, 0)
        # Windows DPI处理
        if platform.system() == "Windows":
            self.setAttribute(Qt.WA_NativeWindow, True)
        # 嵌入 Blender 主窗口（将传入的句柄转换为 QWindow 对象）
        # blender_qwin = QWindow.fromWinId(hwnd)
        # if blender_qwin.screen() is None:
        #     raise RuntimeError("无效的父窗口")
        # self.windowHandle().setParent(blender_qwin)
        # blender_screen = blender_qwin.screen()
        # self.windowHandle().setScreen(blender_screen)  
        self.setWindowOpacity(0.99999)
        self.setMouseTracking(True)

        QCursor.pos()
        self.adjustSize() 
        # self.setMinimumWidth(250) 
        self.setMinimumSize(250, 380)
        self.toolbox=QToolBox()
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

        top_layout.addStretch()
        top_layout.addWidget(self.close_button)


        self.qt_shapekey=Qt_shapekey(self)
        self.qt_vertexgroup=QtVertexGroup(self)
        self.qt_check=CheckWidget(self)
        self.qt_preprocessewigdet=PreprocesseWigdet(self)
        toolbox = ToolBox()
        toolbox.addWidget(self.tr('预处理'),self.qt_preprocessewigdet)
        toolbox.addWidget(self.tr('顶点组'),self.qt_vertexgroup)
        toolbox.addWidget(self.tr('形态键'),self.qt_shapekey)
        toolbox.addWidget(self.tr('检查'),self.qt_check)

        grip = QSizeGrip(self)
        grip.setStyleSheet("width: 16px; height: 16px;")

        layout.addLayout(top_layout)
        layout.addWidget(toolbox)
        # 将它放到布局右下
        layout.addWidget(grip, alignment=Qt.AlignBottom | Qt.AlignRight)

        self.setLayout(layout)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        # flags = Qt.Window | Qt.CustomizeWindowHint | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint
        # self.setWindowFlags(flags)
        def debug_layout_borders(widget, depth=0, colors=None):
            if colors is None:
                # 自定义一组层级颜色（循环使用）
                colors = [
                    "red", "green", "blue", "orange", "purple",
                    "cyan", "magenta", "brown", "gray"
                ]

            if isinstance(widget, QWidget):
                color = colors[depth % len(colors)]
                widget.setStyleSheet(f"border: 2px dashed {color};")
                widget.styleSheet
                for child in widget.findChildren(QWidget, options=Qt.FindDirectChildrenOnly):
                    debug_layout_borders(child, depth + 1, colors)
        # debug_layout_borders(self)


        # 用持久化 QTimer 取代 singleShot
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update_window_state)
        self._timer.start(100)

        # 用于记录鼠标拖动时的初始位置
        self.dragging = False
        self.offset = QPoint()
    def update_window_state(self):
    # print('更新windows层级')
        bpy.app.timers.register(self._qt_poll_active_pose_bone)
        update_window_layer()
    def get_obj(self):
        if self.obj_ptr is not None:
            self.obj=obj_from_ptr(self.obj_ptr)
        
    def _qt_poll_active_pose_bone(self):
        """用 Qt 的定时器来检查 active_pose_bone"""
        # global _last_active_pose_bone
        bone = bpy.context.active_pose_bone
        if bone != self.qt_vertexgroup._last_active_pose_bone:
            # 更新全局状态并触发回调
            
            self.qt_vertexgroup_last_active_pose_bone = bone
            self.qt_vertexgroup.update_vertex_group_index()
            # _on_pose_bone_changed(bone)
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
        self.install_translator()

        # 显示主窗口
        if not qt_window or not qt_window.isVisible():
            user32 = ctypes.windll.user32
            hwnd = user32.FindWindowW("GHOST_WindowClass", None)
            qt_window = MyQtWindow(hwnd,last_window_pos,ops=self)
            qt_window.setAttribute(Qt.WA_NativeWindow, True)  # 强制成本地窗口
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
            qt_window.raise_()
            _ = qt_window.winId()  # 触发创建窗口句柄
        
        #刷新视图,更新deps
        obj = bpy.context.view_layer.objects.active
        if obj is None:
            qt_window.obj_ptr=None
        else:
            qt_window.obj_ptr=obj.as_pointer()
            qt_window.get_obj()
        bpy.context.view_layer.objects.active=None
        bpy.context.view_layer.objects.active=obj
        return {'FINISHED'}
    def install_translator(self):
        translator = QTranslator()
        self._qt_translator = translator
        lang = get_blender_language()
        
        qm_path = Path(__file__).parent.parent / "translations" / f"{lang}.qm"
        print('[DEBUG]',lang)
        print('[DEBUG] qm_path', qm_path)

        if qm_path.exists():
            t=translator.load(str(qm_path))
            QApplication.instance().installTranslator(translator)
            print(f"[Qt] Loaded language: {lang}",t)
        else:
            print(f"[Qt] Translation file not found: {qm_path}")
        print("Translator isEmpty?", translator.isEmpty())
        print("File path:", translator.filePath())

def menu_func(self, context):
    self.layout.operator(ShowQtPanelOperator.bl_idname, text="VRC", icon='WINDOW')
    