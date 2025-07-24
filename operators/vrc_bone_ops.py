import bpy
from pathlib import Path
import numpy as np

from .vertex_group import determine_and_convert

from ..utils.mesh_data_transfer import MeshData
from ..utils.armature import finde_common_bones, pose_to_reset

from ..common.class_loader.auto_load import ClassAutoloader
vrc_bone_ops=ClassAutoloader(Path(__file__))
def reg_vrc_bone_ops():
    vrc_bone_ops.init()
    vrc_bone_ops.register()
def unreg_vrc_bone_ops():
    vrc_bone_ops.unregister()
class DeleteUnusedBonesOperator(bpy.types.Operator):
    """删除没有权重的骨骼及其子骨骼，保留有直接子骨骼权重的主骨骼"""
    bl_idname = "kourin.delete_unused_bones"
    bl_label = "Delete Unused Bones"
    bl_options = {'REGISTER', 'UNDO'}
    @classmethod
    def poll(cls, context):
        obj=bpy.context.active_object
        return obj is not None and obj.type == 'ARMATURE'

    def get_bone_hierarchy(self, bone):
        """递归获取骨骼及其所有子骨骼"""
        bones = [bone]
        for child in bone.children:
            bones.extend(self.get_bone_hierarchy(child))
        return bones

    def has_vertex_weights(self, armature, bone_name):
        """检查骨骼是否绑定到任何顶点"""
        for obj in bpy.context.scene.objects:
            if obj.type == 'MESH':
                for modifier in obj.modifiers:
                    if modifier.type == 'ARMATURE' and modifier.object == armature:
                        if obj.vertex_groups.find(bone_name) >= 0:
                            return True
        return False

    def should_keep_bone(self, armature, bone):
        """判断骨骼是否需要保留"""
        # 如果骨骼自身有权重
        if self.has_vertex_weights(armature, bone.name):
            return True
        
        # 如果直接子骨骼中有任何一个有权重
        for child in bone.children:
            if self.has_vertex_weights(armature, child.name):
                return True
        
        return False

    def execute(self, context):
        armature = context.object
        if not armature or armature.type != 'ARMATURE':
            self.report({'ERROR'}, "No armature selected!")
            return {'CANCELLED'}

        bpy.ops.object.mode_set(mode='EDIT')
        bones_to_delete = []

        # 第一遍收集所有可能删除的骨骼
        for bone in armature.data.edit_bones:
            # 检查是否需要保留该骨骼
            if not self.should_keep_bone(armature, bone):
                bones_to_delete.append(bone.name)
        for bone_name in bones_to_delete:
            if bone_name in armature.data.edit_bones:  # 检查骨骼是否存在
                armature.data.edit_bones.remove(armature.data.edit_bones[bone_name])  # 删除骨骼

        bpy.ops.object.mode_set(mode='OBJECT')
        self.report({'INFO'}, "未使用的骨骼已删除！保留有直接子节点权重的父级骨骼。")
        return {'FINISHED'}

class SetBoneDisplayOperator(bpy.types.Operator):
    """将激活骨架视图显示为棍形，其他骨骼显示为八面锥"""
    bl_idname = "kourin.set_bone_display"
    bl_label = "设置骨骼显示方式"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        # 获取当前激活的骨架对象
        active_armature = context.active_object
        if not active_armature or active_armature.type != 'ARMATURE':
            self.report({'WARNING'}, "请选择一个骨架对象")
            return {'CANCELLED'}
        # 遍历场景中的所有骨架对象
        for obj in context.scene.objects:
            if obj.type == 'ARMATURE':
                # 如果是激活的骨架，设置显示为棍形
                if obj == active_armature:
                    obj.data.display_type = 'STICK'
                # 其他骨架设置为八面锥
                else:
                    obj.data.display_type = 'OCTAHEDRAL'
        self.report({'INFO'}, "骨骼显示方式已设置")
        return {'FINISHED'}
