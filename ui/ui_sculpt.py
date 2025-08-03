import ctypes
from functools import partial
from pathlib import Path
import platform
import sys
import weakref
from PySide6.QtWidgets import QApplication, QWidget,QVBoxLayout, QLabel,QHBoxLayout

from PySide6.QtGui import QWindow, QMouseEvent,QRegion
from PySide6.QtCore import Qt, QTimer,QPoint,Signal,QRect,QEvent
import bpy
import numpy as np

from .ui_widgets import BaseWidget, Button
from ..operators.color_selector import get_blender_hwnd

from ..utils.color_selector import debug_print

from ..utils.utils import undoable

from ..common.class_loader.auto_load import ClassAutoloader
sculpt_menu=ClassAutoloader(Path(__file__))
def reg_sculpt_menu():
    sculpt_menu.init()
    sculpt_menu.register()
def unreg_sculpt_menu():
    sculpt_menu.unregister()
# 调试模式开关
DEBUG_MODE = True


import ctypes
from ctypes import wintypes
from PySide6.QtGui import QWindow
from PySide6.QtWidgets import QWidget

# Win32 API 准备
user32 = ctypes.windll.user32
shcore = ctypes.windll.shcore
from ctypes import wintypes
wintypes.HRESULT = wintypes.LONG
# DPI 获取函数
MonitorFromWindow = user32.MonitorFromWindow
MonitorFromWindow.restype = wintypes.HMONITOR
MonitorFromWindow.argtypes = (wintypes.HWND, wintypes.DWORD)

# 常量
MONITOR_DEFAULTTONEAREST = 2
MDT_EFFECTIVE_DPI = 0

GetDpiForMonitor = shcore.GetDpiForMonitor
GetDpiForMonitor.restype = wintypes.HRESULT
GetDpiForMonitor.argtypes = (wintypes.HMONITOR,
                             wintypes.INT,
                             ctypes.POINTER(wintypes.UINT),
                             ctypes.POINTER(wintypes.UINT))

# 获取显示器 DPI
def get_monitor_dpi(hwnd):
    hMon = MonitorFromWindow(wintypes.HWND(hwnd),
                             MONITOR_DEFAULTTONEAREST)
    dpi_x = wintypes.UINT()
    dpi_y = wintypes.UINT()
    hr = GetDpiForMonitor(hMon,
                          MDT_EFFECTIVE_DPI,
                          ctypes.byref(dpi_x),
                          ctypes.byref(dpi_y))
    if hr != 0:
        # 失败时退回系统 DPI（96）
        return 96, 96
    return dpi_x.value, dpi_y.value

# 还是用之前的 GetWindowRect 拿物理窗口位置/尺寸
def get_window_rect(hwnd):
    class RECT(ctypes.Structure):
        _fields_ = [("left", wintypes.LONG),
                    ("top", wintypes.LONG),
                    ("right", wintypes.LONG),
                    ("bottom", wintypes.LONG)]
    rect = RECT()
    if not user32.GetWindowRect(wintypes.HWND(hwnd),
                                ctypes.byref(rect)):
        raise ctypes.WinError()
    return rect.left, rect.top, rect.right-rect.left, rect.bottom-rect.top

import sys, math
from functools import partial
from PySide6.QtWidgets import QApplication, QWidget, QPushButton, QGraphicsDropShadowEffect
from PySide6.QtGui import QPainter, QColor, QPen, QCursor
from PySide6.QtCore import Qt, QPointF, QRectF, QSize

