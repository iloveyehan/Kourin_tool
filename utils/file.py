import bpy
from pathlib import Path

def get_path():
    # 使用 Path 对象获取当前文件的绝对路径，并获取上级目录

    return Path(__file__).resolve().parent.parent

def get_name():
    print(get_path())
    # 如果路径中包含 'extensions' 文件夹，返回扩展名称
    if 'extensions' in str(get_path()):
        return 'bl_ext.user_default.' + get_path().name
    else:
        # 否则，返回路径的最后一部分（即目录名）
        return get_path().name

def get_prefs():
    print(get_name())
    return bpy.context.preferences.addons[get_name()].preferences
def get_addon(addon, debug=False):
    import addon_utils

    for mod in addon_utils.modules():
        name = mod.bl_info["name"]
        version = mod.bl_info.get("version", None)
        foldername = mod.__name__
        path = mod.__file__
        enabled = addon_utils.check(foldername)[1]

        if name == addon:
            if debug:
                print(name)
                print("  enabled:", enabled)
                print("  folder name:", foldername)
                print("  version:", version)
                print("  path:", path)
                print()

            return enabled, foldername, version, path
    return False, None, None, None