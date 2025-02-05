
from pathlib import Path
import bpy
import bmesh
from bpy.props import (
    BoolProperty,
    FloatProperty,
    IntProperty,
    EnumProperty,
    FloatVectorProperty,
)
from bpy.types import Operator, Panel, PropertyGroup
from mathutils import Vector

from ..common.class_loader.auto_load import ClassAutoloader
trans=ClassAutoloader(Path(__file__))
def reg_trans():
    trans.init()
    trans.register()
def unreg_trans():
    trans.unregister()
class ARI_OT_MoveVerPos(Operator):
    """
    模拟MEL中 AriTransferPosition_MoveVerPos
    根据用户设定的moveMode(距离/拓扑/ID)等，去匹配并移动
    """
    bl_idname = "ari_tools.move_verpos"
    bl_label = "Search/Move"

    # mode:
    #  1 => Search
    #  2 => Move
    mode: IntProperty(default=1)

    def execute(self, context):
        props = context.scene.ari_transfer_position_settings
        obj = context.active_object
        global source_verts_positions, source_verts_indices
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "请选中一个网格物体并进入编辑模式")
            return {'CANCELLED'}

        bm = bmesh.from_edit_mesh(obj.data)
        if not bm:
            self.report({'ERROR'}, "请进入编辑模式")
            return {'CANCELLED'}

        # 如果没有源数据，就提示先Get
        if len(source_verts_positions) == 0:
            self.report({'WARNING'}, "请先点击 [Get] 获取源点信息")
            return {'CANCELLED'}

        # 目标(选中)顶点
        selected_verts = [v for v in bm.verts if v.select]
        if len(selected_verts) == 0:
            self.report({'WARNING'}, "请选中一些顶点或UV")
            return {'CANCELLED'}

        # 处理每个选中的顶点(或UV)
        tolerance_val = props.tolerance if props.transfer_mode == 'VERTEX' else props.tolerance_uv
        threshold_val = props.threshold_vertex if props.transfer_mode == 'VERTEX' else props.threshold_uv
        move_mode = props.move_mode

        # Search or Move// 根据 UV 或 顶点，获取移动阈值
        # 根据 UV 或 顶点，获取公差
        if self.mode == 1:
            range=props.threshold
            gosa=props.tolerance
            self.report({'INFO'}, "执行搜索(Search) - 不会实际移动，仅做匹配演示。")
        else:
            range = props.threshold_uv
            gosa = props.tolerance_uv
            self.report({'INFO'}, "执行移动(Move) - 将匹配到的点移动。")
        worldTrue=props.world_space
        # 获取当前选择并尝试转换成   选中列表
        transformList=[]
        for o in bpy.context.selected_objects:
            if o.type == 'MESH':
                transformList.append(o)

        for v in selected_verts:
            # 先拿到当前点的坐标(顶点或UV)
            if props.transfer_mode == 'VERTEX':
                if props.use_world_space:
                    vpos = obj.matrix_world @ v.co
                else:
                    vpos = v.co.copy()
            else:
                # UV模式
                uv_layer = bm.loops.layers.uv.active
                if not uv_layer or not v.link_loops:
                    continue
                vpos_2d = v.link_loops[0][uv_layer].uv.copy()
                # 统一用 3D Vector, z=0
                vpos = Vector((vpos_2d.x, vpos_2d.y, 0))

            # 根据move_mode来查找可能匹配的源位置
            matched_source_pos = None

            # 1) 距离模式
            if move_mode == 'DISTANCE':
                # 在所有源点中找一个最合适的(或最近的)pos
                pass
                # for s_pos in source_verts_positions:
                #     if val_much(vpos, s_pos, tolerance_val):
                #         matched_source_pos = s_pos
                #         break

            # 2) 顶点ID模式
            elif move_mode == 'VERTEXID':
                # 直接比对索引；如果找到相同的 index, 就用对应的源位置
                # v.index => 目标的index
                # source_verts_indices[i] => 源的index
                if v.index in source_verts_indices:
                    idx = source_verts_indices.index(v.index)
                    matched_source_pos = source_verts_positions[idx]

            # 3) 拓扑模式(TOPOLOGY)
            # 由于Blender不一样，需要更复杂拓扑算法。此处仅简单演示
            elif move_mode == 'TOPOLOGY':
                # 简略做法：假设对称网格顶点数量相同 + 索引大体对应
                if v.index < len(source_verts_positions):
                    # 直接用对应下标
                    matched_source_pos = source_verts_positions[v.index]

            # 若找到匹配，则根据mode决定是否要Move
            if matched_source_pos is not None:
                if self.mode == 2:
                    # Move
                    if props.transfer_mode == 'VERTEX':
                        # 顶点
                        if props.use_world_space:
                            # 先把 matched_source_pos 转回局部坐标(若需要)
                            local_pos = obj.matrix_world.inverted() @ matched_source_pos
                            v.co = local_pos
                        else:
                            # 直接设
                            v.co = matched_source_pos
                    else:
                        # UV
                        uv_layer = bm.loops.layers.uv.active
                        if uv_layer and v.link_loops:
                            # matched_source_pos 是 3D Vector
                            new_uv_x = matched_source_pos.x
                            new_uv_y = matched_source_pos.y
                            for loop in v.link_loops:
                                loop[uv_layer].uv = (new_uv_x, new_uv_y)
                else:
                    # mode == 1: Search, 不移动
                    pass
            else:
                # 没找到匹配(距离或ID或拓扑都不满足)，可做一些标记
                pass

        bmesh.update_edit_mesh(obj.data)
        return {'FINISHED'}
