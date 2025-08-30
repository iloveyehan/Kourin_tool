import platform
import bpy
import numpy as np
import ctypes
from functools import partial
from pathlib import Path
import platform
import sys
import weakref
from PySide6.QtWidgets import QComboBox, QWidget,QVBoxLayout, QLabel,QHBoxLayout



from ..ui.qt_toastwindow import ToastWindow

from .ui_widgets import BaseWidget, Button
from ..utils.utils import undoable

from ..operators.base_qt_ops import BaseQtOperator
import sys, math
from functools import partial
from PySide6.QtWidgets import QApplication, QWidget, QPushButton, QGraphicsDropShadowEffect
from PySide6.QtGui import QPainter, QColor, QPen, QCursor,QWindow,QMouseEvent
from PySide6.QtCore import Qt, QPointF, QRectF, QSize,QPoint
import zipfile
import xml.etree.ElementTree as ET

def read_xlsx_strings(filepath):
    # xlsx 文件其实是 zip
    with zipfile.ZipFile(filepath, "r") as z:
        # 读取共享字符串表 sharedStrings.xml
        with z.open("xl/sharedStrings.xml") as f:
            tree = ET.parse(f)
            root = tree.getroot()

            # Excel 的 XML 使用命名空间，需要处理
            ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
            strings = [t.text for t in root.findall(".//a:t", ns)]

            return strings
