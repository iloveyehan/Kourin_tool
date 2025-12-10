import copy
import ctypes
from ctypes import wintypes
import traceback
# from OpenGL import GL as gl
import OpenImageIO as oiio

import numpy as np
# import gpu
import gpu
import typing
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, StringProperty

import sys
from pathlib import Path
import bpy
import inspect
import pkgutil # 导入 pkgutil 用于遍历子包
import importlib 

from types import ModuleType

from .imgui_setup import toast_drawer

from .operators.main_button import source_obj
# from . import save
# from .extern.robust_weight_transfer import Robust_register,Robust_unregister


# --- 自动注册器列表 ---
CLASSES = []
# --- 核心自动注册函数 (最终修正版) ---
def get_classes_to_register(module: ModuleType):
    """
    遍历给定模块，收集所有继承自 bpy.types 的类（带详细调试）。
    """
    # print(f"\n--- 正在检查模块: {module.__name__} ---")
    
    for name, obj in inspect.getmembers(module):
        # 1. 必须是类
        if not inspect.isclass(obj):
            continue
            
        # 2. 必须是在这个模块中定义的（而不是导入的）
        if obj.__module__ != module.__name__:
            continue
            
        # print(f"  正在检查类: '{name}'")

        # --- 详细的基类检查 ---
        if not hasattr(obj, "__bases__"):
            # print(f"    [跳过] '{name}': 没有 __bases__ 属性。")
            continue
            
        is_blender_class = False
        try:
            # 遍历所有基类
            for base in obj.__bases__:
                # 获取基类的模块名
                base_module_name = getattr(base, "__module__", "N/A")
                
                # print(f"      -> 检查基类: {base.__name__} (来自模块: '{base_module_name}')")
                
                # 🌟 🌟 🌟 
                # 🌟 关键修复：Blender 核心类型来自 'bpy_types' 模块
                # 🌟 🌟 🌟 
                if base_module_name in ['bpy_types','bpy.types','_bpy_types']:
                    # print(f"      [匹配] '{base.__name__}' 是一个 bpy.types 核心类。")
                    is_blender_class = True
                    break # 找到匹配，停止检查
                
        except Exception as e:
            # print(f"    [错误] 检查 '{name}' 的基类时出错: {e}")
            continue
        # --- 检查结束 ---

        # 4. 检查结果
        if is_blender_class:
            if obj not in CLASSES:
                # print(f"    [√ 成功] 将 '{name}' 添加到注册列表。")
                CLASSES.append(obj)
        else:
            pass
            # print(f"    [X 失败] '{name}' 未能识别为 bpy.types 的子类。")

    # print(f"--- 检查完毕: {module.__name__} | 累计找到: {len(CLASSES)} ---")

from .operators.base_ops import BaseDrawCall


# current_folder=Path(__file__).parent.absolute()
# sys.path.append(str(current_folder))
# from .imgui_setup.hook_ime import hook_ime,restore_wndproc
from .imgui_setup.shapekey import shapkey_widget
from .imgui_setup.check import widget_check
from .imgui_setup.vertex_group import vertex_group_widget
from .imgui_setup.selectable_input import selectable_input
from .imgui_setup.preprocessing.pre_widget import pre_widget
from .widget import get_wheeL_tri, color_bar, colorpicker, color_palette,picker_switch_button
from .utils.utils import get_brush_color_based_on_mode,get_prefs,im_pow
from mathutils import Vector
from .pref import Imgui_Color_Picker_Preferences
import time
import bpy
import sys
from imgui_bundle import imgui
from imgui_bundle import ImVec2, ImVec4
from .imgui_setup.imgui_global import GlobalImgui
from .imgui_setup.mirror_reminder import open_mirror_tip, open_tip

bl_info = {
    "name": "Kourin_tool",
    "author": "cupcko",
    "version": (1, 3, 7),
    "blender": (4, 0, 0),
    "location": "3D View,Image Editor",
    "description": "123",
    "category": "3D View"
}


