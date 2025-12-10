import ctypes
from ctypes import wintypes
import sys
import time
import traceback
import bpy
from imgui_bundle import imgui,ImVec2, ImVec4
from pathlib import Path
from ..render import Renderer as BlenderImguiRenderer
from .widget_rewriting import ImageButton, TextButton,ImguiWindowManager
class GlobalImgui:
    """
    重构说明：
    - 每个 region (region_id) 仅维护一个 Blender draw handler。
    - 每个 region 内维护 callbacks 字典 {cb_id: (callback, user_data)}。
    - handler_add 返回 cb_id；handler_remove(cb_id) 只移除对应回调（若回调为空则移除 draw handler）。
    - 提供安全的 draw handler 创建/移除，避免 nullptr handler 的异常。
    """

    _instance = None

    def __init__(self):
        self.imgui_vrc_instance = []
        #子窗口管理器
        self.windows = {}  # { "window_id": { "open": [bool], "content": [...] } }
        # 基础状态
        self.debug = True
        self.imgui_context = None
        self.imgui_backend = None
        self.surface_deform_name='shinano'

        self._regions = {}

        # 全局回调 id 自增
        self._next_cb_id = 1

        # 输入/剪贴板/字体等（保留你的原属性名以兼容其它代码）
        self.ctrl_c = False
        self.ctrl_x = False
        self.ctrl_v = False
        self.ctrl_a = False
        self.clipboard = ''
        self.text_input_buf = ''
        self.loaded_font = None

        # 窗口/UI 状态等（保持原属性）
        self.show_new_window = [False]
        self.show_mirror_reminder_window = False
        self.mirror_reminder_window_open_time = None

        # widget 实例保留
        self.btn_image = ImageButton()
        self.btn_text= TextButton()
        self.window_mgr = ImguiWindowManager(self)
        # 样式/按钮配置（保留）
        #预处理
      

        # 镜像顶点组等（保留）
        self.vg_left = False
        self.vg_right = False
        self.vg_middle = False
        self.vg_mul = False
        self.vg_select = False
        self.last_side = ''
        self.vg_mirror_search=False
        self.last_mesh_obj=None
        #同步集合
        self.obj_sync_col={}
        self.obj_sync_col_index={}
        self.obj_change_sk=False
        #  if obj.as_pointer() in gp.obj_sync_col_index:
        #     idx=gp.obj_sync_col_index[obj.as_pointer()]
        #顶点权重数检测
        self._cached_obj_name = None
        self._cached_indices = []
        self._cached_positions = []
        self._cached_over_count = 0
        self.threshold = 4
        self.overinfluence_point_size = 6
        self._draw_handle=None
        # 颜色配置
        self.set_color()

    def prepare_for_file_reload(self):
        """
        在 Blender 开始加载新文件前调用：优雅地停止/标记所有运行中的 UI、移除 draw handlers、
        清理对 Blender RNA 对象的引用，保留可重建的 Python 状态。
        """
        # 1) 标记任何运行中窗口应当关闭（用 try/except 安全访问）
        try:
            # 如果 imgui_vrc_instance 存在且含 RNA，请保护访问
            for i, inst in enumerate(list(getattr(self, "imgui_vrc_instance", []))):
                try:
                    inst.should_close = True
                except ReferenceError:
                    # 已被 Blender 删除
                    pass
                except Exception:
                    pass
        except Exception:
            pass

        # 2) 移除 Blender draw handlers（由我们管理的 regions）
        try:
            self.shutdown_imgui()
        except Exception:
            pass

        # 3) 清理对 RNA 的直接引用（只保留 Python 原始数据）
        try:
            self.imgui_vrc_instance = []
        except Exception:
            self.imgui_vrc_instance = []

    def reinit_after_file_load(self):
        """
        在 Blender 完成加载后调用：重建 imgui context / renderer / fonts（按需）。
        这个函数要保证幂等（可多次安全调用）。
        """
        # 先确保我们有一个 clean 状态
        try:
            if getattr(self, "imgui_context", None) is not None:
                try:
                    # 不要强行 destroy（视你的实现），先清理现有资源
                    self.shutdown_imgui()
                except Exception:
                    pass
        except Exception:
            pass

        # 重新初始化 imgui（这会重建 context + renderer + upload font atlas）
        try:
            self.init_imgui()
        except Exception as e:
            print("GlobalImgui.reinit_after_file_load: init_imgui failed:", e)
    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = GlobalImgui()
        return cls._instance

    # ---------------- font / imgui init (同原来) ----------------
    @staticmethod
    def init_font():
        io = imgui.get_io()
        try:
            io.fonts.clear()
        except Exception:
            pass

        font_path = Path(__file__).parent.parent / "SourceHanSansCN-Normal.otf"
        if not font_path.exists():
            print("未找到字体文件：", font_path)
            return

        glyph_ranges = None
        try:
            atlas = io.fonts
            if hasattr(atlas, "get_glyph_ranges_chinese_full"):
                glyph_ranges = atlas.get_glyph_ranges_chinese_full()
            elif hasattr(atlas, "get_glyph_ranges_chinese_simplified_common"):
                glyph_ranges = atlas.get_glyph_ranges_chinese_simplified_common()
            elif hasattr(atlas, "get_glyph_ranges_cjk"):
                glyph_ranges = atlas.get_glyph_ranges_cjk()
            elif hasattr(atlas, "get_glyph_ranges_default"):
                glyph_ranges = atlas.get_glyph_ranges_default()
        except Exception:
            glyph_ranges = None

        if glyph_ranges is None:
            glyph_ranges = [
                0x0020, 0x007F,
                0x4E00, 0x9FFF,
                0x3000, 0x303F,
                0xFF00, 0xFFEF,
                0x2000, 0x206F,
                0x0000
            ]

        loaded_font = None
        try:
            try:
                loaded_font = io.fonts.add_font_from_file_ttf(str(font_path), 15.0, None)
            except TypeError:
                try:
                    loaded_font = io.fonts.add_font_from_file_ttf(str(font_path), 15.0, None)
                except TypeError:
                    loaded_font = io.fonts.add_font_from_file_ttf(str(font_path), 15.0)
        except Exception as e:
            print("加载字体失败:", e)
            loaded_font = None

        if loaded_font is None:
            print("字体加载未成功，请检查路径或字体文件是否受支持。")
        else:
            print("已添加字体:", font_path)

        try:
            io.font_default = loaded_font
        except Exception:
            try:
                if hasattr(io.fonts, "fonts") and len(io.fonts.fonts) > 0:
                    io.font_default = io.fonts.fonts[-1]
            except Exception:
                pass

        # 如果 renderer 已存在则触发上传
        # try:
        #     r = GlobalImgui.get().imgui_backend
        #     if r is not None and hasattr(r, "refresh_font_texture_ex"):
        #         try:
        #             r.refresh_font_texture_ex()
        #         except Exception:
        #             try:
        #                 r.refresh_font_texture_ex(None)
        #             except Exception as e:
        #                 print("尝试上传字体纹理失败：", e)
        # except Exception:
        #     pass

    def set_color(self):
        self.child_bg = imgui.ImVec4(0.1, 0.1, 0.1, 1.0)
        self.title_bg_active_color = imgui.ImVec4(0.1, 0.1, 0.1, 0.9)
        self.title_bg_color = imgui.ImVec4(0.1, 0.1, 0.1, 0.9)
        self.title_bg_collapsed_color = imgui.ImVec4(78 / 255.0, 85 / 255.0, 91 / 255.0, 134 / 255.0)
        self.frame_bg_color = imgui.ImVec4(0.39, 0.39, 0.39, 0.573)
        self.window_bg_color = imgui.ImVec4(0.137, 0.137, 0.137, 0.9)
        self.button_color = imgui.ImVec4(0.33, 0.33, 0.33, 1)
        self.button_hovered_color = imgui.ImVec4(0.39, 0.39, 0.39, 1)
        self.button_active_color = imgui.ImVec4(71 / 255.0, 114 / 255.0, 179 / 255.0, 1)
        self.header_color = imgui.ImVec4(75 / 255.0, 75 / 255.0, 75 / 255.0, 79 / 255.0)

    def init_imgui(self):
        if self.imgui_context is None:
            self.imgui_context = imgui.create_context()
            io = imgui.get_io()
            io.config_flags |= (imgui.ConfigFlags_.nav_enable_keyboard.value)
            io.config_flags |= imgui.ConfigFlags_.docking_enable.value

            # Windows 特定 clipboard hooks（保留原逻辑）
            if sys.platform == "win32":
                try:
                    user32 = ctypes.WinDLL('user32', use_last_error=True)
                    GetForegroundWindow = user32.GetForegroundWindow
                    GetForegroundWindow.restype = wintypes.HWND
                    hwnd = GetForegroundWindow()
                    imgui.platform_handle = hwnd
                    io.want_capture_keyboard = True

                    def _set_clipboard_text(_imgui_context, text: str) -> None:
                        bpy.context.window_manager.clipboard = text

                    def _get_clipboard_text(_imgui_context) -> str:
                        return bpy.context.window_manager.clipboard

                    imgui.get_platform_io().platform_set_clipboard_text_fn = _set_clipboard_text
                    imgui.get_platform_io().platform_get_clipboard_text_fn = _get_clipboard_text
                except Exception:
                    pass

            # 初始化字体与 renderer、按需设置 keymap
            self.init_font()
            try:
                self.imgui_backend = BlenderImguiRenderer()
            except Exception as e:
                print("初始化 BlenderImguiRenderer 失败：", e)
                self.imgui_backend = None
            try:
                # 将 renderer_has_textures 标志置位（某些绑定需要）
                imgio = imgui.get_io()
                imgio.backend_flags |= imgui.BackendFlags_.renderer_has_textures.value
            except Exception:
                pass

            # 如果后端存在，强制刷新字体纹理（兼容不同签名）
            if self.imgui_backend is not None:
                try:
                    # 首选：无参
                    self.imgui_backend.refresh_font_texture_ex()
                except TypeError:
                    try:
                        self.imgui_backend.refresh_font_texture_ex(None)
                    except Exception as e:
                        print("Failed to refresh font atlas on init:", e)
                except Exception as e:
                    print("Failed to refresh font atlas on init:", e)
            self.setup_key_map()

    # ---------------- 简化且安全的 draw handler 管理 ----------------
    def _safe_draw_handler_remove(self, space_type, handle, space_str='WINDOW'):
        """安全移除 draw handler（会捕获异常并清理）。"""
        if handle is None:
            return
        try:
            space_type.draw_handler_remove(handle, space_str)
        except Exception as e:
            # 忽略 already removed / invalid handler 错误，但打印 debug 信息
            if self.debug:
                print("safe_draw_handler_remove: 忽略移除错误:", e)

    def _ensure_region_handler(self, space_type, region_id, ops):
        """
        确保指定 region_id 有 Blender draw handler；如果没有则创建。
        返回该 region dict。
        """
        region = self._regions.get(region_id)
        if region is None:
            # 新建 region dict
            region = {
                "space_type": space_type,
                "handle": None,
                "callbacks": {}
            }
            self._regions[region_id] = region

        # 如果尚未创建 draw handler，则添加
        if region["handle"] is None:
            try:
                # Draw handler callback 参数：draw(self, area, ops)，我们传入 (space_type, ops)
                # 注意：采用与原代码相同的 draw() 签名
                handle = space_type.draw_handler_add(self.draw, (space_type, ops), 'WINDOW', 'POST_PIXEL')
                region["handle"] = handle
                # if self.debug:
                #     print(f"Added draw handler for region {region_id}: {handle}")
            except Exception as e:
                print("创建 draw handler 失败：", e)
                region["handle"] = None
        return region

    # 保持原有的 handler_add 接口（兼容现有调用）
    def handler_add(self, callback, space_type_and_region, ops):
        """
        callback: callable(context) — 在 draw 时被调用
        space_type_and_region: (SpaceType, region_id)
        ops: operator 或者包含 region 的对象（用于 draw 中判断 region）
        返回 callback id（可用于 handler_remove）
        """
        if self.imgui_context is None:
            self.init_imgui()

        SpaceTypeObj, region_id = space_type_and_region

        # 确保 region handler 存在
        region = self._ensure_region_handler(SpaceTypeObj, region_id, ops)

        # register callback
        cb_id = self._next_cb_id
        self._next_cb_id += 1
        region["callbacks"][cb_id] = (callback, region_id)
        # if self.debug:
        #     print(f"Registered callback {cb_id} for region {region_id}, total callbacks in region: {len(region['callbacks'])}")
        return cb_id

    def handler_remove(self, cb_id):
        """
        移除指定回调 id；若对应 region 无回调则移除 Blender draw handler。
        """
        if cb_id is None:
            return

        # 在所有 region 中查找 cb_id
        found_region_key = None
        for region_id, region in list(self._regions.items()):
            if cb_id in region["callbacks"]:
                found_region_key = region_id
                break

        if found_region_key is None:
            if self.debug:
                print("handler_remove: 未找到 cb_id:", cb_id)
            return

        region = self._regions[found_region_key]
        # 删除回调
        try:
            del region["callbacks"][cb_id]
            # if self.debug:
            #     print(f"Removed callback {cb_id} from region {found_region_key}, remaining: {len(region['callbacks'])}")
        except Exception:
            pass

        # 如果该 region 无回调了，则移除 draw handler 并从 _regions 中删除 entry
        if len(region["callbacks"]) == 0:
            handle = region.get("handle")
            space_type = region.get("space_type")
            # 安全移除
            try:
                self._safe_draw_handler_remove(space_type, handle, 'WINDOW')
            except Exception:
                pass
            # 清理
            try:
                del self._regions[found_region_key]
            except Exception:
                self._regions.pop(found_region_key, None)
            # if self.debug:
            #     print("handler_remove: region cleared:", found_region_key)

        # 如果所有 region 都被清理掉了，可选择 shutdown imgui（保留或注释）
        if not self._regions:
            try:
                self.shutdown_imgui()
            except Exception:
                pass

    # ---------------- shutdown ----------------
    def shutdown_imgui(self):
        """移除所有 draw handler 并清理状态（安全、幂等）。"""
        # if self.debug:
        #     print("shutdown_imgui: clearing all regions:", list(self._regions.keys()))
        # 1) 移除所有 draw handlers（保证没有回调在使用 ImGui）
        for region_id, region in list(self._regions.items()):
            try:
                space_type = region.get("space_type")
                handle = region.get("handle")
                self._safe_draw_handler_remove(space_type, handle, 'WINDOW')
            except Exception as e:
                if self.debug:
                    print("shutdown_imgui: 忽略移除错误:", e)
        self._regions.clear()

        # if self.debug:
        #     print("shutdown_imgui: done")


    def destroy_imgui_ct(self):
        """
        安全销毁 ImGui context（最后一步）。
        注意：不要在销毁后再调用任何 imgui.get_io()/io.fonts.* 等。
        """
        ctx = getattr(self, "imgui_context", None)
        if ctx is None:
            if self.debug:
                print("destroy_imgui_ct: no context to destroy")
            return

        # 尝试切换到目标 context（有些绑定需要此操作）
        try:
            curr = None
            try:
                curr = imgui.get_current_context()
            except Exception:
                curr = None
            try:
                imgui.set_current_context(ctx)
            except Exception:
                # 可能绑定没有此函数或无须切换，忽略
                pass
        except Exception:
            pass

        # 最后销毁 context（在确保不再调用 imgui API 之后）
        try:
            imgui.destroy_context(ctx)
        except Exception:
            # 如果销毁也崩溃，那基本上是绑定/版本不兼容的问题
            if self.debug:
                print("destroy_imgui_ct: destroy_context raised exception (ignored).")
        # 清空引用
        self.imgui_context = None
        if self.debug:
            print("destroy_imgui_ct: done")


    def shutdown_all_resources(self):
        """
        安全顺序：
        1) 移除 handlers / 停止回调
        2) 切换到我们的 imgui context（如果可用）
        3) 解除 ImGui 对 GPU 纹理的引用（io.fonts.texture_id = 0）
        4) 释放后端 GPU 资源（shader / GPUTexture / 清理缓存）
        5) （可选）尝试清理 io.fonts（如果安全）
        6) 销毁 ImGui context（最后）
        7) 删除 Blender Image（仅当 users == 0）
        """
        if self.debug:
            print("[DEBUG] shutdown_all_resources: start")

        # 0) 移除所有 draw handler（保证没有回调正在使用 ImGui）
        try:
            self.shutdown_imgui()
        except Exception:
            pass

        # 1) 切换到我们的 context（如果存在且可切换）
        ctx = getattr(self, "imgui_context", None)
        curr_ctx = None
        if ctx is not None:
            try:
                try:
                    curr_ctx = imgui.get_current_context()
                except Exception:
                    curr_ctx = None
                try:
                    imgui.set_current_context(ctx)
                except Exception:
                    pass
            except Exception:
                pass

        # 2) 解除 ImGui 对 GPU 纹理的引用（不要在销毁后再做）
        try:
            if ctx is not None:
                try:
                    io = imgui.get_io()  # 仅在 context 存在且已切换时安全调用
                    try:
                        io.fonts.texture_id = 0
                    except Exception:
                        pass
                except Exception:
                    # 无法获取 io（可能绑定不支持 get_current_context），则跳过
                    if self.debug:
                        print("[DEBUG] shutdown_all_resources: cannot get io; skipping io cleanup")
        except Exception:
            pass

        # 3) 释放后端 GPU 资源（shader / texture）
        try:
            if getattr(self, "imgui_backend", None):
                try:
                    # 这个函数应当尽量不依赖 ImGui context，如果依赖，确保上面已切换
                    self.imgui_backend._invalidate_device_objects()
                except Exception:
                    if self.debug:
                        print("[DEBUG] shutdown_all_resources: backend _invalidate failed")
                # 清空引用
                self.imgui_backend = None
        except Exception:
            pass
        if self.debug:
            print("[DEBUG]: ImGui 清理完后端")

        # 4) （可选且有风险）尝试清理 fonts atlas 数据 —— 如果这个步骤曾导致崩溃，请注释掉它
        fonts_cleared = False
        try:
            if ctx is not None:
                try:
                    io = imgui.get_io()
                    # **小心：io.fonts.clear() 在某些绑定/版本上会触发原生崩溃**
                    # 如果你之前遇到崩溃，请不要调用下面一行（注释掉）
                    if hasattr(io.fonts, "clear"):
                        try:
                            io.fonts.clear()
                            fonts_cleared = True
                            if self.debug:
                                print("[DEBUG]: io.fonts.clear() succeeded")
                        except Exception:
                            # 若 clear 报错，不要继续，跳过
                            if self.debug:
                                print("[DEBUG]: io.fonts.clear() raised exception; skipped")
                except Exception:
                    if self.debug:
                        print("[DEBUG]: cannot call io.fonts.clear() (get_io failed)")
        except Exception:
            pass

        if self.debug and not fonts_cleared:
            print("[DEBUG]:  ImGui 清理完字体 或者已被跳过（为了防止崩溃）")

        # 5) 销毁 ImGui 上下文（最后）
        try:
            self.destroy_imgui_ct()
        except Exception:
            pass

        # 6) 删除 Blender Image（如果我们记录了并且没有 users）
        try:
            font_img = getattr(self, "_font_image", None)
            if font_img is None and getattr(self, "imgui_backend", None):
                font_img = getattr(self.imgui_backend, "_font_image", None)
            if font_img is not None:
                try:
                    # 以名字查找 image（更稳妥）
                    if getattr(font_img, "name", None) in bpy.data.images:
                        img = bpy.data.images[font_img.name]
                        if getattr(img, "users", 0) == 0:
                            bpy.data.images.remove(img)
                            if self.debug:
                                print("[DEBUG] removed font image:", font_img.name)
                        else:
                            if self.debug:
                                print("[DEBUG] font image still has users:", img.users)
                except Exception:
                    pass
                try:
                    self._font_image = None
                except Exception:
                    pass
        except Exception:
            pass

        if self.debug:
            print("[DEBUG]: ImGui 所有资源彻底销毁完成。")

    # ---------------- draw（保持原 draw 逻辑，但用新的回调分发） ----------------
    def apply_ui_settings(self):
        region = bpy.context.region
        imgui.get_io().display_size = (region.width, region.height)
        style = imgui.get_style()
        style.window_padding = (1, 1)
        style.window_rounding = 6
        style.frame_rounding = 2
        style.frame_border_size = 1
        style.indent_spacing = 8
        style.scrollbar_size=6
        style.set_color_(2, imgui.ImVec4(0, 0, 0, 0.55))

    def draw(self, space_type, ops):
            """
            Blender draw handler callback — 
            'space_type' 是从 draw_handler_add 的 args 传入的 (e.g., bpy.types.SpaceView3D)
            'ops' 是 Imgui_Window_Imgui 实例 (从 args 传入)
            """
            
            # 🌟 关键修复：
            current_area = None
            try:
                # 1. 从 bpy.context 获取当前 Blender 正在绘制的 area
                current_area = bpy.context.area 
                
                # 2. 检查 ops 是否有效，以及 ops.area 是否是当前 area
                if not ops or not hasattr(ops, 'area') or current_area != ops.area:
                    # 如果不是目标区域 (例如，Blender 正在绘制 视图 B)，
                    # 则*立即*返回，不执行任何 ImGui 调用。
                    return
            except Exception as e:
                # ops 可能已失效 (例如 ReferenceError)，安全退出
                # print(f"GlobalImgui.draw: Area check failed: {e}")
                return
                
            # -----------------------------------------------
            # 只有在 current_area == ops.area 时 (即在 视图 A 中)，
            # 才执行下面的所有 ImGui 绘制逻辑
            # -----------------------------------------------

            # 基础设置
            try:
                # 注意：apply_ui_settings 内部也依赖 bpy.context
                self.apply_ui_settings()
            except Exception:
                pass

            # new_frame / context 切换 防护
            try:
                if getattr(self, "imgui_context", None) is not None:
                    try:
                        imgui.set_current_context(self.imgui_context)
                    except Exception:
                        pass
                try:
                    # 🌟 修复：使用我们刚获取的 current_area，而不是未定义的 'area'
                    region = current_area.regions.active if current_area.regions else None
                    if region:
                        imgui.get_io().display_size = (region.width, region.height)
                    else:
                        # 备用方案（如果 area.regions.active 不可靠）
                        region = bpy.context.region
                        imgui.get_io().display_size = (region.width, region.height)
                except Exception:
                    pass

                imgui.new_frame()
            except Exception:
                # new_frame 失败直接返回，避免后续调用导致崩溃
                print('[DEBUG]:new frame启动失败')
                traceback.print_exc()
                return

            # Push style — 保证 push/pop 配对（using try/finally）
            pushed_colors = 0
            try:
                imgui.push_style_color(imgui.Col_.frame_bg.value, self.frame_bg_color); pushed_colors += 1
                imgui.push_style_color(imgui.Col_.window_bg.value, self.window_bg_color); pushed_colors += 1
                imgui.push_style_color(imgui.Col_.title_bg.value, self.title_bg_color); pushed_colors += 1
                imgui.push_style_color(imgui.Col_.title_bg_active.value, self.title_bg_active_color); pushed_colors += 1
                imgui.push_style_color(imgui.Col_.title_bg_collapsed.value, self.title_bg_collapsed_color); pushed_colors += 1
                imgui.push_style_color(imgui.Col_.button.value, self.button_color); pushed_colors += 1
                imgui.push_style_color(imgui.Col_.button_hovered.value, self.button_hovered_color); pushed_colors += 1
                imgui.push_style_color(imgui.Col_.button_active.value, self.button_active_color); pushed_colors += 1
                imgui.push_style_color(imgui.Col_.header.value, self.header_color); pushed_colors += 1

                imgui.get_style().set_color_(5, imgui.ImVec4(0, 0, 0, 0))
                imgui.push_style_var(20, 1)

                # dispatch callbacks for this region
                try:
                    region_ptr = None
                    try:
                        # 使用 ops.region, 因为 ops 是 Imgui_Window_Imgui 实例
                        region_ptr = ops.region.as_pointer()
                    except Exception:
                        region_ptr = getattr(ops, "region_id", None)

                    if region_ptr is not None and region_ptr in self._regions:
                        callbacks = list(self._regions[region_ptr]["callbacks"].items())
                        for cb_id, (cb, user_data) in callbacks:
                            try:
                                # 现在 cb (Imgui_Window_Imgui.draw) 被安全调用
                                # 它的内部检查 (context.area == self.area) 也会通过
                                cb(bpy.context)
                            except Exception:
                                traceback.print_exc()
                    else:
                        # 没有对应 region，什么也不做
                        pass
                except Exception:
                    traceback.print_exc()

            finally:
                # Pop style var + pop all pushed colors (保证平衡)
                try:
                    # 先 pop var（如果 push 了）
                    try:
                        imgui.pop_style_var(1)
                    except Exception:
                        pass

                    # pop pushed colors 按实际 pushed 数量来回退
                    for _ in range(pushed_colors):
                        try:
                            imgui.pop_style_color()
                        except Exception:
                            pass
                except Exception:
                    pass

            # end frame & render
            try:
                imgui.end_frame()
            except Exception:
                # 即使 end_frame 失败，也尝试调用 render（部分绑定需要 end_frame+render）
                pass
                print('[DEBUG]:endframe失败')
            try:
                imgui.render()
            except Exception:
                # render 失败可能意味着内部断言（例如 Missing PopStyleColor），打印并跳过渲染
                traceback.print_exc()
                print('[DEBUG]:end render失败')
                return

            # 安全地获取 draw_data，并在为 None 时直接跳过后端渲染
            try:
                draw_data = imgui.get_draw_data()
            except Exception:
                draw_data = None

            if draw_data is None:
                if self.debug:
                    print("draw: imgui.get_draw_data() returned None — skipping backend.render()")
                return

            # Use backend to render the draw lists, guard exceptions so one bad frame doesn't crash
            try:
                if getattr(self, "imgui_backend", None) is not None:
                    self.imgui_backend.render(draw_data)
            except Exception:
                traceback.print_exc()
    def setup_key_map(self):
        io = imgui.get_io()
        keys = (
            imgui.Key.tab,
            imgui.Key.left_arrow,
            imgui.Key.right_arrow,
            imgui.Key.up_arrow,
            imgui.Key.down_arrow,
            imgui.Key.home,
            imgui.Key.end,
            imgui.Key.insert,
            imgui.Key.delete,
            imgui.Key.backspace,
            imgui.Key.enter,
            imgui.Key.escape,
            imgui.Key.page_up,
            imgui.Key.page_down,
            imgui.Key.a,
            imgui.Key.c,
            imgui.Key.v,
            imgui.Key.x,
            imgui.Key.y,
            imgui.Key.z,
            imgui.Key.left_ctrl,
            imgui.Key.right_ctrl,
            imgui.Key.left_shift,
            imgui.Key.right_shift,
            imgui.Key.left_alt,
            imgui.Key.right_alt,
            imgui.Key.left_super,
            imgui.Key.right_super,

        )
        # for k in keys:
        #     # We don't directly bind Blender's event type identifiers
        #     # because imgui requires the key_map to contain integers only
        #     # io.add_input_character(k)
        #     io.key_map[k] = k

from bpy.app.handlers import persistent
@persistent
def _globalimgui_load_pre(dummy):
    try:
        GlobalImgui.get().prepare_for_file_reload()
    except Exception:
        pass

@persistent
def _globalimgui_load_post(dummy):
    try:
        GlobalImgui.get().reinit_after_file_load()
    except Exception:
        pass
