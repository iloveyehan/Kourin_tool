import subprocess
import sys
import typing
from pathlib import Path


# from .operators import origin
import bpy
from bpy_types import Operator


from .utils.registration import register_keymaps, unregister_keymaps,is_pyside6_installed
# from .panels.AddonPanels import AriEdgeSmoothSettings,AriTransferPositionSettings
from .reg import keys
from .update import KourinCheckUpdateOperator
from . import zh_CN
# Add-on info
bl_info = {
    "name": "Kourin_tool",
    "author": "Cupcko[649730016@qq.com]",
    "blender": (3, 5, 0),
    "version": (1, 1, 4),
    "description": "This is a template for building addons",
    "warning": "",
    "doc_url": "[documentation url]",
    "tracker_url": "[contact email]",
    "support": "COMMUNITY",
    "category": "3D View"
}

# 插件主类
class MyAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__
    def draw(self, context):
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
class InstallPysideOperator(Operator):
    """Install Pillow Library"""
    bl_idname = "kourin.install_pyside6"
    bl_label = "Install Pyside6"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            import pip
            # 安装Pyside6库
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyside6"])
            # subprocess.check_call([sys.executable, "-m", "pip", "install", "PyQt6"])
            self.report({'INFO'}, "Pyside6 installed successfully.")
        except Exception as e:
            self.report({'ERROR'}, str(e))
        return {'FINISHED'}
_addon_properties = {
# bpy.types.Scene: {
        # "ari_edge_smooth_settings": bpy.props.PointerProperty(type=AriEdgeSmoothSettings),
        # 'ari_transfer_position_settings':bpy.props.PointerProperty(type=AriTransferPositionSettings)
# },
}

# support adding properties in a declarative way
def add_properties(property_dict: dict[typing.Any, dict[str, typing.Any]]):
    for cls, properties in property_dict.items():
        for name, prop in properties.items():
            setattr(cls, name, prop)


# support removing properties in a declarative way
def remove_properties(property_dict: dict[typing.Any, dict[str, typing.Any]]):
    for cls, properties in property_dict.items():
        for name in properties.keys():
            if hasattr(cls, name):
                delattr(cls, name)
# You may declare properties like following, framework will automatically add and remove them.
# Do not define your own property group class in the __init__.py file. Define it in a separate file and import it here.
# 注意不要在__init__.py文件中自定义PropertyGroup类。请在单独的文件中定义它们并在此处导入。
# _addon_properties = {
#     bpy.types.Scene: {
#         "property_name": bpy.props.StringProperty(name="property_name"),
#     },
# }

# Best practice: Please do not define Blender classes in the __init__.py file.
# Define them in separate files and import them here. This is because the __init__.py file would be copied during
# addon packaging, and defining Blender classes in the __init__.py file may cause unexpected problems.
# 建议不要在__init__.py文件中定义Blender相关的类。请在单独的文件中定义它们并在此处导入它们。
# __init__.py文件在代码打包时会被复制，在__init__.py文件中定义Blender相关的类可能会导致意外的问题。
#中文翻译
class TranslationHelper():
    def __init__(self, name: str, data: dict, lang='zh_CN'):
        self.name = name
        self.translations_dict = dict()

        for src, src_trans in data.items():
            key = ("Operator", src)
            self.translations_dict.setdefault(lang, {})[key] = src_trans
            key = ("*", src)
            self.translations_dict.setdefault(lang, {})[key] = src_trans

    def register(self):
        try:
            bpy.app.translations.register(self.name, self.translations_dict)
        except(ValueError):
            pass

    def unregister(self):
        bpy.app.translations.unregister(self.name)
def reg_all():
    ...
def unreg_all():
    ...
Kourin_tool_zh_CN = TranslationHelper('Kourin_tool_zh_CN', zh_CN.data)
Kourin_tool_zh_HANS = TranslationHelper('Kourin_tool_zh_HANS', zh_CN.data, lang='zh_HANS')
if is_pyside6_installed():
    # print(1,is_pyside6_installed())
    from .operators.origin import reg_origin,unreg_origin
    from .operators.transfer import reg_trans,unreg_trans
    from .operators.color_selector import reg_color_selector,unreg_color_selector
    from .operators.vrc_bone_ops import reg_vrc_bone_ops,unreg_vrc_bone_ops
    # from .operators.tool_vert import reg_tool_vert,unreg_tool_vert

    from .preference.AddonPreferences import reg_pref,unreg_pref
    from .panels.main_button import main_button_register,main_button_unregister
    from .ui.ui_vrc_panel import reg_ui_vrc_panel,unreg_ui_vrc_panel
    from .ui.ui_sculpt import reg_sculpt_menu,unreg_sculpt_menu
    from .operators.draw import reg_draw_info,unreg_draw_info
    from .operators.vertex_group import reg_vrc_vg_ops,unreg_vrc_vg_ops
    from .operators.shapkey import reg_vrc_sk_ops,unreg_vrc_sk_ops
    def reg_all():

        reg_vrc_vg_ops()
        reg_vrc_sk_ops()
        reg_vrc_bone_ops()
        reg_draw_info()
        reg_origin()
        main_button_register()
        reg_trans()
        reg_color_selector()

        reg_pref()
        reg_ui_vrc_panel()
        reg_sculpt_menu()
        add_properties(_addon_properties)
    def unreg_all():
        unreg_vrc_vg_ops()
        unreg_vrc_sk_ops()
        main_button_unregister()
        remove_properties(_addon_properties)
        unreg_ui_vrc_panel()
        unreg_sculpt_menu()
        unreg_origin()
        unreg_trans()
        unreg_vrc_bone_ops()
        unreg_color_selector()

        unreg_pref()
        unreg_draw_info()
else:
    # print(2)
    def reg_all():
        pass
    def unreg_all():
        pass
from .preference.AddonPreferences import reg_pref,unreg_pref
def register():
    bpy.utils.register_class(InstallPysideOperator)
    bpy.utils.register_class(KourinCheckUpdateOperator)
    # bpy.utils.register_class(MyAddonPreferences)
    
    # main_button_register()
    #翻译
    if bpy.app.version < (4, 0, 0):
        Kourin_tool_zh_CN.register()
    else:
        Kourin_tool_zh_CN.register()
        Kourin_tool_zh_HANS.register()
    reg_all()
    # reg_origin()
    # reg_trans()
    # reg_color_selector()
    # reg_tool_vert()
    # reg_menu()
    # reg_pref()
    # print("registering")
    # Register classes

    # add_properties(_addon_properties)


    # print("{} addon is installed.".format(bl_info["name"]))
    global keymaps
    # print([keys[v] for v in keys])
    keymaps = register_keymaps([keys[v] for v in keys])

def unregister():
    # main_button_unregister()
    bpy.utils.unregister_class(InstallPysideOperator)
    bpy.utils.unregister_class(KourinCheckUpdateOperator)
    #翻译
    if bpy.app.version < (4, 0, 0):
        Kourin_tool_zh_CN.unregister()
    else:
        Kourin_tool_zh_CN.unregister()
        Kourin_tool_zh_HANS.unregister()
    unreg_all()
    # Internationalization
    # unRegister classes
    # remove_properties(_addon_properties)
    # unreg_origin()
    # unreg_trans()
    # unreg_color_selector()
    # unreg_tool_vert()
    # unreg_menu()
    # unreg_pref()
    # print("{} addon is uninstalled.".format(bl_info["name"]))
    global keymaps
    if keymaps:
        unregister_keymaps(keymaps)