from ..operators.base_qt_ops import BaseQtOperator
class Sculptwheel(QWidget):
    def __init__(self, radius=100, button_infos=None, parent=None):
        super().__init__(parent)
        self.setParent(parent)
        self.SculptMenuWidget = parent
        self.ops=parent.ops
         # 半径稍微内缩
        self.radius = radius-20
        size = self.radius * 2 +40
        self.setFixedSize(size, size)
        self.buttons = []
        self._drag_button = None
        self._drag_offset = QPointF()
        self.button_infos = button_infos
        # 准备角度分布参数
        # 布局从正上方开始（-90°）
        self._layout_start_angle = -math.pi / 2  
        # 布局 span：180°
        self._layout_span = math.pi            

        # 检测从 -110° 开始
        self._detect_start_angle = math.radians(-110)  
        # 检测 span：220°
        self._detect_span = math.radians(220)         

        # 这两个在 _init_ui 里计算
        self._layout_step = 0
        self._detect_step = 0

        # 注意：后面我们要用 total_slots 覆盖原来的 _detect_span/_detect_step
        self._detect_start = None
        self._detect_step  = None

        # 容差：允许射线越过圆中心往左延伸的像素数
        # self._x_tolerance = 60
        # 鼠标当前位置（本地坐标），用于绘制射线
        self._last_mouse_pos = QPointF(self.width()/2, self.height()/2)
        self.setMouseTracking(True)
        
        self._init_ui()
        self._dragging_widget = False
        self._widget_drag_offset = QPointF()
        self.move(*(parent.init_pos-radius))
    def _init_ui(self):
        self.setStyleSheet("""
            QPushButton {
                color: white;
                border: 2px solid #1d1d1d;
                border-radius: 20px;
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
        border: 2px solid #004080;}    
                                  
            QPushButton[highlighted="true"] {
                background-color: #0077d1;
            }
        """)
        for btn in self.buttons:
            btn.deleteLater()
        self.buttons.clear()

        # 固定按钮列表（你原示例硬编码了图标和名称）
        entries = [
            ('mesh_sculpt_inflate.png',    'mesh_sculpt_inflate'),
            ('mesh_sculpt_grab.png',       'mesh_sculpt_grab'),
            ('mesh_sculpt_elastic_grab.png','mesh_sculpt_elastic_grab'),
            ('mesh_sculpt_slide_relax.png','mesh_sculpt_slide_relax'),
            ('Box_Mask_icon.png',          'mask_box'),
            ('mask_bursh.png',             'mask_brush'),
        ]
        n = len(entries)
        if n <2:
            return

        # 布局仍然在 180° 上均分
        self._layout_span = math.pi
        self._layout_step = self._layout_span / (n - 1)

        # 1) 计算“唯一槽位”数量（半圈逻辑）
        unique_slots = (n-2)*2 + 2    # = (6-2)*2 +2 = 10

        # 2) 全圆槽位 = unique_slots * 2
        total_slots = unique_slots * 2  # = 20

        # 3) 每槽角度
        self._detect_step = 2 * math.pi / total_slots

        # 4) 检测起始角度要左移1格，这样槽 0 的起点点就在 -90° 上
        self._detect_start = self._layout_start_angle - self._detect_step

        # … 完成按钮布局（和你原来的一样） …
        center = QPointF(self.width()/2, self.height()/2)
        for i, (icon, bt_name) in enumerate(entries):
            angle = self._layout_start_angle + self._layout_step * i
            x = center.x() + math.cos(angle) * self.radius
            y = center.y() + math.sin(angle) * self.radius
            btn = Button('', icon,parent=self)
            size=np.array((40,40))
            btn.setFixedSize(*size)
            btn.setIconSize(QSize(*(size-12)))
            btn.setProperty('bt_name', bt_name)
            btn.move(int(x - btn.width() / 2), int(y - btn.height() / 2))
    
            effect = QGraphicsDropShadowEffect(btn)
            effect.setBlurRadius(10)
            effect.setOffset(2, 2)
            btn.setGraphicsEffect(effect)
            btn.setProperty("highlighted", False)
            # btn.setMouseTracking(True)           # 开启鼠标跟踪（Hover 需要）
            # btn.installEventFilter(self)
            btn.clicked.connect(self.button_handler)
            self.buttons.append(btn)
            # i=i+1


    def button_handler(self):
        name = self.sender().property('bt_name')
        func = getattr(self, f"handle_{name}", None)
        if func:
            def wrapped_func():
                func()
                def set_close():
                    try:
                        self.ops._press_brush=True
                    except:
                        print('[DEBUG]:Sculpt窗口已经关闭(通过射线)')
                try:
                    bpy.app.timers.register(set_close, first_interval=0.05)

                except:
                    print(f'[DEBUG] raycast:brush {name}')
            bpy.app.timers.register(wrapped_func)


            
    @undoable
    def handle_mesh_sculpt_inflate(self):
        bpy.ops.brush.asset_activate(asset_library_type='ESSENTIALS', asset_library_identifier="", relative_asset_identifier="brushes\\essentials_brushes-mesh_sculpt.blend\\Brush\\Inflate/Deflate")
    
    @undoable
    def handle_mesh_sculpt_grab(self):
        bpy.ops.brush.asset_activate(asset_library_type='ESSENTIALS', asset_library_identifier="", relative_asset_identifier="brushes\\essentials_brushes-mesh_sculpt.blend\\Brush\\Grab")
    @undoable
    def handle_mesh_sculpt_elastic_grab(self):
        bpy.ops.brush.asset_activate(asset_library_type='ESSENTIALS', asset_library_identifier="", relative_asset_identifier="brushes\\essentials_brushes-mesh_sculpt.blend\\Brush\\Elastic Grab")

    @undoable
    def handle_mesh_sculpt_slide_relax(self):
        bpy.ops.brush.asset_activate(asset_library_type='ESSENTIALS', asset_library_identifier="", relative_asset_identifier="brushes\\essentials_brushes-mesh_sculpt.blend\\Brush\\Relax Slide")

    @undoable
    def handle_mask_box(self):
        bpy.ops.wm.tool_set_by_id(name="builtin.box_mask",space_type='VIEW_3D')
    @undoable
    def handle_mask_brush(self):
        bpy.ops.wm.tool_set_by_id(name="builtin_brush.mask",space_type='VIEW_3D')
    def blender_to_local(self, mouse_x: float, mouse_y: float) -> QPointF:
        """
        把 Blender 的 window 坐标 (左下原点) 转换到本控件的局部坐标 (左上原点)。
        """
        # 1. 翻转 Y
        # screen_geom = self.SculptMenuWidget._blender_qwindow.screen().geometry()
        blender_geom = self.SculptMenuWidget._blender_qwindow.geometry()
        inv_y = blender_geom.height() - mouse_y

        # 2. 从 Blender 窗口坐标到屏幕全局坐标
        global_pt = self.SculptMenuWidget._blender_qwindow.mapToGlobal(
            QPoint(int(mouse_x), int(inv_y))
        )

        # 3. 从全局坐标到本控件局部坐标
        return self.mapFromGlobal(global_pt)
    # 你可以提供一个公开方法，既设置了 _last_mouse_pos 又自动重绘
    def set_blender_mouse(self, bx, by):
        self._last_mouse_pos = self.blender_to_local(bx, by)
        self.update()
    def set_global_mouse(self, gx, gy):
        """直接用屏幕全局坐标更新射线位置。"""
        pt = QPoint(int(gx), int(gy))
        # 把屏幕坐标映射到本控件的局部坐标
        self._last_mouse_pos = self.mapFromGlobal(pt)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        # 1. 画圆环
        pen = QPen(QColor('#888888'), 4)
        painter.setPen(pen)
        rect = QRectF(20, 20, self.radius * 2, self.radius * 2)
        painter.drawEllipse(rect)

        # 2. 可视化射线：从中心到鼠标
        pen_line = QPen(QColor('#ffcc00'), 2, Qt.DashLine)
        painter.setPen(pen_line)
        center = QPointF(self.width()/2, self.height()/2)
        painter.drawLine(center, self._last_mouse_pos)
        # painter.drawText(10, 10, f"{QCursor.pos().x():.1f}, {QCursor.pos().y():.1f}")
        center = QPointF(self.width()/2, self.height()/2)
        dx = self._last_mouse_pos.x() - center.x()
        dy = self._last_mouse_pos.y() - center.y()

        angle = math.atan2(dy, dx)
        rel = (angle - self._detect_start) % (2 * math.pi)

        slot = int(rel / self._detect_step)
        candidate_idx = slot // 2

        # 判断 idx 是否落在 [0, n-1] 范围内
        if 0 <= candidate_idx < len(self.buttons):
            valid_idx = candidate_idx
        else:
            valid_idx = None

        # 根据 valid_idx 刷新 highlighted 属性
        for i, btn in enumerate(self.buttons):
            is_highlight = (i == valid_idx)
            if btn.property("highlighted") != is_highlight:
                btn.setProperty("highlighted", is_highlight)
                btn.style().unpolish(btn)
                btn.style().polish(btn)
                btn.update()
        
        # super().paintEvent(event)
    def keyReleaseOps(self):
        n = len(self.buttons)
        center = QPointF(self.width()/2, self.height()/2)
        dx = self._last_mouse_pos.x() - center.x()
        dy = self._last_mouse_pos.y() - center.y()

        angle = math.atan2(dy, dx)
        # 以 _detect_start 为 0，走全圆 2π
        rel = (angle - self._detect_start) % (2 * math.pi)
        if rel > self._detect_span:
            return  # 超出检测扇形

        # 总槽位 = 按钮数 * 2（首尾各两个槽）
        slots = n * 2
        # 得到在哪个槽（0..slots-1）
        slot_idx = int(rel / self._detect_step)

        # 每两个槽映射到同一个 idx
        idx = slot_idx // 2
        # 再 clamp 到 [0, n-1]
        idx = max(0, min(idx, n - 1))

        # 触发
        self.buttons[idx].click()
        # print(f"点击: {self.buttons[idx].property('bt_name')} idx={idx}")

