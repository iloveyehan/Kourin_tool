from functools import partial
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel,QHBoxLayout
import bpy

from .qt_toastwindow import ToastWindow
from ..utils.utils import undoable

class PreprocesseWigdet(QWidget):
    
    def __init__(self,parent):
        from .ui_widgets import Button
        super().__init__()
        self.ops=parent.ops
        # 创建布局
        self.qt_window=parent

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        h_1=QHBoxLayout()
        h_1.setContentsMargins(0, 0, 0, 0)
        h_1.setSpacing(0)
        h_2=QHBoxLayout()
        h_2.setContentsMargins(0, 0, 0, 0)
        h_2.setSpacing(0)
        layout.addLayout(h_1)
        layout.addLayout(h_2)
        # 添加标签
        for name,bt_name,check,tooltip in [
            ('材质','set_viewport_display_random',False,'把材质设置为随机\n方便查看穿模情况'),
            ('清理','clean_skeleton',False,'选中骨架\n移除所有没有权重的骨骼'),
            ('棍型','make_skeleton',False,'设置棍型骨架\n其他衣服骨骼设置为八面锥'),
            ('名称','show_bonename',True,'骨骼名称显示切换'),
            ('前面','in_front',False,'在前面'),
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
        h_1.addStretch()


        for name,bt_name,check,tooltip in [
            ('应用','pose_to_reset',False,'把当前POSE设置为默认POSE\n注意:需要选中骨骼'),
            ('合骨','combine_selected_bone_weights',False,'多选骨骼，合并权重到激活骨骼\n删除其他骨骼（支持镜像处理）'),
            ('改名','rename_armature',False,'把骨骼命名统一\n以激活骨架为准\n注意:可能有错误,需要检查'),
            ('合并','merge_armature',False,'合并骨架\n注意:以激活骨架为主'),
            # ('名称','show_bonename',True,'骨骼名称显示切换'),
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
        h_2.addStretch()



        # 设置布局到中央部件
        self.setLayout(layout)
    def button_handler(self):
        self.msg='操作完成'
        name = self.sender().property('bt_name')
        # print(f'dianjiele {name}')
        # 动态找到处理函数或从映射里取
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
        # print(f'dianjiele {name}')
        # 动态找到处理函数或从映射里取
        func = getattr(self, f"handle_{name}")
        bpy.app.timers.register(partial(func, checked))
    @undoable
    def handle_clean_skeleton(self):
        obj = bpy.context.active_object
        if not obj or obj.type != 'ARMATURE':
            self.msg="请选择一个骨骼对象"
            return
        bpy.ops.kourin.delete_unused_bones()
        return None
    @undoable
    def handle_combine_selected_bone_weights(self):
        obj=bpy.context.object
        
        self.qt_window.get_obj()

        if self.qt_window.obj is not None and self.qt_window.obj.type=='ARMATURE':

            md=self.qt_window.obj.mode
            bpy.ops.object.mode_set(mode='POSE')
            bpy.ops.kourin.combine_selected_bone_weights()
            bpy.ops.object.mode_set(mode=md)
    def handle_set_viewport_display_random(self): 
        bpy.ops.kourin.set_viewport_display_random()
    @undoable
    def handle_show_bonename(self,checked): 
        print('show_bonename')
        bpy.ops.kourin.show_bone_name(t_f=checked)
    @undoable
    def handle_pose_to_reset(self):
        bpy.ops.kourin.pose_to_reset()
    @undoable
    def handle_merge_armature(self):
        bpy.ops.kourin.merge_armatures()
    @undoable
    def handle_rename_armature(self):
        bpy.ops.kourin.rename_armatures()
    @undoable
    def handle_make_skeleton(self):
        bpy.ops.kourin.set_bone_display()
    def handle_in_front(self):
        self.qt_window.get_obj()
        if self.qt_window.obj.type=='ARMATURE':
            self.qt_window.obj.show_in_front = not self.qt_window.obj.show_in_front