class KourinSetViewportDisplayRandomOperator(bpy.types.Operator):
    """将激活骨架视图显示为棍形，其他骨骼显示为八面锥"""
    bl_idname = "kourin.set_viewport_display_random"
    bl_label = "设置物体显示方式为随机"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.color_type = 'RANDOM'
        # context.space_data.shading.color_type = 'RANDOM'
        return {'FINISHED'}
    
class KourinShowBoneNameOperator(bpy.types.Operator):
    """将激活骨架视图显示为棍形，其他骨骼显示为八面锥"""
    bl_idname = "kourin.show_bone_name"
    bl_label = "设置物体显示方式为随机"
    bl_options = {'REGISTER', 'UNDO'}
    t_f: bpy.props.BoolProperty(name="t_f", default=True)
    def execute(self, context):
        for b in context.selected_objects:
            if b.type=='ARMATURE':
                b.data.show_names = self.t_f
        return {'FINISHED'}
class KourinPoseToReset(bpy.types.Operator):
    bl_idname = 'kourin.pose_to_reset'
    bl_label = '应用pose模式的调整'
    bl_description = '应用pose模式的调整,设置为默认姿势'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object.type == 'ARMATURE'
    def execute(self, context):
        armature=bpy.context.object
        mode=bpy.context.object.mode
        bpy.ops.object.mode_set(mode='OBJECT')
        pose_to_reset(armature)
        bpy.ops.object.mode_set(mode=mode)
        self.report({'INFO'}, "应用完成")
        return {'FINISHED'}


class Kourin_merge_armatures(bpy.types.Operator):
    """Merge two selected Armature objects into one, preserving bone hierarchy exactly as specified."""
    bl_idname = "kourin.merge_armatures"
    bl_label = "Merge Armatures"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        if context.active_object is None:
            return False
        arms = [o for o in context.selected_objects if o.type == 'ARMATURE']
        return len(arms) == 2 and context.active_object in arms
    
    def execute(self, context):
        bpy.ops.object.mode_set(mode='OBJECT')
        active_arm = context.active_object
        other_arm = [o for o in context.selected_objects if o != active_arm][0]
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        # —— 关键改动：遍历时立即排除重名骨骼 —— 
        dupes = set()
        child_dupes = {}
        unique_info = {}  # bone_name -> (parent_name or None, use_connect)

        for bone in other_arm.data.bones:
            if bone.name in active_arm.data.bones:
                # 这是重名骨骼，只记录它在 other_arm 下的子骨骼信息
                dupes.add(bone.name)
                # child_dupes[bone.name] = [
                #     (ch.name, ch.use_connect) for ch in bone.children
                # ]
                # **跳过下面的唯一骨骼记录逻辑**
                continue

            # 只有非重名的骨骼才会进到这里
            parent = bone.parent.name if bone.parent else None
            unique_info[bone.name] = (parent, bone.use_connect)

        # 2) 删除 other_arm 中的重名骨骼
        
        bpy.ops.object.select_all(action='DESELECT')
        context.view_layer.objects.active = other_arm
        other_arm.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        for name in dupes:
            if name in other_arm.data.edit_bones:
                other_arm.data.edit_bones.remove(other_arm.data.edit_bones[name])
        bpy.ops.object.mode_set(mode='OBJECT')

        # 3) 合并到 active_arm
        bpy.ops.object.select_all(action='DESELECT')
        active_arm.select_set(True)
        other_arm.select_set(True)
        context.view_layer.objects.active = active_arm
        bpy.ops.object.join()

        # 4) 在合并后的骨架中还原父子关系
        bpy.ops.object.mode_set(mode='EDIT')
        eb = active_arm.data.edit_bones

        # 4.1 重名骨骼：完全以 active_arm 为准，只还原它们原来在 other_arm 下的子关系
        for pname, children in child_dupes.items():
            if pname not in eb:
                continue
            parent_b = eb[pname]
            for cname, is_conn in children:
                if cname in eb:
                    ch_b = eb[cname]
                    ch_b.parent = parent_b
                    ch_b.use_connect = is_conn

        # 4.2 唯一骨骼：还原它们在 other_arm 中的父子关系
        for bname, (pname, is_conn) in unique_info.items():
            if bname not in eb:
                continue
            bone = eb[bname]
            if pname and pname in eb:
                bone.parent = eb[pname]
                bone.use_connect = is_conn
            else:
                bone.parent = None
                bone.use_connect = False

        bpy.ops.object.mode_set(mode='OBJECT')

        # 5) 更新所有 MESH 的 Armature Modifier 指向
        for obj in context.scene.objects:
            if obj.type == 'MESH':
                for mod in obj.modifiers:
                    if mod.type == 'ARMATURE':
                        mod.object = active_arm

        return {'FINISHED'}
