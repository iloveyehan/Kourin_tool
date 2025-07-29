import os
from pathlib import Path

import bpy
from bpy.props import StringProperty, IntProperty, BoolProperty,FloatProperty
from bpy.types import AddonPreferences
from ..utils.registration import is_pyside6_installed
from ..common.class_loader.auto_load import ClassAutoloader

pref=ClassAutoloader(Path(__file__))
def reg_pref():
    pref.init()
    pref.register()
def unreg_pref():
    pref.unregister()

class Kourin_toolTOOLSPreference(AddonPreferences):
    # this must match the add-on name (the folder name of the unzipped file)
    bl_idname = 'Kourin_tool'

    # https://docs.blender.org/api/current/bpy.props.html
    # The name can't be dynamically translated during blender programming running as they are defined
    # when the class is registered, i.e. we need to restart blender for the property name to be correctly translated.
    # filepath: StringProperty(
    #     name="Resource Folder",
    #     default=os.path.join(os.path.expanduser("~"), "Documents", 'Kourin_tool'),
    #     subtype='DIR_PATH',
    # )
    # number: IntProperty(
    #     name="Int Config",
    #     default=2,
    # )
    # boolean: BoolProperty(
    #     name="Boolean Config",
    #     default=False,
    # )
    # modal_hud_scale: FloatProperty(name="HUD Scale", description="Scale of HUD elements", default=1, min=0.1)

    def draw(self, context: bpy.types.Context):
        layout = self.layout
        layout.label(text="Add-on Preferences View")
        # layout.prop(self, "filepath")
        # layout.prop(self, "number")
        # layout.prop(self, "boolean")
        layout = self.layout
        if not is_pyside6_installed():
            # 如果未安装 PySide6，显示提醒面板
            box = layout.box()
            box.label(text="PySide6 未安装", icon="ERROR")
            box.label(text="请安装 PySide6 后并重启以使用此插件的完整功能。")
            box.operator("kourin.install_pyside6", text="安装 PySide6")
        else:
            # 如果已安装 PySide6，显示正常设置
            layout.label(text="PySide6 已安装，插件功能可用。")
        row2 = layout.row(align=True)
        row2.operator("kourin.check_update", text="检查更新")

        