filepath = Path(__file__).parent.parent.resolve() /'surface_deform'/ "name_list.xlsx"
# 测试
strings_list = read_xlsx_strings(filepath)

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
        h_3=QHBoxLayout()
        # h_2_3=QVBoxLayout()
        h_2_1.setContentsMargins(0, 0, 0, 0)
        h_2_1.setSpacing(0)
        settings = bpy.context.scene.kourin_weight_transfer_settings
        o=settings.source_object
        if o is not None and o.type=='MESH':
            if o.name==bpy.context.active_object.name:
                name=self.tr('权重来源不能是自己')
            else:
                name=o.name
        else:
            name='None'
        


        layout.addWidget(QLabel(name))# 第一行

        layout.addLayout(h_1)
        layout.addLayout(h_2)
        layout.addLayout(h_3)
        h_2.addLayout(h_2_1)
        
        

        # h_2.addLayout(h_2_3)
        
        layout.addStretch()
        # 添加标签
        for icon,bt_name,check,tooltip in [
            # ('hide_off.svg','faceset_from_visible',False,'从视图可见顶点创建面组'),
            ('editmode_hlt.svg','faceset_from_edit',False,self.tr('从选中的顶点创建面组')),
            ('armature_data.svg','edit_to_paint_with_a',False,self.tr('选中骨架,并进入权重绘制')),
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
        h_1.addStretch()#横向图标行
        self.checkable_buttons = {}
        for name,bt_name,check,tooltip in [
            (self.tr('组'),'vg_asign',False,self.tr('创建顶点组')),
            (self.tr('传权重,修改器'),'weight_by_modi',False,self.tr('用数据传递修改器')),
            (self.tr('传权重,算法'),'weight_by_algorithm',False,self.tr('用算法传权重')),
            
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
            h_2_1.addWidget(btn)#横向h2
        # h_2.addStretch()
        #插入combox 选择预设
        self.combo = QComboBox()
        self.combo.addItems(strings_list)
        self.combo.currentTextChanged.connect(self.on_combo_changed)
        # 如果上次选择的项存在，设置为当前选择项
        from .qt_global import GlobalProperty as gp
        if gp.get().surface_defrom_name is not None:
            index = self.combo.findText(gp.get().surface_defrom_name)
            if index >= 0:
                self.combo.setCurrentIndex(index)
        self.combo.setStyleSheet("""
            QComboBox {
                color: white; /* 设置字体颜色为白色 */
                background-color: black; /* 设置背景颜色为黑色 */
            }
            QComboBox QAbstractItemView {
                color: white; /* 下拉列表的字体颜色 */
                background-color: black; /* 下拉列表的背景颜色 */
            }
        """)
        h_2_1.addWidget(self.combo)

        h_2.addStretch()

        self.checkable_buttons = {}
        for name,bt_name,check,tooltip in [
            (self.tr('紧身'),'surface_defrom',False,self.tr('紧身类型')),
            (self.tr('宽松'),'surface_defrom_loose',False,self.tr('宽松类型')),
            
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
            h_3.addWidget(btn)#横向h2

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
        self.msg=self.tr('操作完成')
        name = self.sender().property('bt_name')
        func = getattr(self, f"handle_{name}")

        def wrapped_func():
            func()  # 原函数执行
            # 然后注册 toast 显示（下一帧）
            def show_toast():
                if self.msg=='':
                    if hasattr(self,'ops') and hasattr(self.ops,'auto_close'):
                        self.ops.auto_close=True
                        return
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
    def handle_surface_defrom(self):
        from ..ui.qt_global import GlobalProperty as gp
        # 备份
        this_obj=bpy.context.active_object
        bpy.ops.kourin.vg_asign_new_group()
        vg=bpy.context.object.vertex_groups.active
        mode_t=this_obj.mode
        selected_t=bpy.context.selected_objects
        #开始
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.kourin.load_surfacedeform(file_name=gp.get().surface_defrom_name + '_fitting_surface')
        surface_obj=bpy.context.active_object
        sk_surface_obj=surface_obj.data.shape_keys.key_blocks
        sk_num=len(surface_obj.data.shape_keys.key_blocks)
        temp_objs=[]#创建了根据sk命名的临时obj
        for i in range(sk_num):
            if i:
                o = this_obj.copy()
                o.data = this_obj.data.copy()
                o.name = f'temp_{sk_surface_obj[i].name}'
                o.data.name = f'temp_{sk_surface_obj[i].name}'
                bpy.context.collection.objects.link(o)
                temp_objs.append(o)
                print('temp创建完成',i)
        #切换this_obj绑定到sk_surface_obj,依次切换value
        for o in temp_objs:
            mod=o.modifiers.new('temp_sd','SURFACE_DEFORM')     
            mod.target=surface_obj
            mod.vertex_group=vg.name
            o.select_set(True)
            bpy.context.view_layer.objects.active=o
            bpy.ops.object.surfacedeform_bind(modifier="temp_sd")
            sk_surface_obj[o.name[5:]].value=1
            bpy.ops.kourin.apply_modi_with_shapekey(mod_name=mod.name)
            sk_surface_obj[o.name[5:]].value=0
        #合并到this_obj
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active=this_obj
        this_obj.select_set(True)
        object_settings = this_obj.kourin_weight_transfer_settings
        object_settings.vertex_group=vg.name
        bpy.ops.kourin.skin_weight_transfer()
        for o in temp_objs:
            o.select_set(True)
        bpy.ops.object.join_shapes()
        for o in temp_objs:
            bpy.data.meshes.remove(o.data)
        bpy.data.meshes.remove(surface_obj.data)
        
        for sk in this_obj.data.shape_keys.key_blocks:
            if 'temp' in sk.name:
                sk.name=sk.name[5:]

        # bpy.ops.kourin.skin_weight_transfer()
        bpy.ops.object.select_all(action='DESELECT')
        for o in selected_t:
            o.select_set(True)
        bpy.context.view_layer.objects.active=this_obj
        bpy.ops.object.mode_set(mode=mode_t)
        
    @undoable
    def handle_surface_defrom_loose(self):
        from ..ui.qt_global import GlobalProperty as gp
        # 备份
        this_obj=bpy.context.active_object
        bpy.ops.kourin.vg_asign_new_group()
        vg=bpy.context.object.vertex_groups.active
        mode_t=this_obj.mode
        selected_t=bpy.context.selected_objects
        #开始
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.kourin.load_loose_surfacedeform(file_name=gp.get().surface_defrom_name + '_loose_surface')
        surface_obj=bpy.context.active_object
        sk_surface_obj=surface_obj.data.shape_keys.key_blocks
        sk_num=len(surface_obj.data.shape_keys.key_blocks)
        temp_objs=[]#创建了根据sk命名的临时obj
        for i in range(sk_num):
            if i:
                o = this_obj.copy()
                o.data = this_obj.data.copy()
                o.name = f'temp_{sk_surface_obj[i].name}'
                o.data.name = f'temp_{sk_surface_obj[i].name}'
                bpy.context.collection.objects.link(o)
                temp_objs.append(o)
                print('temp创建完成',i)
        #切换this_obj绑定到sk_surface_obj,依次切换value
        for o in temp_objs:
            mod=o.modifiers.new('temp_sd','SURFACE_DEFORM')     
            mod.target=surface_obj
            mod.vertex_group=vg.name
            o.select_set(True)
            bpy.context.view_layer.objects.active=o
            bpy.ops.object.surfacedeform_bind(modifier="temp_sd")
            sk_surface_obj[o.name[5:]].value=1
            bpy.ops.kourin.apply_modi_with_shapekey(mod_name=mod.name)
            sk_surface_obj[o.name[5:]].value=0
        #合并到this_obj
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active=this_obj
        this_obj.select_set(True)
        object_settings = this_obj.kourin_weight_transfer_settings
        object_settings.vertex_group=vg.name
        bpy.ops.kourin.skin_weight_transfer()
        for o in temp_objs:
            o.select_set(True)
        bpy.ops.object.join_shapes()
        for o in temp_objs:
            bpy.data.meshes.remove(o.data)
        bpy.data.meshes.remove(surface_obj.data)
        
        for sk in this_obj.data.shape_keys.key_blocks:
            if 'temp' in sk.name:
                sk.name=sk.name[5:]

        # bpy.ops.kourin.skin_weight_transfer()
        bpy.ops.object.select_all(action='DESELECT')
        for o in selected_t:
            o.select_set(True)
        bpy.context.view_layer.objects.active=this_obj
        bpy.ops.object.mode_set(mode=mode_t)
        
    def on_combo_changed(self, text):
        from .qt_global import GlobalProperty as GP
        try:
            GP.get().surface_defrom_name = text
            print(f"设置 vg_mirror_search = {text}")
        except Exception as e:
            print("设置失败：", e)
    @undoable
    def handle_edit_to_paint_with_a(self):
        self.msg=''
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
        bpy.ops.object.mode_set(mode='SCULPT')
        bpy.ops.sculpt.face_sets_create(mode='SELECTION')
    @undoable
    def handle_weight_by_modi(self):
        from ..utils.armature import comfirm_one_arm,get_arm_modi_obj
        obj=bpy.context.object
        if not comfirm_one_arm(obj):
            self.msg=self.tr('有多个可用的骨骼修改器,先禁用多余的')
            return
        modi_arm=get_arm_modi_obj(obj)
        settings = bpy.context.scene.kourin_weight_transfer_settings
        if not settings.source_object:
            self.msg=self.tr('先设置权重来源')
            print(self.msg)
            return
        
        mode_t=obj.mode
        bpy.ops.kourin.vg_asign_new_group()
        bpy.ops.object.mode_set(mode='OBJECT')
        if modi_arm:
            pose_t=modi_arm.object.data.pose_position
            modi_arm.object.data.pose_position='REST'
        bpy.ops.kourin.vg_trans_modi()
        modi=obj.modifiers.active
        bpy.ops.object.datalayout_transfer(modifier=modi.name)
        try:
            bpy.ops.object.modifier_apply(modifier=modi.name, report=True)
        except:
            bpy.ops.kourin.apply_modi_with_shapekey(mod_name=modi.name)
        if modi_arm:
            modi_arm.object.data.pose_position=pose_t
        bpy.ops.object.mode_set(mode=mode_t)
    @undoable
    def handle_weight_by_algorithm(self):
        from ..utils.armature import comfirm_one_arm,get_arm_modi_obj
        obj=bpy.context.object
        if not comfirm_one_arm(obj):
            self.msg=self.tr('有多个可用的骨骼修改器,先禁用多余的')
            return
        modi=get_arm_modi_obj(obj)
        

        settings = bpy.context.scene.kourin_weight_transfer_settings
        if not settings.source_object:
            self.msg=self.tr('先设置权重来源')
            print(self.msg)
            return
        
        mode_t=obj.mode
        # pose_t=bpy.context.object.data.pose_position = 'POSE'

        bpy.ops.kourin.vg_asign_new_group()
        vg=bpy.context.object.vertex_groups.active
        object_settings = obj.kourin_weight_transfer_settings
        object_settings.vertex_group=vg.name
        bpy.ops.object.mode_set(mode='OBJECT')
        if modi:
            pose_t=modi.object.data.pose_position
            modi.object.data.pose_position='REST'
        bpy.ops.kourin.skin_weight_transfer()
        if modi:
            modi.object.data.pose_position=pose_t
        bpy.ops.object.mode_set(mode=mode_t)
        try:
            obj.vertex_groups.remove(vg) 
        except:
            print('顶点组不存在')
    # @undoable
    # def handle_surface_defrom(self):
    #     bpy.ops.kourin.load_surfacedeform(file_name='airi_fitting_surface')
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
    auto_close=False
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