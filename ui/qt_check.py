from functools import partial
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit
import re
import bpy

from .ui_widgets import Button
from ..utils.utils import undoable

class CheckWidget(QWidget):
    def __init__(self,param):
        super().__init__()
        # 主布局
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # 按钮行
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(5)

        # 检查按钮
        check_btn = Button('检查')
        check_btn.setProperty('bt_name', 'check_scene')
        check_btn.clicked.connect(self.button_handler)
        check_btn.setToolTip('检查场景中的命名、UV、集合等')
        btn_layout.addWidget(check_btn)

        # 清理按钮
        clean_btn = Button('清理')
        clean_btn.setProperty('bt_name', 'clean_scene')
        clean_btn.clicked.connect(self.button_handler)
        clean_btn.setToolTip('清理不在当前视图层或未链接到集合的Mesh和未使用的材质（包括fake user）')
        btn_layout.addWidget(clean_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # 结果显示区域
        self.result_view = QTextEdit()
        self.result_view.setReadOnly(True)
        self.result_view.setPlaceholderText('操作结果将在此显示...')
        layout.addWidget(self.result_view)

        self.setLayout(layout)

    def button_handler(self):
        name = self.sender().property('bt_name')
        func = getattr(self, f'handle_{name}')
        # 定时注册以确保在主线程执行
        bpy.app.timers.register(func)

    @undoable
    def handle_check_scene(self):
        results = []
        # 检查材质命名后缀是否重复（.001, .002 等）
        dup_mat = [m.name for m in bpy.data.materials if re.search(r"\.\d{3,}$", m.name)]
        results.append(f"重复后缀的材质: {', '.join(dup_mat) or '无'}")

        # 检查Mesh命名后缀重复
        dup_mesh = [o.name for o in bpy.data.objects if o.type=='MESH' and re.search(r"\.\d{3,}$", o.name)]
        results.append(f"重复后缀的Mesh: {', '.join(dup_mesh) or '无'}")

        # 检查UV层数量 (>1)
        uv_multi = [f"{o.name} ({len(o.data.uv_layers)}个UV)" for o in bpy.data.objects
                    if o.type == 'MESH' and len(o.data.uv_layers) > 1]
        results.append(f"多UV层Mesh: {', '.join(uv_multi) or '无'}")

                # 检查所有Mesh的UV层，并按UV名称分组
        uv_group = {}
        for obj in bpy.data.objects:
            if obj.type == 'MESH' and obj.data.uv_layers:
                for layer in obj.data.uv_layers:
                    uv_group.setdefault(layer.name, []).append(obj.name)
        # 只有当有多个UV组时才显示分组信息
        if len(uv_group) > 1:
            results.append("UV层分组:")
            for uv_name, objs in uv_group.items():
                line = f"  {uv_name}: {', '.join(objs)}"
                results.append(line)
        elif len(uv_group) == 1:
            # 只有一个UV名称存在，无需分组显示
            pass
        else:
            results.append("无UV层检测到")

        # 检查视图层中的多余集合，深度遍历子集合"，深度遍历子集合
        def collect_extra(layer_col, base_names):
            extras = []
            for child in layer_col.children:
                if child.name not in base_names:
                    extras.append(child.name)
                extras.extend(collect_extra(child, base_names))
            return extras
        root = bpy.context.view_layer.layer_collection
        base_names = {root.name, 'Collection'}
        extra_cols = collect_extra(root, base_names)
        results.append(f"删除多余集合: {', '.join(extra_cols) or '无'}")

        # 检查是否都是骨骼子集
        arm = next((o for o in bpy.context.scene.objects if o.type == 'ARMATURE'), None)
        if arm:
            non_child = [o.name for o in bpy.context.scene.objects if o.parent != arm and o !=arm]
            results.append(f"没把骨骼设为父级: {', '.join(non_child) or '无'}")
        else:
            results.append("场景中无骨骼Armature")

        # 检查灯光和相机
        lights = [o.name for o in bpy.context.scene.objects if o.type == 'LIGHT']
        cams = [o.name for o in bpy.context.scene.objects if o.type == 'CAMERA']
        results.append(f"删除灯光对象: {', '.join(lights) or '无'}")
        results.append(f"删除相机对象: {', '.join(cams) or '无'}")

        # 更新结果视图
        def update_view():
            # 构建HTML内容，支持红色UV名称
            html = ['<pre>']
            for line in results:
                if line.startswith('  '):
                    # UV组行，以两个空格开头
                    uv_name, objs = line.strip().split(': ', 1)
                    html.append(f"  <span style='color:red'>{uv_name}</span>: {objs}")
                else:
                    html.append(line)
            html.append('</pre>')
            self.result_view.setHtml('<br>'.join(html))
            return None
        bpy.app.timers.register(update_view)
        return None


    @undoable
    def handle_clean_scene(self):
        results = []
        # 当前视图层可见对象
        visible_objs = set(bpy.context.view_layer.objects)
        removed_names = []
        # 清理不在视图层或未链接到集合的Mesh对象
        for obj in list(bpy.data.objects):
            if obj.type == 'MESH':
                in_col = bool(obj.users_collection)
                if obj not in visible_objs or not in_col:
                    removed_names.append(obj.name)
                    bpy.data.objects.remove(obj, do_unlink=True)
        results.append(f"删除对象: {', '.join(removed_names) or '无'}")

        # 清理孤立的 Mesh 数据块
        removed_mesh_data = []
        for mesh in list(bpy.data.meshes):
            if mesh.users == 0:
                removed_mesh_data.append(mesh.name)
                bpy.data.meshes.remove(mesh)
        results.append(f"删除Mesh数据: {', '.join(removed_mesh_data) or '无'}")

        # 清理未使用的材质，包括 fake user
        removed_mats = []
        for mat in list(bpy.data.materials):
            if getattr(mat, 'use_fake_user', False):
                mat.use_fake_user = False
            if mat.users == 0:
                removed_mats.append(mat.name)
                bpy.data.materials.remove(mat)
        results.append(f"删除材质: {', '.join(removed_mats) or '无'}")

        # 更新结果视图
        def update_view():
            self.result_view.setPlainText("\n".join(results))
            return None
        bpy.app.timers.register(update_view)
        return None