class Kourin_rename_armatures(bpy.types.Operator):
    """把两个骨架的相同部位的骨骼统一命名,以激活的为准"""
    bl_idname = "kourin.rename_armatures"
    bl_label = "Merge Armatures"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        # 确保恰好两个骨架被选中，且有一个活动对象
        if context.active_object is None:
            return False
        armatures = [obj for obj in context.selected_objects if obj.type == 'ARMATURE']
        return (len(armatures) == 2 and context.active_object.type == 'ARMATURE')
    
    def execute(self, context):
        finde_common_bones()
        return {'FINISHED'}
class Kourin_combine_selected_bone_weights(bpy.types.Operator):
    """多选骨骼，合并权重到激活骨骼，删除其他骨骼（支持镜像处理）"""
    bl_idname = "kourin.combine_selected_bone_weights"
    bl_label = "合并骨骼权重，删除其他骨骼"
    bl_options = {'REGISTER', 'UNDO'}
    mirror: bpy.props.BoolProperty(
        name="镜像处理",
        description="对选中骨骼的对称骨骼执行相同操作",
        default=True
    )
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'ARMATURE'
    def execute(self, context):
        from .vertex_group import determine_and_convert
        armature = context.active_object
        active_bone = context.active_bone
        child_objs = [obj for obj in armature.children if obj.type == 'MESH']
        # 获取镜像骨骼名称
        if self.mirror:
            mirror_active_name = determine_and_convert(active_bone.name)[2]
        mirror_active_bone = None
        if self.mirror and mirror_active_name:
            mirror_active_bone = armature.data.bones.get(mirror_active_name)
        # 切换到姿态模式获取选中骨骼
        bpy.ops.object.mode_set(mode='POSE')
        pose_bones = context.selected_pose_bones
        print('选中',context.selected_pose_bones)
        print('选中1',context.selected_editable_bones)
        # 处理所有子网格对象
        for obj in child_objs:
            mesh_data = MeshData(obj)
            v_count = len(obj.data.vertices)
            # 初始化权重数组
            weights_active = np.zeros(v_count, dtype=np.float32)
            weights_active.shape = (v_count, 1)
            weights_mirror = np.zeros_like(weights_active) if mirror_active_bone else None
            # 遍历所有选中骨骼
            for pose_bone in pose_bones:
                bone_name = pose_bone.name
                # 处理原始骨骼权重
                if (wgts := mesh_data.get_vertex_group_weights(bone_name)) is not None:
                    weights_active += wgts
                # 处理镜像骨骼权重
                
                if self.mirror:
                    if mirror_name := determine_and_convert(bone_name)[2]:
                        
                        if (mirror_wgts := mesh_data.get_vertex_group_weights(mirror_name)) is not None:
                            print(pose_bone.name,weights_mirror,mirror_wgts)
                            weights_mirror += mirror_wgts
                            print(pose_bone.name,weights_mirror,mirror_wgts)
                print(123,pose_bone.name)
            # 写入权重数据
            mesh_data.set_vertex_group_weights(weights_active, active_bone.name)
            if mirror_active_bone and weights_mirror is not None:
                mesh_data.set_vertex_group_weights(weights_mirror, mirror_active_bone.name)
            # 清理顶点组
            self.cleanup_vertex_groups(obj, pose_bones, active_bone, mirror_active_bone)
            mesh_data.free_memory()
        print('选中2',context.selected_pose_bones)
        print('选中2',context.selected_editable_bones)
        # 删除骨骼
        print('mirror_active_bone',mirror_active_bone)
        self.remove_bones(context, armature, active_bone, mirror_active_bone)
        self.report({'INFO'}, '合并完成（镜像已启用）' if self.mirror else '合并完成')
        return {'FINISHED'}

    def cleanup_vertex_groups(self, obj, pose_bones, active_bone, mirror_active_bone):
        """清理原始和镜像顶点组"""
        from .vertex_group import determine_and_convert
        vg_names_to_keep = {active_bone.name}
        if mirror_active_bone:
            vg_names_to_keep.add(mirror_active_bone.name)
        for bone in pose_bones:
            # 删除原始顶点组
            if bone.name in obj.vertex_groups and bone.name not in vg_names_to_keep:
                obj.vertex_groups.remove(obj.vertex_groups[bone.name])

            # 删除镜像顶点组
            if self.mirror:
                if mirror_name := determine_and_convert(bone.name)[2]:
                    if mirror_name in obj.vertex_groups and mirror_name not in vg_names_to_keep:
                        obj.vertex_groups.remove(obj.vertex_groups[mirror_name])

    def remove_bones(self, context, armature, active_bone, mirror_active_bone):
        """删除骨骼逻辑"""
        from .vertex_group import determine_and_convert
        edit_bones = armature.data.edit_bones
        # 收集需要删除的骨骼
        to_remove = []
        for bone in context.selected_pose_bones:
            print('选中的骨骼',bone.name)
            if bone.name == active_bone.name or \
                    (mirror_active_bone and bone.name == mirror_active_bone.name):
                continue

            to_remove.append(bone.name)

            # 添加镜像骨骼到删除列表
            print('self.mirror:',self.mirror)
            if self.mirror:
                if mirror_name := determine_and_convert(bone.name)[2]:
                    print(bone.name,mirror_name)
                    # if mirror_name in edit_bones:
                    to_remove.append(mirror_name)
                    print(2,bone.name,mirror_name)
                        
        # 去重并删除
        print('to_remove')
        for b in to_remove:
            print(b)
        bpy.ops.object.mode_set(mode='EDIT')
        seen = set()
        for bname in to_remove:
            if bname not in seen and bname in edit_bones:
                seen.add(bname)
                edit_bones.remove(edit_bones[bname])
                print('删除',bname)

        bpy.ops.object.mode_set(mode='POSE')
