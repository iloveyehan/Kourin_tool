from pathlib import Path

import bpy
from bpy.props import EnumProperty, FloatProperty, IntProperty, BoolProperty

# from ..operators.cursor import M4CursorToSelected,M4SelectedToCursor,M4CursorToOrigin
from ..utils.file import get_addon

from bpy.app.translations import pgettext as _p
from ..common.class_loader.auto_load import ClassAutoloader
m=ClassAutoloader(Path(__file__))
def reg_menu():
    m.init()
    m.register()
def unreg_menu():
    m.unregister()
class AriEdgeSmoothSettings(bpy.types.PropertyGroup):
    edge_strength: bpy.props.IntProperty(
        name="Power",
        description="控制边缘平滑度",
        default=5,
        min=3,
        max=100
    )
    repeat_count: bpy.props.IntProperty(
        name="Repeat",
        description="操作重复次数",
        default=1,
        min=1,
        max=100
    )
    uniform_smooth: bpy.props.BoolProperty(
        name="Uniform",
        description="应用均匀平滑",
        default=True
    )
    mode: bpy.props.EnumProperty(
        name="Mode",
        description="选择边选择模式",
        items=[
            ('CONTIGUOUS', "Contiguous", "选择连续边"),
            ('EDGE_RING', "Edge Ring", "选择环形边"),
        ],
        default='CONTIGUOUS'
    )

class ARIEDGESMOOTH_PT_Panel(bpy.types.Panel):
    bl_label = "Ari Edge Smooth Options"
    bl_idname = "ARIEDGESMOOTH_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'AriEdgeSmooth'

    def draw(self, context):
        layout = self.layout
        settings = context.scene.ari_edge_smooth_settings

        layout.prop(settings, "edge_strength")
        layout.prop(settings, "repeat_count")
        layout.prop(settings, "uniform_smooth")
        layout.prop(settings, "mode")

        row = layout.row()
        row.operator("ari_edge_smooth.select_edges", text="Select Edges")
        row = layout.row()
        row.operator("ari_edge_smooth.reset", text="Reset")
        row.operator("cupcko_edgesmooth.apply", text="Apply")
class AriTransferPositionSettings(bpy.types.PropertyGroup):
    transfer_mode: EnumProperty(
        name="传输模式",
        description="选择传输顶点位置或UV位置",
        items=[
            ('VERTEX', "顶点", ""),
            ('UV', "UV", ""),
        ],
        default='VERTEX'
    )
    tolerance: FloatProperty(
        name="搜索容差",
        description="顶点位置匹配的容差",
        default=0.001,
        min=0.0,
        max=0.01,
        step=0.0001,
    )
    tolerance_uv: FloatProperty(
        name="UV搜索容差",
        description="UV位置匹配的容差",
        default=0.0001,
        min=0.0,
        max=0.01,
        step=0.0001,
    )
    move_mode: EnumProperty(
        name="移动模式",
        description="选择移动模式",
        items=[
            ('DISTANCE', "距离", ""),
            ('TOPOLOGY', "拓扑", ""),
            ('VERTEXID', "顶点ID", ""),
        ],
        default='DISTANCE'
    )
    iterations: IntProperty(
        name="迭代次数",
        description="迭代次数",
        default=50,
        min=1,
        max=100,
    )
    world_space: BoolProperty(
        name="世界空间",
        description="在世界空间中移动顶点",
        default=False,
    )
    threshold: FloatProperty(
        name="移动阈值",
        description="移动顶点的阈值",
        default=0.010,
        min=0.001,
        max=1.0,
        step=0.001,
    )
    threshold_uv: FloatProperty(
        name="UV移动阈值",
        description="移动UV的阈值",
        default=0.010,
        min=0.0001,
        max=1.0,
        step=0.001,
    )
    min_percentage: FloatProperty(
        name="最小百分比",
        description="最小距离百分比",
        default=10.0,
        min=0.0,
        max=100.0,
        step=1.0,
    )

class ARITRANSFERPOSITION_PT_Panel(bpy.types.Panel):
    bl_label = "Ari传输位置"
    bl_idname = "OBJECT_PT_ari_transfer_position"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'AriTools'

    def draw(self, context):
        layout = self.layout
        settings = context.scene.ari_transfer_position_settings

        layout.prop(settings, "transfer_mode")
        if settings.transfer_mode == 'VERTEX':
            layout.prop(settings, "tolerance")
        elif settings.transfer_mode == 'UV':
            layout.prop(settings, "tolerance_uv")

        layout.prop(settings, "move_mode")
        layout.prop(settings, "iterations")
        layout.prop(settings, "world_space")
        if settings.transfer_mode == 'VERTEX':
            layout.prop(settings, "threshold")
        elif settings.transfer_mode == 'UV':
            layout.prop(settings, "threshold_uv")
        layout.prop(settings, "min_percentage")

        layout.operator("object.ari_transfer_position", text="传输位置")
