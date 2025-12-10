from pathlib import Path
import bpy
from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty, EnumProperty
import bpy
import json
import gzip
import os


    
def save_mesh_data(obj, filepath):
    mesh = obj.data
    data = {
        "name": obj.name,
        "vertices": [round(c, 6) for v in mesh.vertices for c in v.co],
        "faces": [list(p.vertices) for p in mesh.polygons],
        "vertex_groups": {},
        "shape_keys": {}
    }

    # 顶点组
    for vg in obj.vertex_groups:
        weights = []
        for v in mesh.vertices:
            try:
                w = vg.weight(v.index)
            except:
                w = 0.0
            weights.append(round(w, 6))
        data["vertex_groups"][vg.name] = weights

    # 形态键
    if mesh.shape_keys:
        for kb in mesh.shape_keys.key_blocks:
            if kb.name == "Basis":
                continue
            data["shape_keys"][kb.name] = [round(c, 6) for v in kb.data for c in v.co]

    # 保存压缩 JSON
    with gzip.open(filepath, 'wt', encoding='utf-8') as f:
        json.dump(data, f, separators=(',', ':'))  # 去掉空格，进一步压缩

    print(f"✅ 保存完成 (压缩): {filepath}")




class Kourin_save_surfacedeform(Operator):
    """保存save_surfacedeform"""
    bl_idname = "kourin.save_surfacedeform"
    bl_label = "保存绑定box"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        # 调用 Blender 内置 glTF 导入器
        try:
            # 使用示例
            obj = context.active_object
            if obj and obj.type == 'MESH':
                filepath = os.path.join(bpy.path.abspath("//"), f"{obj.name}_fitting_surface_meshdata.json.gz")
                save_mesh_data(obj, filepath)
            else:
                print("❌ 请先选择一个 MESH 对象")
            self.report({'INFO'}, f"保存成功 {filepath}")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"保存失败: {e}")
            return {'CANCELLED'}
def load_mesh_data(filepath):
    with gzip.open(filepath, 'rt', encoding='utf-8') as f:
        data = json.load(f)
    return data

def restore_mesh(data):
    mesh = bpy.data.meshes.new(data["name"] + "_restored")
    obj = bpy.data.objects.new(mesh.name, mesh)
    bpy.context.collection.objects.link(obj)

    # 还原顶点
    verts = [(data["vertices"][i], 
              data["vertices"][i+1], 
              data["vertices"][i+2]) for i in range(0, len(data["vertices"]), 3)]
    mesh.from_pydata(verts, [], data["faces"])
    mesh.update()

    # 还原顶点组
    for vg_name, weights in data["vertex_groups"].items():
        vg = obj.vertex_groups.new(name=vg_name)
        for i, w in enumerate(weights):
            if w > 0.0:
                vg.add([i], w, 'REPLACE')

    # 还原形态键
    if data["shape_keys"]:
        obj.shape_key_add(name="Basis")
        for sk_name, coords in data["shape_keys"].items():
            kb = obj.shape_key_add(name=sk_name)
            for i, v in enumerate(kb.data):
                v.co = (
                    coords[i*3],
                    coords[i*3+1],
                    coords[i*3+2]
                )
    obj.select_set(True)
    bpy.context.view_layer.objects.active=obj
    print(f"✅ 还原完成: {obj.name}")
    return obj

def set_arm_modi_obj():
    # 存储骨骼物体的列表
    armature_objects = []
    
    # 遍历场景中的所有物体
    for obj in bpy.context.scene.objects:
        # 检查物体是否为骨骼（ARMATURE）
        if obj.type == 'ARMATURE':
            armature_objects.append(obj)
            break
    
    # 检查是否找到骨骼物体
    if not armature_objects:
        print("未找到骨骼物体！")
    else:
        # 获取第一个找到的骨骼物体
        armature_obj = armature_objects[0]
    
        o=bpy.context.active_object
        print(f"正在为物体 {o.name} 添加 Armature 修改器...")

        # 添加 Armature 修改器
        armature_modifier = o.modifiers.new(name="Armature", type='ARMATURE')

        # 设置 Armature 修改器的 Object 属性为存储的骨骼物体
        armature_modifier.object = armature_obj
        armature_modifier.show_in_editmode = True
        armature_modifier.show_on_cage = True
class Kourin_save_loose_surfacedeform(Operator):
    """保存save_loose_surfacedeform"""
    bl_idname = "kourin.save_loose_surfacedeform"
    bl_label = "保存绑定box"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        # 调用 Blender 内置 glTF 导入器
        try:
            # 使用示例
            obj = context.active_object
            if obj and obj.type == 'MESH':
                filepath = os.path.join(bpy.path.abspath("//"), f"{obj.name}_loose_surface_meshdata.json.gz")
                save_mesh_data(obj, filepath)
            else:
                print("❌ 请先选择一个 MESH 对象")
            self.report({'INFO'}, f"保存成功 {filepath}")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"保存失败: {e}")
            return {'CANCELLED'}
def load_mesh_data(filepath):
    with gzip.open(filepath, 'rt', encoding='utf-8') as f:
        data = json.load(f)
    return data

