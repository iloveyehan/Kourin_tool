import bpy
from typing import List, Optional, Dict, Set
from pathlib import Path

class SelectBoneWithChildren(bpy.types.Operator):
    """Select active bone and all its children in Edit Mode"""
    bl_idname = "kourin.select_bone_with_children"
    bl_label = "Select Bone with Children"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object

        if not obj or obj.type != 'ARMATURE' or context.mode != 'EDIT_ARMATURE':
            self.report({'WARNING'}, "Must be in Edit Mode with an armature")
            return {'CANCELLED'}

        edit_bones = obj.data.edit_bones
        active = edit_bones.active

        if not active:
            self.report({'WARNING'}, "No active bone")
            return {'CANCELLED'}

        # 先清除所有选中状态
        for b in edit_bones:
            b.select_head = False
            b.select_tail = False
            b.select = False

        # 递归选中当前骨骼 + 所有子骨骼
        def select_recursive(bone):
            bone.select_head = True
            bone.select_tail = True
            bone.select = True
            for child in bone.children:
                select_recursive(child)

        select_recursive(active)

        active.select_head = False
        active.select_tail = False
        active.select = False

        return {'FINISHED'}


class RemoveTopBones(bpy.types.Operator):
    """Deselect top bones of each selected bone chain with branch logic"""
    bl_idname = "kourin.remove_top_bones"
    bl_label = "Deselect Top Bones of Chains (Branch Logic)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object

        if not obj or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Active object is not an armature")
            return {'CANCELLED'}

        if context.mode != 'EDIT_ARMATURE':
            self.report({'WARNING'}, "Must be in Edit Armature mode")
            return {'CANCELLED'}

        eb = obj.data.edit_bones
        selected = {b for b in eb if b.select}
        
        #分支
        pre_deselect=[]
        for b in selected:
            if b.parent in selected and len(b.parent.children)>1 and len(b.children)>1:
                pre_deselect.append(b)
        pre_deselect=set(pre_deselect)
        for b in pre_deselect:
            selected.remove(b)
            b.select = False
            b.select_head = False
            b.select_tail = False

            
        top_selected = [
            b for b in selected
            if b.select and (b.parent is None or not b.parent.select)
        ]

        to_deselect = set()
        to_deselect.update(top_selected)
        for bone in selected:
            parent = bone.parent
            children = [c for c in bone.children if c in selected]
            if parent in to_deselect and not len(children) and len(parent.children)>1:
                to_deselect.add(bone)

        for b in to_deselect:
            b.select = False
            b.select_head = False
            b.select_tail = False

        return {'FINISHED'}
class Kourin_use_connect(bpy.types.Operator):
    """Deselect top bones of each selected bone chain with branch logic"""
    bl_idname = "kourin.use_connect"
    bl_label = "Deselect Top Bones of Chains (Branch Logic)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object

        if not obj or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Active object is not an armature")
            return {'CANCELLED'}

        if context.mode != 'EDIT_ARMATURE':
            self.report({'WARNING'}, "Must be in Edit Armature mode")
            return {'CANCELLED'}

        eb = obj.data.edit_bones
        for b in eb:
            if b.select:
                b.use_connect = True

        

        return {'FINISHED'}