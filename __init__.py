import typing
from pathlib import Path


# from .operators import origin
import bpy


from .utils.registration import register_keymaps, unregister_keymaps
from .panels.AddonPanels import AriEdgeSmoothSettings,AriTransferPositionSettings
from .reg import keys
from . import zh_CN
# Add-on info
bl_info = {
    "name": "Kourin_tool",
    "author": "[You name]",
    "blender": (3, 5, 0),
    "version": (0, 0, 1),
    "description": "This is a template for building addons",
    "warning": "",
    "doc_url": "[documentation url]",
    "tracker_url": "[contact email]",
    "support": "COMMUNITY",
    "category": "3D View"
}

_addon_properties = {
bpy.types.Scene: {
        "ari_edge_smooth_settings": bpy.props.PointerProperty(type=AriEdgeSmoothSettings),
        'ari_transfer_position_settings':bpy.props.PointerProperty(type=AriTransferPositionSettings)
},
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


Kourin_tool_zh_CN = TranslationHelper('Kourin_tool_zh_CN', zh_CN.data)
Kourin_tool_zh_HANS = TranslationHelper('Kourin_tool_zh_HANS', zh_CN.data, lang='zh_HANS')
from .operators.origin import reg_origin,unreg_origin
from .operators.transfer import reg_trans,unreg_trans
from .operators.color_selector import reg_color_selector,unreg_color_selector
# from .operators.tool_vert import reg_tool_vert,unreg_tool_vert
from .panels.AddonPanels import reg_menu,unreg_menu
from .preference.AddonPreferences import reg_pref,unreg_pref
from .panels.main_button import main_button_register,main_button_unregister
def register():
    main_button_register()
    #翻译
    if bpy.app.version < (4, 0, 0):
        Kourin_tool_zh_CN.register()
    else:
        Kourin_tool_zh_CN.register()
        Kourin_tool_zh_HANS.register()
    reg_origin()
    reg_trans()
    reg_color_selector()
    # reg_tool_vert()
    reg_menu()
    reg_pref()
    print("registering")
    # Register classes

    add_properties(_addon_properties)


    print("{} addon is installed.".format(bl_info["name"]))
    global keymaps
    print([keys[v] for v in keys])
    keymaps = register_keymaps([keys[v] for v in keys])

def unregister():
    main_button_unregister()
    #翻译
    if bpy.app.version < (4, 0, 0):
        Kourin_tool_zh_CN.unregister()
    else:
        Kourin_tool_zh_CN.unregister()
        Kourin_tool_zh_HANS.unregister()
    # Internationalization
    # unRegister classes
    remove_properties(_addon_properties)
    unreg_origin()
    unreg_trans()
    unreg_color_selector()
    # unreg_tool_vert()
    unreg_menu()
    unreg_pref()
    print("{} addon is uninstalled.".format(bl_info["name"]))
    global keymaps
    if keymaps:
        unregister_keymaps(keymaps)