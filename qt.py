import bpy
import ctypes
import os
from ctypes import c_int
import threading
import platform
print(platform.architecture())
# 获取插件目录绝对路径

# 设置 Qt 平台插件路径
# 获取插件目录绝对路径
addon_dir = os.path.dirname(os.path.abspath(__file__))
plugin_path = os.path.join(addon_dir, 'plugins', 'platforms')
        # [!] 设置 Qt 平台插件路径
os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = 'G:/'

print("平台插件路径:", os.path.dirname(__file__))

try:
    mouse_x, mouse_y = 100, 100
    def load_dll():
        color_picker_dll = ctypes.CDLL("G:/colorpicker.dll")
        color_picker_dll.show_color_picker(mouse_x, mouse_y)
    threading.Thread(target=load_dll, daemon=True).start()
except Exception as e:
    pass