def restore_mesh(data):
    mesh = bpy.data.meshes.new(data["name"] + "_restored")
    obj = bpy.data.objects.new(mesh.name, mesh)
    bpy.context.collection.objects.link(obj)

    # 还原顶点
    verts = [(data["vertices"][i], 
              data["vertices"][i+1], 
              data["vertices"][i+2]) for i in range(0, len(data["vertices"]), 3)]
    mesh.from_pydata(verts, [], data["faces"])
    mesh.update()

    # 还原顶点组
    for vg_name, weights in data["vertex_groups"].items():
        vg = obj.vertex_groups.new(name=vg_name)
        for i, w in enumerate(weights):
            if w > 0.0:
                vg.add([i], w, 'REPLACE')

    # 还原形态键
    if data["shape_keys"]:
        obj.shape_key_add(name="Basis")
        for sk_name, coords in data["shape_keys"].items():
            kb = obj.shape_key_add(name=sk_name)
            for i, v in enumerate(kb.data):
                v.co = (
                    coords[i*3],
                    coords[i*3+1],
                    coords[i*3+2]
                )
    obj.select_set(True)
    bpy.context.view_layer.objects.active=obj
    print(f"✅ 还原完成: {obj.name}")
    return obj

def set_arm_modi_obj():
    # 存储骨骼物体的列表
    armature_objects = []
    
    # 遍历场景中的所有物体
    for obj in bpy.context.scene.objects:
        # 检查物体是否为骨骼（ARMATURE）
        if obj.type == 'ARMATURE':
            armature_objects.append(obj)
            break
    
    # 检查是否找到骨骼物体
    if not armature_objects:
        print("未找到骨骼物体！")
    else:
        # 获取第一个找到的骨骼物体
        armature_obj = armature_objects[0]
    
        o=bpy.context.active_object
        print(f"正在为物体 {o.name} 添加 Armature 修改器...")

        # 添加 Armature 修改器
        armature_modifier = o.modifiers.new(name="Armature", type='ARMATURE')

        # 设置 Armature 修改器的 Object 属性为存储的骨骼物体
        armature_modifier.object = armature_obj
        armature_modifier.show_in_editmode = True
        armature_modifier.show_on_cage = True

MODULE_DIR = Path(__file__).parent.parent.resolve()
class Kourin_load_surfacedeform(Operator):
    """加载_surfacedeform"""
    bl_idname = "kourin.load_surfacedeform"
    bl_label = "加载绑定box"
    bl_options = {'REGISTER', 'UNDO'}
    file_name: StringProperty(
        default="",
    )
    def execute(self, context):
        from ..imgui_setup.imgui_global import GlobalImgui as gp
        try:
            # 使用示例
            print('当前文件夹:',MODULE_DIR)
            # self.file_name=''
            self.file_name=gp.get().surface_deform_name + '_fitting_surface'
            filepath = MODULE_DIR /'surface_deform'/ f"{self.file_name}_meshdata.json.gz"
            # filepath = os.path.join(bpy.path.abspath("//"), f"{self.file_name}_meshdata.json.gz")
            data = load_mesh_data(filepath)
            restore_mesh(data)
            set_arm_modi_obj()
            self.report({'INFO'}, f"加载成功 {filepath}")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"加载失败: {e}")
            return {'CANCELLED'}
class Kourin_load_loose_surfacedeform(Operator):
    """加载_surfacedeform"""
    bl_idname = "kourin.load_loose_surfacedeform"
    bl_label = "加载绑定box loose"
    bl_options = {'REGISTER', 'UNDO'}
    file_name: StringProperty(
        default="",
    )
    def execute(self, context):
        from ..imgui_setup.imgui_global import GlobalImgui as gp
        try:
            # 使用示例
            print('当前文件夹:',MODULE_DIR)
            
            self.file_name=gp.get().surface_deform_name + '_loose_surface'
            filepath = MODULE_DIR /'surface_deform'/ f"{self.file_name}_meshdata.json.gz"
            # filepath = os.path.join(bpy.path.abspath("//"), f"{self.file_name}_meshdata.json.gz")
            data = load_mesh_data(filepath)
            restore_mesh(data)
            set_arm_modi_obj()
            self.report({'INFO'}, f"加载成功 {filepath}")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"加载失败: {e}")
            return {'CANCELLED'}


import bpy
import bmesh
from mathutils import Vector


def is_face_concave(face):
    """检测一个 n 边形是否为凹面"""
    verts = [v.co for v in face.verts]
    if len(verts) <= 3:
        return False  # 三角面不可能是凹的

    normal = face.normal
    sign = None
    for i in range(len(verts)):
        v1 = verts[i] - verts[i-1]
        v2 = verts[(i+1) % len(verts)] - verts[i]
        cross = v1.cross(v2).dot(normal)
        if cross != 0:
            this_sign = cross > 0
            if sign is None:
                sign = this_sign
            elif sign != this_sign:
                return True  # 出现不同方向，说明是凹多边形
    return False


class MESH_OT_select_concave_faces(bpy.types.Operator):
    """检测并选中所有凹多边形的顶点"""
    bl_idname = "kourin.select_concave_faces"
    bl_label = "选择凹多边形顶点"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        # 在编辑模式下运行
        obj = bpy.context.edit_object
        bm = bmesh.from_edit_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        bm.verts.ensure_lookup_table()

        # 收集凹面列表
        concave_faces = []
        for f in bm.faces:
            if len(f.verts) > 4:  # 只检查 ngon
                if is_face_concave(f):
                    concave_faces.append(f)

        print(f"发现 {len(concave_faces)} 个凹多边形")

        # 取消所有顶点的选择
        for v in bm.verts:
            v.select = False

        # 遍历凹面列表，把顶点选中
        for f in concave_faces:
            for v in f.verts:
                v.select = True

        # 更新 mesh 显示
        bmesh.update_edit_mesh(obj.data)

        self.report({'INFO'}, f"发现 {len(concave_faces)} 个凹多边形")
        return {'FINISHED'}