class SculptQuickWigdet(QWidget):
    def __init__(self,parent,radius):
        super().__init__()
        # 创建布局
        self.sculpt_widget=parent
        self.init_pos=self.sculpt_widget.init_pos
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
        """)

        self.setParent(parent)
        self.move(self.init_pos[0]-radius-40,self.init_pos[1]-radius+20)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        h_1=QHBoxLayout()
        h_1.setContentsMargins(0, 0, 0, 0)
        h_1.setSpacing(0)
        h_2=QHBoxLayout()
        
        h_2_1=QVBoxLayout()
        h_2_2=QVBoxLayout()
        h_2_3=QVBoxLayout()
        h_2_1.setContentsMargins(0, 0, 0, 0)
        h_2_1.setSpacing(0)
        layout.addLayout(h_1)
        layout.addLayout(h_2)
        h_2.addLayout(h_2_1)
        # h_2.addStretch()
        h_2.addLayout(h_2_2)
        h_2.addLayout(h_2_3)
        
        layout.addStretch()
        # 添加标签
        for icon,bt_name,check,tooltip in [
            ('hide_off.svg','faceset_from_visible',False,self.tr('从视图可见顶点创建面组')),
            ('editmode_hlt.svg','faceset_from_edit',False,self.tr('从选中的顶点创建面组')),
            ('armature_data.svg','edit_to_paint_with_a',False,self.tr('选中骨架,并进入权重绘制')),
        ]:
            btn = Button('',icon,(30,30))

            btn.setProperty('bt_name', bt_name)
            
            if check:
                btn.setCheckable(True)
                btn.clicked.connect(self.button_check_handler)
            else:
                btn.clicked.connect(self.button_handler)
            btn.setToolTip(tooltip)
            h_1.addWidget(btn)
        h_1.addStretch()
        self.checkable_buttons = {}
        for name,bt_name,check,tooltip in [
            (self.tr('拓扑'),'use_automasking_topology',True,self.tr('根据拓扑自动遮罩')),
            (self.tr('面组'),'use_automasking_face_sets',True,self.tr('根据面组自动遮罩')),
            (self.tr('面组边界'),'use_automasking_boundary_face_sets',True,self.tr('面组边界自动遮罩')),
            (self.tr('网格边界'),'use_automasking_boundary_edges',True,self.tr('网格边界自动遮罩')),
            
        ]:
            btn = Button(name)
            btn.setProperty('bt_name', bt_name)
            if check:
                btn.setCheckable(True)
                btn.clicked.connect(self.button_check_handler)
                self.checkable_buttons[bt_name]=btn
            else:
                btn.clicked.connect(self.button_handler)
            btn.setToolTip(tooltip)
            h_2_1.addWidget(btn)
        h_2.addStretch()
        self.setLayout(layout)
        

        #每次启动更新下状态
        # 在初始化后立即更新状态
        self.update_checkable_button_states()

    def update_checkable_button_states(self):
        """根据当前 Blender 状态同步按钮 checked 状态"""
        for bt_name, btn in self.checkable_buttons.items():
            sculpt=bpy.context.scene.tool_settings.sculpt
            state = getattr(sculpt,bt_name)
            btn.blockSignals(True)
            btn.setChecked(state)
            btn.blockSignals(False)
            # print(bt_name,state)
    def button_handler(self):
        name = self.sender().property('bt_name')
        func = getattr(self, f"handle_{name}")
        def wrapped_func():
            func()  # 原函数执行
            def set_close():
                self.sculpt_widget.ops.auto_close=True
            bpy.app.timers.register(set_close, first_interval=0.05)
        bpy.app.timers.register(wrapped_func)
    def button_check_handler(self,checked):
        name = self.sender().property('bt_name')
        func = getattr(self, f"handle_{name}")
        bpy.app.timers.register(partial(func, checked))
    @undoable
    def handle_edit_to_paint_with_a(self):
        from ..utils.armature import comfirm_one_arm
        # n=0     
        # for m in bpy.context.active_object.modifiers:
        #     if m.type=='ARMATURE' and m.show_viewport and m.object is not None:
        #         n=n+1
        # if n>1:
        #     self.msg='有多个可用的骨骼修改器,先禁用多余的'
        #     return False
        if not comfirm_one_arm(bpy.context.active_object):
            self.msg=self.tr('有多个可用的骨骼修改器,先禁用多余的')
            return
        for m in bpy.context.active_object.modifiers:
            if m.type=='ARMATURE' and m.show_viewport and m.object is not None:
                m.object.select_set(True)
        bpy.ops.paint.weight_paint_toggle()
    @undoable
    def handle_faceset_from_edit(self):
        bpy.ops.sculpt.face_sets_create(mode='SELECTION')
    @undoable
    def handle_faceset_from_visible(self):
        bpy.ops.sculpt.face_sets_create(mode='VISIBLE')
    @undoable
    def handle_use_automasking_topology(self,c):
        sculpt=bpy.context.scene.tool_settings.sculpt
        sculpt.use_automasking_topology = not sculpt.use_automasking_topology
    @undoable
    def handle_use_automasking_face_sets(self,c):
        sculpt=bpy.context.scene.tool_settings.sculpt
        sculpt.use_automasking_face_sets=not sculpt.use_automasking_face_sets

    @undoable
    def handle_use_automasking_boundary_edges(self,c):
        sculpt=bpy.context.scene.tool_settings.sculpt
        sculpt.use_automasking_boundary_edges=not sculpt.use_automasking_boundary_edges
    @undoable
    def handle_use_automasking_boundary_face_sets(self,c):
        sculpt=bpy.context.scene.tool_settings.sculpt
        sculpt.use_automasking_boundary_face_sets=not sculpt.use_automasking_boundary_face_sets


class SculptMenuWidget(QWidget):
    def __init__(self, context, parent_hwnd, init_pos,ops=None):
        super().__init__()
        self.ops=ops
        # Windows 平台下使用原生窗口属性
        if platform.system() == "Windows":
            self.setAttribute(Qt.WA_NativeWindow, True)

        # 嵌入 Blender 主窗口
        blender_window = QWindow.fromWinId(parent_hwnd)
        if blender_window.screen() is None:
            raise RuntimeError("无效的父窗口")
        self.windowHandle().setParent(blender_window)

        h=blender_window.screen().geometry().height()
        w=blender_window.screen().geometry().width()
        # 设置窗口大小和初始位置
        self.resize(w, h)

        self.context = context
        self._blender_qwindow = QWindow.fromWinId(parent_hwnd)
        self._blender_qscreen = self._blender_qwindow.screen()
        # 计算初始位置
        window = bpy.context.window
        height = window.height
        self.init_pos = np.array([init_pos[0], height - init_pos[1]])

        
        self.setWindowOpacity(0.99999)

        # 半透明背景和无边框
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)

 

        self.setMouseTracking(True)
        self.setStyleSheet("background-color: rgba(30,30,30,220);")
        
        # 创建布局和 Label 容器 
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(5)
        radius=100

        def callback(idx, *_):
            print(f"Button {idx} clicked")
        infos = ['A', 'B', 'C', 'D', 'E', 'F']
        
        button_infos = [(label, callback) for label in infos]
        self.Sculptwheel = Sculptwheel(radius=radius, button_infos=button_infos,parent=self)

        self.SculptQuickWigdet=SculptQuickWigdet(self,radius)
        self.SculptQuickWigdet.show()
        
        self.setLayout(self.layout)


        
        self.update()
        self.show()

    def mouseMoveEvent(self, event: QMouseEvent):

        super().mouseMoveEvent(event)
    def closeEvent(self, event):
        """确保关闭时停止定时器"""
        if hasattr(self, 'timer'):
            self.timer.stop()
        event.accept()
    def blender_to_sculptwheel(self, mouse_x: float, mouse_y: float) -> QPointF:
        """
        将 Blender 事件坐标 (mouse_x, mouse_y)，
        从 Blender 窗口左下原点，转换到 Sculptwheel 的局部坐标（左上原点）。

        返回值：QPointF(local_x, local_y)
        """
        # 1. Blender 的 (0,0) 在窗口左下，而 Qt 屏幕坐标 (0,0) 在屏幕左上，
        #    需要把 y 翻转一次：
        screen = self._blender_qwindow.screen().geometry()
        # screen.height() = 整个屏幕高度
        inverted_y = screen.height() - mouse_y

        # 2. 将 Blender 客户区坐标 (mouse_x, inverted_y) 转成全局屏幕坐标
        global_pt = self._blender_qwindow.mapToGlobal(QPoint(int(mouse_x), int(inverted_y)))

        # 3. 再从全局坐标映射到 Sculptwheel 子控件的局部坐标
        local_pt = self.Sculptwheel.mapFromGlobal(global_pt)

        return QPointF(local_pt)

class QtSculptMenuOperator(BaseQtOperator,bpy.types.Operator):
    bl_idname = "qt.sculpt_menu"
    bl_label = "雕刻快捷菜单"
    
    # [!] 使用弱引用持有Qt实例
    _qt_app_ref = None
    _qt_window_ref = None
    _qt_window = None       # 新增：强引用
    _press_brush=False
    auto_close=False
    @classmethod
    def poll(cls, context):
        if bpy.context.mode == 'SCULPT':#4.5
            return True
        return False

    def execute(self, context):
        return {'RUNNING_MODAL'}
    def modal(self, context, event):
        if self._press_brush or self.auto_close:#点击笔刷后关闭菜单
            self._cleanup()
            return {'FINISHED'}
        if event.type == 'SPACE' and event.value == 'PRESS':
            w = self.__class__._qt_window
            if w:
                w.show()
                w.raise_()
                w.Sculptwheel.set_global_mouse(*self.get_mouse_pos())
        elif event.type in ['SPACE','Z'] and event.value == 'RELEASE':
            # 把 Blender 坐标先给 Sculptwheel，内部会做转换并重绘
            try:
                sculptwheel = self._qt_window_ref().Sculptwheel
                sculptwheel.set_global_mouse(*self.get_mouse_pos())
            
                sculptwheel.keyReleaseOps()
                self._cleanup()
            except:
                print('[DEBUG]:Sculpt窗口已经关闭')
            return {'FINISHED'}

        if event.type in {'ESC', 'RIGHTMOUSE'}:
            self._cleanup()
            return {'CANCELLED'}
        
        return {'PASS_THROUGH'}


    def invoke(self, context, event):
        self._press_brush=False
        self.auto_close=False
        mouse_pose=(event.mouse_x,event.mouse_y)
        
        # [!] 统一初始化入口
        self._ensure_qt_app()
        
        parent_hwnd = get_blender_hwnd()
        if not parent_hwnd:
            self.report({'ERROR'}, "无法获取窗口句柄")
            return {'CANCELLED'}

        try:
            # [!] 清理旧窗口
            # if hasattr(bpy, '_embedded_qt'):
            #     bpy._embedded_qt.close()
            #     del bpy._embedded_qt
            # —— 安全销毁旧窗口 ——
            old = getattr(self.__class__, "_qt_window", None)
            if old is not None:
                old.close()
            # 创建新窗口
            widget = self.set_embedded_qt(context,parent_hwnd,init_pos=mouse_pose)

            self.__class__._qt_window = widget
            self.__class__._qt_window_ref = weakref.ref(widget)
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
            
        except Exception as e:
            self.report({'ERROR'}, f"窗口创建失败: {str(e)}")
            return {'CANCELLED'}
    def set_embedded_qt(self,context,parent_hwnd,init_pos):
        '返回主窗口'
        return SculptMenuWidget(context,parent_hwnd,init_pos=init_pos,ops=self)