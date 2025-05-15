import bpy
def register_keymaps(keylists):
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon

    keymaps = []

    if kc:
        for keylist in keylists:
            for item in keylist:
                keymap = item.get("keymap")
                space_type = item.get("space_type", "EMPTY")

                if keymap:
                    km = kc.keymaps.get(keymap)

                    if not km:
                        km = kc.keymaps.new(name=keymap, space_type=space_type)

                    if km:
                        idname = item.get("idname")
                        type = item.get("type")
                        value = item.get("value")

                        shift = item.get("shift", False)
                        ctrl = item.get("ctrl", False)
                        alt = item.get("alt", False)

                        kmi = km.keymap_items.new(idname, type, value, shift=shift, ctrl=ctrl, alt=alt)

                        if kmi:
                            properties = item.get("properties")

                            if properties:
                                for name, value in properties:
                                    setattr(kmi.properties, name, value)

                            active = item.get("active", True)
                            kmi.active = active

                            keymaps.append((km, kmi))
    else:
        print("WARNING: Keyconfig not availabe, skipping Kourin_tooltools keymaps")

    return keymaps

def unregister_keymaps(keymaps):
    for km, kmi in keymaps:
        km.keymap_items.remove(kmi)
import importlib
import sys
# 检测是否安装了 PySide6
def is_pyside6_installed():
    try:
        import PyQt6
        return True
    except ImportError:
        return False
from pathlib import Path
def get_path():
    # 获取当前文件的绝对路径，并返回其父目录的父目录
    return Path(__file__).resolve().parent.parent
def get_name():
    path = get_path()
    if 'extensions' in str(path):
        # 如果路径中包含 'extensions'，返回 'bl_ext.user_default.' + 父目录名称
        return f'bl_ext.user_default.{path.name}'
    else:
        # 否则返回父目录名称
        return path.name
def get_prefs():
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