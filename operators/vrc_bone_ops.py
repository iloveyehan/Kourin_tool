import bpy
from pathlib import Path
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
