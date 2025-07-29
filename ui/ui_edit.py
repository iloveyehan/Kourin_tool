import platform
import bpy
import numpy as np
import ctypes
from functools import partial
from pathlib import Path
import platform
import sys
import weakref
from PySide6.QtWidgets import QApplication, QWidget,QVBoxLayout, QLabel,QHBoxLayout

from ..utils.armature import comfirm_one_arm

from ..ui.qt_toastwindow import ToastWindow

from .ui_widgets import BaseWidget, Button
from ..utils.utils import undoable

from ..operators.base_qt_ops import BaseQtOperator
import sys, math
from functools import partial
from PySide6.QtWidgets import QApplication, QWidget, QPushButton, QGraphicsDropShadowEffect
from PySide6.QtGui import QPainter, QColor, QPen, QCursor,QWindow,QMouseEvent
from PySide6.QtCore import Qt, QPointF, QRectF, QSize,QPoint


from ..common.class_loader.auto_load import ClassAutoloader
edit_menu=ClassAutoloader(Path(__file__))
def reg_edit_menu():
    edit_menu.init()
    edit_menu.register()
def unreg_edit_menu():
    edit_menu.unregister()


class EditQuickWigdet(QWidget):
    def __init__(self,parent,radius):
        super().__init__()
        # 创建布局
        self.edit_widget=parent
        self.ops=self.edit_widget.ops
        self.init_pos=self.edit_widget.init_pos
        
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
        """)

        self.setParent(parent)
        self.move(self.init_pos[0]-radius,self.init_pos[1]-radius+20)
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
        settings = bpy.context.scene.kourin_weight_transfer_settings
        o=settings.source_object
        if o is not None and o.type=='MESH':
            if o.name==bpy.context.active_object.name:
                name='权重来源不能是自己'
            else:
                name=o.name
        else:
            name='None'
        
        layout.addWidget(QLabel(name))

        layout.addLayout(h_1)
        layout.addLayout(h_2)
        h_2.addLayout(h_2_1)
        # h_2.addStretch()
        h_2.addLayout(h_2_2)
        h_2.addLayout(h_2_3)
        
        layout.addStretch()
        # 添加标签
        for icon,bt_name,check,tooltip in [
            # ('hide_off.svg','faceset_from_visible',False,'从视图可见顶点创建面组'),
            ('editmode_hlt.svg','faceset_from_edit',False,'从选中的顶点创建面组'),
            ('armature_data.svg','edit_to_paint_with_a',False,'选中骨架,并进入权重绘制'),
        ]:
            btn = Button('',icon,(40,40))

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
            ('组','vg_asign',False,'创建顶点组'),
            ('传权重,修改器','weight_by_modi',False,'用数据传递修改器'),
            ('传权重,算法','weight_by_algorithm',False,'用算法传权重'),
            
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
        self.msg='操作完成'
        name = self.sender().property('bt_name')
        func = getattr(self, f"handle_{name}")

        def wrapped_func():
            func()  # 原函数执行
            # 然后注册 toast 显示（下一帧）
            def show_toast():
                toast = ToastWindow(self.msg, parent=self.edit_widget)
                toast.show_at_center_of()
                return None  # 一次性定时器
            bpy.app.timers.register(show_toast)
            return None  # 一次性定时器

        bpy.app.timers.register(wrapped_func)
    def button_check_handler(self,checked):
        name = self.sender().property('bt_name')
        func = getattr(self, f"handle_{name}")
        bpy.app.timers.register(partial(func, checked))
        # 显示提示窗口
        # toast = ToastWindow("操作已完成", parent=self.edit_widget)
        # toast.show_at_center_of()
    @undoable
    def handle_vg_asign(self):
        bpy.ops.kourin.vg_asign_new_group()
    
    @undoable
    def handle_edit_to_paint_with_a(self):
        
        # n=0     
        # for m in bpy.context.active_object.modifiers:
        #     if m.type=='ARMATURE' and m.show_viewport and m.object is not None:
        #         n=n+1
        # if n>1:
        #     self.msg='有多个可用的骨骼修改器,先禁用多余的'
        #     return False
        if not comfirm_one_arm(bpy.context.active_object):
            self.msg='有多个可用的骨骼修改器,先禁用多余的'
            return
        for m in bpy.context.active_object.modifiers:
            if m.type=='ARMATURE' and m.show_viewport and m.object is not None:
                m.object.select_set(True)
        bpy.ops.paint.weight_paint_toggle()
    @undoable
    def handle_faceset_from_edit(self):
        bpy.ops.object.mode_set(mode='SCULPT')
        bpy.ops.sculpt.face_sets_create(mode='SELECTION')
    @undoable
    def handle_weight_by_modi(self):
        settings = bpy.context.scene.kourin_weight_transfer_settings
        if not settings.source_object:
            self.msg='先设置权重来源'
            print(self.msg)
            return
        obj=bpy.context.object
        mode_t=obj.mode
        bpy.ops.kourin.vg_asign_new_group()
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.kourin.vg_trans_modi()
        modi=obj.modifiers.active
        bpy.ops.object.datalayout_transfer(modifier=modi.name)
        try:
            bpy.ops.object.modifier_apply(modifier=modi.name, report=True)
        except:
            bpy.ops.kourin.apply_modi_with_shapekey(mod_name=modi.name)
        bpy.ops.object.mode_set(mode=mode_t)
    @undoable
    def handle_weight_by_algorithm(self):
        settings = bpy.context.scene.kourin_weight_transfer_settings
        if not settings.source_object:
            self.msg='先设置权重来源'
            print(self.msg)
            return
        obj=bpy.context.object
        mode_t=obj.mode
        bpy.ops.kourin.vg_asign_new_group()
        vg=bpy.context.object.vertex_groups.active
        object_settings = obj.kourin_weight_transfer_settings
        object_settings.vertex_group=vg.name
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.kourin.skin_weight_transfer()
        bpy.ops.object.mode_set(mode=mode_t)
        try:
            obj.vertex_groups.remove(vg) 
        except:
            print('顶点组不存在')
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

class EditMenuWidget(QWidget):
    def __init__(self, context, parent_hwnd, init_pos,ops=None):
        super().__init__()
        self.ops=ops
        # Windows 平台下使用原生窗口属性
        if platform.system() == "Windows":
            self.setAttribute(Qt.WA_NativeWindow, True)
        
        # 嵌入 Blender 主窗口
        blender_window = QWindow.fromWinId(parent_hwnd)
        self.blender=blender_window
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

 
        self.SculptQuickWigdet=EditQuickWigdet(self,radius)
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



class QtEditMenuOperator(BaseQtOperator,bpy.types.Operator):
    bl_idname = "qt.edit_menu"
    bl_label = "编辑快捷菜单"
    @classmethod
    def poll(cls, context):
        if bpy.context.mode == 'EDIT_MESH':#4.5
            return True
        return False
    def key_space_release_ops(self):
        pass
    def key_space_press_ops(self):
        pass
    def set_embedded_qt(self, context, parent_hwnd, init_pos):
        return EditMenuWidget(context,parent_hwnd,init_pos,ops=self)