class Imgui_Window_Imgui(bpy.types.Operator, BaseDrawCall):
    bl_idname = "imgui.window"
    bl_label = "color picker"
    bl_options = {'REGISTER','UNDO'}

    @classmethod
    def poll(cls, context):
        return 1

    def draw(self, context: bpy.types.Context):
        # 严格的区域验证 - 防止跨区域交互
        if context.area != self.area or context.region != self.region:
            return
        
        # 如果被暂停，跳过大部分绘制（只保留最小化框架）
        if self._is_suspended:
            # 每30帧绘制一次简化版本，保持窗口存在
            self._suspend_frame_skip += 1
            if self._suspend_frame_skip < 30:
                return
            self._suspend_frame_skip = 0
            
            # 绘制简化版本（只显示标题栏）
            _main_window, _main_x = imgui.begin("VRC窗口", self.main_window[0])
            imgui.text_disabled("(暂停中...)")
            imgui.end()
            
            if not _main_x:
                self.show_window_imgui = False
            return
        
        self.cover = False
        self.cover_style_editor = False
        
        _main_window, _main_x = imgui.begin("VRC窗口", self.main_window[0])

        imgui.set_next_item_open(True, cond=imgui.Cond_.once)
        pre_widget(self)
        vertex_group_widget(self)
        shapkey_widget(self)
        widget_check(self)
        imgui.separator()
        
        # imgui.show_demo_window()
        # 
        if imgui.button("打开新窗口"):
            GlobalImgui.get().show_new_window[0] = True
            
        if imgui.button("打开镜像提醒"):
            GlobalImgui.get().show_mirror_reminder_window = True
            GlobalImgui.get().mirror_reminder_window_open_time = time.time()
        
        self.track_any_cover()
        
        # 新窗口渲染
        if hasattr(GlobalImgui.get(), 'show_new_window') and GlobalImgui.get().show_new_window[0]:
            opened, _x = imgui.begin(
                "新窗口", 
                GlobalImgui.get().show_new_window[0],
                imgui.WindowFlags_.no_nav | imgui.WindowFlags_.no_focus_on_appearing
            )
            
            imgui.text("这是一个新窗口！")
            imgui.text(f"item_spacing:{imgui.get_style().item_spacing}")
            imgui.text(f"item_inner_spacing:{imgui.get_style().item_inner_spacing}")
            imgui.text(f"window_padding:{imgui.get_style().window_padding}")
            
            # 颜色编辑器
            _, GlobalImgui.get().title_bg_color = imgui.color_edit4("窗口标题##title_bg_color", GlobalImgui.get().title_bg_color)
            _, GlobalImgui.get().title_bg_active_color = imgui.color_edit4("窗口标题激活##title_bg_active_color", GlobalImgui.get().title_bg_active_color)
            _, GlobalImgui.get().title_bg_collapsed_color = imgui.color_edit4("窗口折叠##title_bg_collapsed_color", GlobalImgui.get().title_bg_collapsed_color)
            _, GlobalImgui.get().window_bg_color = imgui.color_edit4("窗口背景##window_bg_color", GlobalImgui.get().window_bg_color)
            _, GlobalImgui.get().frame_bg_color = imgui.color_edit4("frame##frame_bg_color", GlobalImgui.get().frame_bg_color)
            _, GlobalImgui.get().button_color = imgui.color_edit4("按钮##button_color", GlobalImgui.get().button_color)
            _, GlobalImgui.get().button_active_color = imgui.color_edit4("按钮激活##button_active_color", GlobalImgui.get().button_active_color)
            _, GlobalImgui.get().button_hovered_color = imgui.color_edit4("按钮悬浮##button_hovered_color", GlobalImgui.get().button_hovered_color)
            _, GlobalImgui.get().header_color = imgui.color_edit4("子标题##header_color", GlobalImgui.get().header_color)
            _, GlobalImgui.get().child_bg = imgui.color_edit4("子集##child_bg", GlobalImgui.get().child_bg)
            
            if imgui.button("关闭"):
                GlobalImgui.get().show_new_window[0] = False
                
            self.track_any_cover_style_editor()
            imgui.end()
            
            if not opened or not _x:
                GlobalImgui.get().show_new_window[0] = False
                
        open_mirror_tip('镜像没开')
        # from .imgui_setup.tip import render_toasts
        # render_toasts()
        imgui.end()

        if not _main_x:
            self.show_window_imgui = False

    def invoke(self, context, event):
        # 不清空列表，支持多个 ImGui UI 同时存在
        if not hasattr(GlobalImgui.get(), 'imgui_vrc_instance'):
            GlobalImgui.get().imgui_vrc_instance = []
        GlobalImgui.get().imgui_vrc_instance.append(self)
        
        self.should_close = False
        self.cover = False
        self.ops_name='main'
        self.cover_style_editor = False
        self.show_mirror_reminder_window = False
        self.mirror_reminder_window_open_time = None
        self.show_window_imgui = True
        self.area = context.area
        self.region = context.region
        self.region_capture = None
        
        # 性能优化缓存
        self._last_mouse_region = None
        self._last_mouse_area = None
        self._redraw_counter = 0
        self._imgui_mouse_reset = False
        self._is_suspended = False  # 暂停标志
        self._last_active_time = time.time()  # 最后活跃时间
        self._suspend_frame_skip = 0  # 暂停时的跳帧计数
        
        self.init_imgui(context)
        
        GlobalImgui.get().main_window=True
        self.load_icon()
        context.window_manager.modal_handler_add(self)


        self._interval: float = 0.2  # 默认 0.5 秒执行一次
        self._start_time = time.perf_counter()
        self._last_tick = self._start_time
        return {'RUNNING_MODAL'}
    

    def modal(self, context, event):
        # 提前退出检查
        if self.should_close or not self.show_window_imgui or not GlobalImgui.get().debug:
            self.call_shutdown_imgui()
            self.refresh()
            return {'FINISHED'}
        
        # 检查并更新暂停状态
        self.update_suspend_state()
        # 如果被暂停，大幅降低处理频率
        if self._is_suspended:
            # 每10帧处理一次，检查是否需要恢复
            if self._redraw_counter % 10 == 0:
                if context.area == self.area:
                    context.area.tag_redraw()
            self._redraw_counter += 1
            return {'PASS_THROUGH'}  # 暂停时透传所有事件
        
        # 优化的区域查找
        region, current_area, mx, my, is_in_operator_region = self.find_mouse_region(event)
        
        # 没找到任何区域，透传
        if region is None:
            self.reset_imgui_mouse()
            return {'PASS_THROUGH'}
        
        # 【关键】鼠标不在操作符绑定的区域内
        if not is_in_operator_region:
            # 重置 ImGui 鼠标状态，避免错误的悬停/点击
            self.reset_imgui_mouse()
            return {'PASS_THROUGH'}
        
        #刷新font
        now = time.perf_counter()

        # 到间隔了 → 执行你的逻辑
        if now - self._last_tick >= self._interval:
            self._last_tick = now
            from .render import Renderer
            self._font_tex = Renderer.instance.refresh_font_texture_ex()

        
        # 鼠标在正确的区域内，重置标志
        self._imgui_mouse_reset = False
        
        # 更新坐标
        self.mpos = (mx, my)
        
        # 智能重绘：只在必要时重绘
        self._redraw_counter += 1
        needs_redraw = (
            event.type not in {'TIMER', 'MOUSEMOVE'} or  # 非移动事件总是重绘
            self.cover or  # 鼠标在 ImGui 上时重绘
            self._redraw_counter % 2 == 0  # 其他情况限流
        )
        
        if needs_redraw and context.area == self.area:
            context.area.tag_redraw()
        
        # 边界检查（双重保险）
        if mx < 0 or mx > region.width or my < 0 or my > region.height:
            self.reset_imgui_mouse()
            return {'PASS_THROUGH'}
        
        # 重要事件优先透传
        if event.type in {'MIDDLEMOUSE', 'TAB'}:
            return {'PASS_THROUGH'}
        
        # 雕刻 权重模式特殊处理
        if context.mode in ['SCULPT','PAINT_WEIGHT']:
            # 在雕刻模式下，如果不在 ImGui 窗口上，透传所有笔刷相关事件
            if not self.cover and event.type in {
                'LEFTMOUSE', 'RIGHTMOUSE', 
                'WHEELUPMOUSE', 'WHEELDOWNMOUSE',
                'F', '[', ']'  # 常用的雕刻快捷键
            }:
                return {'PASS_THROUGH'}
        
        # 右键处理（原有逻辑保持）
        if event.type == 'RIGHTMOUSE':
            io = imgui.get_io()
            if self.cover and event.value == 'PRESS':
                io.add_mouse_button_event(1, True)
                return {'RUNNING_MODAL'}
            else:
                io.add_mouse_button_event(1, False)
                return {'PASS_THROUGH'}

        
        # 轮询事件
        self.poll_mouse(context, event)
        self.poll_events(context, event)
        
        # 焦点决策：只有在 ImGui 窗口上才拦截事件
        return {'RUNNING_MODAL' if (self.cover or self.cover_style_editor) else 'PASS_THROUGH'}

    def load_icon(self):
        """批量加载图标"""
        icons = {
            'btn_set_viewport_display_random': "material.png",
            'btn_show_axes': "axis_front.png",
            'btn_clean_skeleton': "brush_data.png",
            'btn_make_skeleton': "armature_data.png",
            'btn_show_bonename': "group_bone.png",
            'btn_show_in_front': "transform_origins.png",
            'btn_pose_to_reset': "checkmark.png",
            'btn_add_sk': "add.png",
            'btn_rm_sk': "remove.png",
            'btn_sk_special': "downarrow_hlt.png",
            'btn_mv_sk_up': "tria_up.png",
            'btn_mv_sk_down': "tria_down.png",
            'btn_clear_all_sk_value': "panel_close.png",
            'btn_solo_active_sk': "solo_off.png",
            'btn_sk_edit_mode': "editmode_hlt.png"
        }
        for attr_name, icon_file in icons.items():
            setattr(self, attr_name, self.load_icon_texture(icon_file))
    
    def refresh(self):
        """只刷新必要的区域"""
        for area in bpy.context.screen.areas:
            if area.type in ['VIEW_3D', 'IMAGE_EDITOR']:
                area.tag_redraw()
    
    def find_mouse_region(self, event):
        """
        优化的鼠标区域查找
        返回: (region, area, mx, my, is_in_operator_region)
        """
        gx, gy = event.mouse_x, event.mouse_y
        
        # 优先检查操作符所在的区域（最常见的情况）
        if self.area and self.region:
            r = self.region
            if (gx >= r.x and gx <= r.x + r.width and 
                gy >= r.y and gy <= r.y + r.height):
                mx = gx - r.x
                my = gy - r.y
                return r, self.area, mx, my, True
        
        # 再检查上次缓存的区域（鼠标在其他区域的情况）
        if self._last_mouse_region and self._last_mouse_area:
            r = self._last_mouse_region
            if (gx >= r.x and gx <= r.x + r.width and 
                gy >= r.y and gy <= r.y + r.height):
                mx = gx - r.x
                my = gy - r.y
                return r, self._last_mouse_area, mx, my, False
        
        # 最后才遍历所有区域
        for area in bpy.context.window.screen.areas:
            for r in area.regions:
                if (gx >= r.x and gx <= r.x + r.width and 
                    gy >= r.y and gy <= r.y + r.height):
                    self._last_mouse_region = r
                    self._last_mouse_area = area
                    mx = gx - r.x
                    my = gy - r.y
                    return r, area, mx, my, False
        
        return None, None, None, None, False
    
    def reset_imgui_mouse(self):
        """重置 ImGui 鼠标状态"""
        if not self._imgui_mouse_reset:
            try:
                io = imgui.get_io()
                io.add_mouse_pos_event(-1, -1)  # 告诉 ImGui 鼠标离开
                self._imgui_mouse_reset = True
            except Exception:
                pass
    
    def check_should_suspend(self):
        """
        检查是否应该暂停当前 UI
        如果其他 ImGui UI 正在被交互，则暂停自己
        """
        if not hasattr(GlobalImgui.get(), 'imgui_vrc_instance'):
            return False
        
        # 遍历所有 ImGui 实例
        for instance in GlobalImgui.get().imgui_vrc_instance:
            if hasattr(instance, 'ops_name'):
                # print('跳过自己')
                continue  # 跳过自己
                
            if instance == self:
                # print('跳过自己')
                continue  # 跳过自己
            
            # 如果其他实例正在被 hover 或交互
            if hasattr(instance, 'cover') and instance.cover:
                print(self,'其他实例正在被 hover 或交互')
                print(instance)
                return True
            if hasattr(instance, 'cover_style_editor') and instance.cover_style_editor:
                print('cover_style_editor')
                return True
        
        return False
    
    def update_suspend_state(self):
        """更新暂停状态"""
        should_suspend = self.check_should_suspend()
        
        if should_suspend:
            if not self._is_suspended:
                # 进入暂停状态
                self._is_suspended = True
                self._suspend_frame_skip = 0
        else:
            if self._is_suspended:
                # 恢复活跃状态
                self._is_suspended = False
                self._suspend_frame_skip = 0
            self._last_active_time = time.time()
    



    def cancel(self, context):
        print("Operator 被 Blender 取消，执行清理")
        # 从全局列表中移除自己
        if hasattr(GlobalImgui.get(), 'imgui_vrc_instance'):
            try:
                GlobalImgui.get().imgui_vrc_instance.remove(self)
            except ValueError:
                pass
        self.call_shutdown_imgui()
        self.refresh()
        return {'CANCELLED'}



