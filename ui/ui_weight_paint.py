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
from .qt_global import GlobalProperty as G_prop
from ..ui.ui_widgets import BaseWidget, Button
from ..utils.utils import undoable

from ..operators.base_qt_ops import BaseQtOperator
import sys, math
from functools import partial
from PySide6.QtWidgets import QApplication, QWidget, QComboBox, QGraphicsDropShadowEffect
from PySide6.QtGui import QPainter, QColor, QPen, QCursor,QWindow,QMouseEvent
from PySide6.QtCore import Qt, QPointF, QRectF, QSize,QPoint


from ..common.class_loader.auto_load import ClassAutoloader
weight_paint_menu=ClassAutoloader(Path(__file__))
def reg_weight_paint_menu():
    weight_paint_menu.init()
    weight_paint_menu.register()
def unreg_weight_paint_menu():
    weight_paint_menu.unregister()
class WeightMirror(BaseWidget):
    def __init__(self,parent,ops=None):
        super().__init__(ops=ops)
        layout=QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        h_1=QHBoxLayout()
        h_2=QHBoxLayout()
        for name,bt_name,check,tooltip in [
            # ('hide_off.svg','faceset_from_visible',False,'从视图可见顶点创建面组'),
            ('←','sym_to_left',False,'对称到左边'),
            ('镜像','mirror',False,'镜像权重'),
            ('→','sym_to_right',False,'对称到右边'),
        ]:
            btn = Button(name)

            btn.setProperty('bt_name', bt_name)
            
            if check:
                btn.setCheckable(True)
                btn.clicked.connect(self.button_check_handler)
            else:
                btn.clicked.connect(self.button_handler)
            btn.setToolTip(tooltip)
            h_1.addWidget(btn)

        self.combo = QComboBox()
        self.combo.addItems(["最近", "面投射"])
        self.combo.currentTextChanged.connect(self.on_combo_changed)
            

        for name,bt_name,check,tooltip in [
            ('剪切','weight_cut',False,'剪切权重'),
            ('粘贴','weight_paste',False,'粘贴权重'),
        ]:
            btn = Button(name)

            btn.setProperty('bt_name', bt_name)
            
            if check:
                btn.setCheckable(True)
                btn.clicked.connect(self.button_check_handler)
            else:
                btn.clicked.connect(self.button_handler)
            btn.setToolTip(tooltip)
            h_2.addWidget(btn)


        layout.addLayout(h_1)
        layout.addWidget(self.combo)
        layout.addLayout(h_2)
        self.setLayout(layout)
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

        bpy.app.timers.register(wrapped_func)
    def button_check_handler(self,checked):
        name = self.sender().property('bt_name')
        func = getattr(self, f"handle_{name}")
        bpy.app.timers.register(partial(func, checked))
    def on_combo_changed(self, text):
        from .qt_global import GlobalProperty as GP
        try:
            GP.get().vg_mirror_search = text=='最近'
            print(f"设置 vg_mirror_search = {text}")
        except Exception as e:
            print("设置失败：", e)
    def get_mirror_prop(s):
        temp={
            'vg_mul':G_prop.get().vg_mul,
            'vg_select':G_prop.get().vg_select,
            'vg_middle':G_prop.get().vg_middle,
            'vg_select':G_prop.get().vg_left,
            'vg_select':G_prop.get().vg_right,
        }
        return temp
    @undoable
    def handle_sym_to_left(self):
        if not comfirm_one_arm(bpy.context.active_object):
            self.msg='有多个可用的骨骼修改器,先禁用多余的'
            return
        temp=self.get_mirror_prop()

        G_prop.get().vg_left=True
        G_prop.get().vg_right=False
        G_prop.get().vg_middle=True
        G_prop.get().vg_mul=False
        G_prop.get().vg_select=False

        bpy.ops.kourin.vg_mirror_weight()

        for k in temp:
            setattr(G_prop.get(),k,temp[k])
    @undoable
    def handle_sym_to_right(self):
        if not comfirm_one_arm(bpy.context.active_object):
            self.msg='有多个可用的骨骼修改器,先禁用多余的'
            return
        temp=self.get_mirror_prop()

        G_prop.get().vg_left=False
        G_prop.get().vg_right=True
        G_prop.get().vg_middle=True
        G_prop.get().vg_mul=False
        G_prop.get().vg_select=False

        bpy.ops.kourin.vg_mirror_weight()

        for k in temp:
            setattr(G_prop.get(),k,temp[k])

    @undoable
    def handle_mirror(self):
        if not comfirm_one_arm(bpy.context.active_object):
            self.msg='有多个可用的骨骼修改器,先禁用多余的'
            return
        temp=self.get_mirror_prop()

        G_prop.get().vg_left=False
        G_prop.get().vg_right=False
        G_prop.get().vg_middle=False
        G_prop.get().vg_mul=False
        G_prop.get().vg_select=False

        bpy.ops.kourin.vg_mirror_weight()

        for k in temp:
            setattr(G_prop.get(),k,temp[k])
    @undoable
    def handle_weight_cut(self):
        bpy.ops.kourin.copy_vertex_group_weights()


    @undoable
    def handle_weight_paste(self):

        bpy.ops.kourin.paste_vertex_group_weights()