class Kourin_sync_active_bone_name(bpy.types.Operator):
    """同步两个Armature的Active Bone名称"""
    bl_idname = "kourin.sync_active_bone_name"
    bl_label = "同步Active Bone名称"
    bl_options = {'REGISTER', 'UNDO'}
    mirror: bpy.props.BoolProperty(
        name="镜像处理",
        description="对选中骨骼的对称骨骼执行相同操作",
        default=True
    )
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'ARMATURE'
    def execute(self, context):
        # 获取当前选中的两个Armature对象
        armatures = [obj for obj in context.selected_objects if obj.type == 'ARMATURE']
        armature = context.active_object
        active_bone = context.active_bone
        # 获取镜像骨骼名称
        mirror_active_name = determine_and_convert(active_bone.name)[2]

        if len(armatures) != 2:
            self.report({'ERROR'}, "请确保选中了两个Armature对象")
            return {'CANCELLED'}
        ac_bone_name=bpy.context.active_pose_bone.name
        for a in armatures:
            if a==bpy.context.active_object:
                continue
            mirror_name = determine_and_convert(a.data.bones.active.name)[2]
            print('mirror_name',mirror_name,'mirror_active_name',mirror_active_name)
            if self.mirror:
                print('mirror mirror_name',mirror_name,'mirror_active_name',mirror_active_name)
                mirror_bone = a.data.bones.get(mirror_name)
                print(mirror_bone)
                if mirror_bone is not None:
                    mirror_bone.name=mirror_active_name
                    
            a.data.bones.active.name=ac_bone_name
        
        self.report({'INFO'}, f"已将第二个Armature的Active Bone名字改为: {ac_bone_name}")
        return {'FINISHED'}