class TranslationHelper():
    def __init__(self, name: str, data: dict, lang='zh_CN'      ):
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
from .prop import ImguiObjectSettingsGroup,ImguiSceneSettingsGroup
_addon_properties = {
bpy.types.Scene: {
        # "ari_edge_smooth_settings": bpy.props.PointerProperty(type=AriEdgeSmoothSettings),
        # 'ari_transfer_position_settings':bpy.props.PointerProperty(type=AriTransferPositionSettings),
    
    'kourin_weight_transfer_settings' : bpy.props.PointerProperty(type=ImguiSceneSettingsGroup),
        
},
bpy.types.Object: {
    'kourin_weight_transfer_settings' : bpy.props.PointerProperty(type=ImguiObjectSettingsGroup),
}
}
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

from . import zh_CN
Colorpickerzh_CN = TranslationHelper('Colorpickerzh_CN', zh_CN.data)
Colorpickerzh_HANS = TranslationHelper('Colorpickerzh_HANS', zh_CN.data, lang='zh_HANS')
from .operators.base_ops import IMGUI_OT_shutdown_all
def vrc_menu(self, context):
    row = self.layout.row(align=True)
    # 打开原来的 ImGui 窗口 operator（保持原样）
    row.operator(Imgui_Window_Imgui.bl_idname, text="VRChat", icon='WINDOW')
    # 右侧小按钮 "X" 关闭 ImGui 窗口
    # emboss=False 让按钮看起来更简洁；如需更显眼可改为 emboss=True 或加 icon='CANCEL'
    row.operator(IMGUI_OT_shutdown_all.bl_idname, text="X", emboss=False)

