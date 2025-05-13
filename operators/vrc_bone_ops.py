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
    bl_idname = "armature.delete_unused_bones"
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