class ARITRANSFERPOSITION_OT_Transfer(Operator):
    bl_idname = "object.ari_transfer_position"
    bl_label = "Ari传输位置"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.ari_transfer_position_settings
        obj = context.active_object

        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "请选中一个网格对象")
            return {'CANCELLED'}

        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)

        if bm is None:
            self.report({'ERROR'}, "请进入编辑模式")
            return {'CANCELLED'}

        selected_verts = [v for v in bm.verts if v.select]
        if not selected_verts:
            self.report({'ERROR'}, "请选中顶点或UV")
            return {'CANCELLED'}

        # 获取传输模式
        transfer_mode = settings.transfer_mode

        # 获取源顶点或UV位置
        source_positions = []
        if transfer_mode == 'VERTEX':
            source_positions = [v.co.copy() for v in selected_verts]
        elif transfer_mode == 'UV':
            uv_layer = bm.loops.layers.uv.active
            if uv_layer is None:
                self.report({'ERROR'}, "没有UV层")
                return {'CANCELLED'}
            source_positions = [v[uv_layer].uv.copy() for v in bm.loops for v in selected_verts]

        # 遍历所有顶点或UV，寻找匹配并传输位置
        for v in bm.verts:
            if not v.select:
                continue
            if transfer_mode == 'VERTEX':
                target_pos = v.co.copy()
                for src_pos in source_positions:
                    distance = (target_pos - src_pos).length
                    if distance <= settings.tolerance:
                        if settings.world_space:
                            v.co = src_pos
                        else:
                            v.co -= obj.matrix_world.translation
                            v.co = src_pos
                        break
            elif transfer_mode == 'UV':
                uv_layer = bm.loops.layers.uv.active
                if uv_layer is None:
                    continue
                for loop in v.link_loops:
                    target_uv = loop[uv_layer].uv.copy()
                    for src_uv in source_positions:
                        distance = (target_uv - src_uv).length
                        if distance <= settings.tolerance_uv:
                            loop[uv_layer].uv = src_uv
                            break

        bmesh.update_edit_mesh(mesh)
        self.report({'INFO'}, "传输完成")
        return {'FINISHED'}