from .utils.utils import register_keymaps,unregister_keymaps
from .msgbus_handlers import reg_msgbus_handler,unreg_msgbus_handler
# from .operators.bone import reg_vrc_bone_ops,unreg_vrc_bone_ops
from .keymap import keys
def register():
# 获取所有已安装的插件
    # addons = bpy.context.preferences.addons
    # # 遍历并打印插件名称
    # for addon in addons:
    #     print(addon.module)
    # GlobalImgui.get().debug=True
    if bpy.app.version < (4, 0, 0):
        Colorpickerzh_CN.register()
    else:
        Colorpickerzh_CN.register()
        Colorpickerzh_HANS.register()
    toast_drawer.register_draw_handler()
    reg_msgbus_handler()
    # save.register()
    # reg_vrc_bone_ops()
    # reg_vrc_vg_ops()
    # bpy.utils.register_class(Imgui_Color_Picker_Imgui)
    # bpy.utils.register_class(Imgui_Window_Imgui)
    # bpy.utils.register_class(Imgui_Color_Picker_Preferences)
    
    
    CLASSES.clear()
    
    # 2. 递归查找并导入子模块，填充 CLASSES 列表
    addon_module = sys.modules[__name__]
    for importer, modname, ispkg in pkgutil.walk_packages(addon_module.__path__, addon_module.__name__ + '.'):
        try:
            # 动态导入子模块 (例如: a_imgui.operators.bone)
            module = importlib.import_module(modname)
            get_classes_to_register(module)
        except Exception as e:
            # print(f"Warning: 导入模块 {modname} 失败. 跳过. 错误: {e}")
            pass
    # 3. 收集 __init__.py 中定义的类 (例如 Imgui_Window_Imgui)
    get_classes_to_register(addon_module) 
    
    # 4. 批量注册所有找到的类
    print(f"\n[Auto-Register] 最终找到 {len(CLASSES)} 个类，开始注册...")
    if not CLASSES:
        print("[Auto-Register] 警告：没有找到任何要注册的类。请检查您的类定义。")
        
    for cls in CLASSES:
        try:
            bpy.utils.register_class(cls)
            # print(f"  [√ 已注册] {cls.__name__}")
        except Exception as e:
            pass
            # print(f"  [X 注册失败] {cls.__name__}: {e}")



    add_properties(_addon_properties)
    bpy.types.VIEW3D_MT_editor_menus.append(vrc_menu)
    bpy.types.VIEW3D_MT_editor_menus.append(source_obj)
    # Robust_register()
    global keymaps
    keymaps = register_keymaps([keys[v] for v in keys])