class EditQuickWigdet(QWidget):
    def __init__(self,parent,ops=None):
        super().__init__(parent)
        self.ops=ops
        # 创建布局
        self.edit_widget=parent
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
        self.move(self.init_pos[0]-self.width()/2,self.init_pos[1]-self.height())
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        h_1=QHBoxLayout()
        h_1.setContentsMargins(0, 0, 0, 0)
        h_1.setSpacing(0)
        h_2=QHBoxLayout()

        

        # h_2_1.setContentsMargins(0, 0, 0, 0)
        # h_2_1.setSpacing(0)


        layout.addLayout(h_1)
        # self.combo = QComboBox()
        # self.combo.addItems(["最近", "面投射"])
        # self.combo.currentTextChanged.connect(self.on_combo_changed)
        layout.addWidget(WeightMirror(self,ops=self.ops))
        # layout.addWidget(self.combo)
        layout.addLayout(h_2)


        
        layout.addStretch()
        
        h_2.addStretch()
        self.setLayout(layout)
        


    

    
    @undoable
    def handle_vg_asign(self):
        bpy.ops.kourin.vg_asign_new_group()
    @undoable
    def handle_faceset_from_edit(self):
        bpy.ops.object.mode_set(mode='SCULPT')
        bpy.ops.sculpt.face_sets_create(mode='SELECTION')
    @undoable
    def handle_weight_by_modi(self):
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
        obj=bpy.context.object
        mode_t=obj.mode
        bpy.ops.kourin.vg_asign_new_group()
        vg=bpy.context.object.vertex_groups.active
        object_settings = obj.kourin_weight_transfer_settings
        object_settings.vertex_group=vg.name
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.kourin.skin_weight_transfer()
        bpy.ops.object.mode_set(mode=mode_t)
    
    @undoable
    def handle_use_automasking_boundary_face_sets(self,c):
        sculpt=bpy.context.scene.tool_settings.sculpt
        sculpt.use_automasking_boundary_face_sets=not sculpt.use_automasking_boundary_face_sets

class WeightPaintMenuWidget(QWidget):
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

        
        self.SculptQuickWigdet=EditQuickWigdet(self,ops=self.ops)
        self.SculptQuickWigdet.show()


        
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
    bl_idname = "qt.weight_paint_menu"
    bl_label = "编辑快捷菜单"
    @classmethod
    def poll(cls, context):
        o=context.active_object
        if o is not None and o.type=='MESH' and o.mode=='WEIGHT_PAINT':
            return True
        return False
    def key_space_release_ops(self):
        pass
    def key_space_press_ops(self):
        pass
    def set_embedded_qt(self, context, parent_hwnd, init_pos):
        return WeightPaintMenuWidget(context,parent_hwnd,init_pos,ops=self)