def unregister():
    # Robust_unregister()
    bpy.types.VIEW3D_MT_editor_menus.remove(vrc_menu)
    bpy.types.VIEW3D_MT_editor_menus.remove(source_obj)
    remove_properties(_addon_properties)

    GlobalImgui.get().prepare_for_file_reload()
    print('[DEBUG]:注销imgui')
    wm = bpy.context.window_manager
    if 'IMGUI_OT_window' in wm.operators:
        print('IMGUI_OT_window')
        wm.operators['IMGUI_OT_window'].cancel(bpy.context)
    try:
        GlobalImgui.get().shutdown_all_resources() 
        print('[DEBUG]: ImGui 资源清理完毕。')
    except Exception as e:
        print(f'[ERROR]: ImGui 资源清理失败，可能导致崩溃: {e}')
    
    # save.unregister()
    if bpy.app.version < (4, 0, 0):
        Colorpickerzh_CN.unregister()
    else:
        Colorpickerzh_CN.unregister()
        Colorpickerzh_HANS.unregister()
    # 批量注销 (与之前保持一致，反向遍历)
    for cls in reversed(CLASSES):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"Failed to unregister class {cls.__name__}: {e}")
    
    CLASSES.clear()
    # bpy.utils.unregister_class(Imgui_Color_Picker_Imgui)
    # bpy.utils.unregister_class(Imgui_Window_Imgui)
    # bpy.utils.unregister_class(Imgui_Color_Picker_Preferences)
    # unreg_vrc_bone_ops()
    # unreg_vrc_vg_ops()
    unreg_msgbus_handler()
    toast_drawer.unregister_draw_handler()
    global keymaps
    if keymaps:
        unregister_keymaps(keymaps)
