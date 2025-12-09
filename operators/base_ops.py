from pathlib import Path
import bpy
import gpu
import numpy as np
import OpenImageIO as oiio
from imgui_bundle import imgui
from ..render import Renderer as BlenderImguiRenderer
from ..imgui_setup.imgui_global import GlobalImgui
def imgui_handler_remove(handle):
    GlobalImgui.get().handler_remove(handle)

class BaseDrawCall:
    # 定义键盘按键映射，键是字符串表示，值是 ImGui 中定义的键码
    key_map = {
        'TAB': imgui.Key.tab,
        'LEFT_ARROW': imgui.Key.left_arrow,
        'RIGHT_ARROW': imgui.Key.right_arrow,
        'UP_ARROW': imgui.Key.up_arrow,
        'DOWN_ARROW': imgui.Key.down_arrow,
        'HOME': imgui.Key.home,
        'END': imgui.Key.end,
        'INSERT': imgui.Key.insert,
        'DEL': imgui.Key.delete,
        'BACK_SPACE': imgui.Key.backspace,
        'SPACE': imgui.Key.space,
        'RET': imgui.Key.enter,
        'NUMPAD_ENTER': imgui.Key.enter,
        'ESC': imgui.Key.escape,
        'PAGE_UP': imgui.Key.page_up,
        'PAGE_DOWN': imgui.Key.page_down,
        'A': imgui.Key.a,
        'C': imgui.Key.c,
        'V': imgui.Key.v,
        'X': imgui.Key.x,
        'Y': imgui.Key.y,
        'Z': imgui.Key.z,
        'LEFT_CTRL': imgui.Key.left_ctrl,
        'RIGHT_CTRL': imgui.Key.right_ctrl,
        'LEFT_ALT': imgui.Key.left_alt,
        'RIGHT_ALT': imgui.Key.right_alt,
        'LEFT_SHIFT': imgui.Key.left_shift,
        'RIGHT_SHIFT': imgui.Key.right_shift,
        'OSKEY': imgui.Key.comma,
    }

    def __init__(self):
        self.c = .0
        self.mpos = (0, 0)  # 初始化鼠标位置
    def _get_current_region_and_mpos(self, context, event):
        """
        在 invoke 时执行，用于找到操作符启动时鼠标所在的区域 (Region)
        并计算区域局部坐标 (mpos)。
        """
        gx, gy = event.mouse_x, event.mouse_y
        
        region = None
        # 查找当前鼠标所在的区域 (这个循环在 invoke 中只执行一次是可接受的)
        for area in context.window.screen.areas:
            for r in area.regions:
                if (gx >= r.x and gx <= r.x + r.width and
                    gy >= r.y and gy <= r.y + r.height):
                    region = r
                    self.area = area # 保存 Area 供 ImGui 初始化使用
                    break
            if region:
                break
        
        if region is None:
            # 如果找不到，返回 None，让 invoke 退出
            return None, (0, 0)

        # 计算区域内的鼠标局部坐标 (Local Coordinates)
        mx = gx - region.x
        my = gy - region.y
        
        return region, (mx, my)
    def init_imgui(self, context):
        from ..imgui_setup.imgui_global import GlobalImgui
        GlobalImgui.get().close_ui=False
        self.main_window=[True,True]
         # 先把 area 和 region 存下来
        # self.area   = context.area
        # self.region = context.region
        # print(self.area,self.region)
        self._key_state = {}

        self.clipboard=''
        self._next_texture_id = 2#1或者0是fonts
        
        
        if self.area.type == 'VIEW_3D':
            # print('添加句柄,',self.region.as_pointer())
            self.imgui_handle = GlobalImgui.get().handler_add(
                self.draw,
                (bpy.types.SpaceView3D, self.region.as_pointer()),
                self,
            ) 
        
        elif self.area.type=='IMAGE_EDITOR':
            self.imgui_handle = GlobalImgui.get().handler_add(self.draw, bpy.types.SpaceImageEditor, self)
        # print('imgui handle',self.imgui_handle)       
    def draw(self, context):
        pass
    def load_icon(self):
        pass
    
    # --- load_png_to_gpu_texture 函数定义 (复制粘贴上述完整函数代码) ---
    def load_png_to_gpu_texture(self, filepath: str) -> gpu.types.GPUTexture:
        """
        使用OpenImageIO和NumPy将本地PNG图像加载为gpu.types.GPUTexture。

        此函数不使用PIL或bpy.data.images.load()。

        Args:
            filepath (str): 本地PNG图像文件的完整路径。

        Returns:
            gpu.types.GPUTexture: 加载的GPU纹理对象。
            如果加载失败，则返回None。
        """
        if oiio is None:
            print("OpenImageIO模块未加载，无法执行图像导入。")
            return None

        img_input = oiio.ImageInput.open(filepath)
        if not img_input:
            print(f"错误：无法打开图像文件或文件格式不受支持 - {filepath}")
            return None

        try:
            # 获取图像规格
            spec = img_input.spec()
            width = spec.width
            height = spec.height
            nchannels = spec.nchannels
            oiio_format = spec.format

            # print(f"图像规格：{width}x{height}, 通道数：{nchannels}, OIIO格式：{oiio_format}")

            pixels_np = img_input.read_image(format=oiio.TypeDesc("uint8"))
            if pixels_np is None:
                print(f"错误：无法读取图像像素数据或文件格式不受支持 - {filepath}")
                return None
                # print(f"错误：无法读取图像像素数据 - {filepath}")
                # return None
                # 确保读取到的NumPy数组形状与预期一致
            if pixels_np.shape != (height, width, nchannels):
                print(f"警告：读取到的图像数据形状不匹配预期。预期：({height}, {width}, {nchannels})，实际：{pixels_np.shape}")
                nchannels = pixels_np.shape[2] if len(pixels_np.shape) == 3 else 1
            # 通道处理
            if nchannels == 3:
                # print("检测到3通道RGB图像，添加一个完全不透明的Alpha通道。")
                rgba_pixels = np.zeros((height, width, 4), dtype=np.uint8)
                rgba_pixels[:, :, :3] = pixels_np[:, :, :3]
                rgba_pixels[:, :, 3] = 255
                final_pixels_np = rgba_pixels
                target_channels = 4
                gpu_format_str = 'RGBA8'
            elif nchannels == 4:
                # print("图像已包含Alpha通道。")
                final_pixels_np = pixels_np
                target_channels = 4
                gpu_format_str = 'RGBA8'
            elif nchannels == 1:
                # print("检测到1通道灰度图像，转换为RGBA。")
                rgba_pixels = np.zeros((height, width, 4), dtype=np.uint8)
                rgba_pixels[:, :, 0] = pixels_np[:, :, 0]
                rgba_pixels[:, :, 1] = pixels_np[:, :, 0]
                rgba_pixels[:, :, 2] = pixels_np[:, :, 0]
                rgba_pixels[:, :, 3] = 255
                final_pixels_np = rgba_pixels
                target_channels = 4
                gpu_format_str = 'RGBA8'
            else:
                # print(f"警告：不支持的通道数 ({nchannels})。尝试使用原始数据。")
                final_pixels_np = pixels_np
                target_channels = nchannels
                if nchannels == 1:
                    gpu_format_str = 'R8'
                elif nchannels == 2:
                    gpu_format_str = 'RG8'
                else:
                    gpu_format_str = 'RGBA8'

            # 扁平化数据
            float_pixels = final_pixels_np.astype(np.float32) / 255.0
            flattened_pixels = float_pixels.ravel()
            # flattened_pixels = final_pixels_np.ravel()

            # 创建 GPU Buffer
            gpu_buffer = gpu.types.Buffer('FLOAT', (width * height * target_channels,), flattened_pixels)

            # 创建 GPU 纹理
            gpu_texture = gpu.types.GPUTexture(size=(width, height), format=gpu_format_str, data=gpu_buffer)
            # print(f"成功创建GPUTexture：尺寸 {width}x{height}, 格式 {gpu_format_str}")

            return gpu_texture

        except Exception as e:
            print(f"在加载PNG到GPU纹理时发生错误：{e}")
            import traceback
            traceback.print_exc()
            return None

        finally:
            img_input.close()

    def load_icon_texture(self, path: str) -> int:
        # 1. 生成完整的唯一文件路径作为缓存Key
        full_path = str(Path(__file__).parent.parent / 'icons' / path)
        # 2. 检查缓存：如果文件路径已存在于映射中，直接返回现有 ID
        if full_path in BlenderImguiRenderer._path_to_id_map:
            return BlenderImguiRenderer._path_to_id_map[full_path]

        # 3. 首次加载：加载到 GPU
        tex = self.load_png_to_gpu_texture(full_path)
        if tex is None:
            return 0 # 返回一个无效 ID 或处理错误

        # 4. 分配唯一的全局 ID
        texture_id = BlenderImguiRenderer._next_texture_id
        BlenderImguiRenderer._next_texture_id += 1
        
        # 5. 更新缓存和映射
        BlenderImguiRenderer._texture_cache[texture_id] = tex
        BlenderImguiRenderer._path_to_id_map[full_path] = texture_id
    
    # print(f"加载新图标：{path}, 分配 ID: {texture_id}")
        # print('载入图像路径:',Path(__file__))
        # tex=self.load_png_to_gpu_texture(str(Path(__file__).parent.parent/'icons'/path))
        # # bindcode = tex.gl_load()
        # texture_id = self._next_texture_id
        # self._next_texture_id += 1
        # # 你这边的缓存机制
        # # texture_id = gl.glGenTextures(1)
        # BlenderImguiRenderer._texture_cache[texture_id] = tex
        return texture_id
    

    def call_shutdown_imgui(self):
        # print('[DEBUG]:关闭窗口')
        if hasattr(self, 'color_palette'):
            bpy.context.scene['color_picker_col']=self.color_palette
        if hasattr(self,'ops_name'):
            GlobalImgui.get().main_window=False
        imgui_handler_remove(self.imgui_handle)

    def track_any_cover(self):

        self.cover = (
            imgui.is_any_item_hovered() 
            # or imgui.is_window_hovered(imgui.HoveredFlags_.root_and_child_windows)
            or imgui.is_window_hovered() or imgui.get_io().want_capture_mouse 
            or imgui.get_io().want_text_input
        )
        # print('self.cover',self.cover)
    def track_any_cover_style_editor(self):

        self.cover_style_editor = (
            imgui.is_any_item_hovered() 
            # or imgui.is_window_hovered(imgui.HoveredFlags_.root_and_child_windows)
            or imgui.is_window_hovered() or imgui.get_io().want_capture_mouse 
            or imgui.get_io().want_text_input
        )
        # print('self.cover_style_editor',self.cover)
    def poll_mouse(self, context: bpy.types.Context, event: bpy.types.Event):
        io = imgui.get_io()  # 获取 ImGui 的 IO 对象
        # 将 Blender 的鼠标位置转换为 ImGui 的坐标系
        io.add_mouse_pos_event(self.mpos[0], self.region.height - 1 - self.mpos[1])
        # 根据事件类型更新 ImGui 的鼠标状态
        if event.type == 'LEFTMOUSE':
            io.add_mouse_button_event(0, event.value == 'PRESS')
        elif event.type == 'RIGHTMOUSE':
            io.add_mouse_button_event(1, event.value == 'PRESS')
        elif event.type == 'MIDDLEMOUSE':
            io.add_mouse_button_event(2, event.value == 'PRESS')
        if event.type == 'WHEELUPMOUSE':
            io.add_mouse_wheel_event(0, 1)
        elif event.type == 'WHEELDOWNMOUSE':
            io.add_mouse_wheel_event(0, -1)

    def poll_events(self, context: bpy.types.Context, event: bpy.types.Event):
        io = imgui.get_io()

        # 将 Blender 事件映射为 ImGuiKey 枚举
        if event.type in self.key_map:
            imgui_key = self.key_map[event.type]  # 已映射为 ImGuiKey.xxx
            is_press = (event.value == 'PRESS')
            self._key_state[imgui_key] = is_press  # 👈 存储键盘状态
            io.add_key_event(imgui_key, is_press)

        # 更新修饰键状态（可选，用于确保一致性）

        # 分别更新 Ctrl、Shift、Alt、Super 修饰键状态
        def key_down(key_name):
            k = self.key_map.get(key_name)
            return k is not None and self._key_state.get(k, False)

        io.add_key_event(imgui.Key.left_ctrl, key_down('LEFT_CTRL'))
        # print('左ctrl',key_down('LEFT_CTRL'))
        io.add_key_event(imgui.Key.right_ctrl, key_down('RIGHT_CTRL'))
        io.add_key_event(imgui.Key.left_shift, key_down('LEFT_SHIFT'))
        io.add_key_event(imgui.Key.right_shift, key_down('RIGHT_SHIFT'))
        io.add_key_event(imgui.Key.left_alt, key_down('LEFT_ALT'))
        io.add_key_event(imgui.Key.right_alt, key_down('RIGHT_ALT'))
        io.add_key_event(imgui.Key.left_super, key_down('OSKEY'))

        if event.type == 'C' and event.ctrl and event.value == 'PRESS':
            GlobalImgui.get().ctrl_c=True
        if event.type == 'X' and event.ctrl and event.value == 'PRESS':
            GlobalImgui.get().ctrl_x=True
        if event.type == 'A' and event.ctrl and event.value == 'PRESS':
            GlobalImgui.get().ctrl_a=True
        if event.type == 'V' and event.ctrl and event.value == 'PRESS':
            GlobalImgui.get().ctrl_v=True
        if event.unicode and 0 < (char := ord(event.unicode)) < 0x10000:
            io.add_input_character(char)
    def cancel(self, context):
        print("Operator 被 Blender 取消，执行清理")
        self.call_shutdown_imgui()
        self.refresh()
        return {'CANCELED'}
    def refresh(self):
        for area in bpy.context.screen.areas:
            if area.type in ['VIEW_3D','IMAGE_EDITOR']:
                area.tag_redraw()
import traceback

class IMGUI_OT_shutdown_all(bpy.types.Operator):
    """安全地注销并释放 ImGui 相关资源（移除 handlers、销毁 context、释放 GPU 纹理等）
    用于在卸载插件或重新加载时强制清理 ImGui 状态。"""
    bl_idname = "imgui.shutdown_all"
    bl_label = "Shutdown ImGui (safe)"
    bl_options = {'REGISTER'}

    def execute(self, context):
        try:
            # 1) 告知全局管理器准备进行文件/进程重载（内部会标记窗口关闭、移除 draw handlers 等）
            try:
                GlobalImgui.get().prepare_for_file_reload()
            except Exception as e:
                # 非致命：记录并继续
                print("[DEBUG] prepare_for_file_reload failed:", e)
                traceback.print_exc()

            self.report({'INFO'}, "开始清理 ImGui（prepare_for_file_reload 执行完毕）")
            print('[DEBUG]: 注销 imgui (prepare_for_file_reload done)')

            # 2) 如果有正在运行的 operator（例如你的 ImGui 窗口 operator），尝试优雅地取消它
            try:
                wm = bpy.context.window_manager
                # wm.operators 是一个 collection，可以通过 key 字符串判断是否存在
                # 保守地尝试遍历并调用 cancel 或 finish
                found = False
                for op_name in list(wm.operators):
                    # op_name 看起来像 "IMGUI_OT_window"（取决于 operator 定义）
                    if "IMGU" in op_name.upper() or "IMGUi" in op_name:
                        # 仅作提示（部分 Blender 版本 wm.operators 行为差异大）
                        print("可能的 ImGui operator entry:", op_name)
                    # 兼容你原先检查字符串的方式
                # 兼容原代码的快速检查
                if 'IMGUI_OT_window' in wm.operators:
                    try:
                        print('IMGUI_OT_window found in wm.operators, attempting cancel')
                        wm.operators['IMGUI_OT_window'].cancel(bpy.context)
                        found = True
                    except Exception as e:
                        print("cancel IMGUI_OT_window failed:", e)
                if found:
                    self.report({'INFO'}, "尝试取消 IMGUI_OT_window。")
            except Exception as e:
                # 非致命：记录并继续
                print("[DEBUG] checking/cancelling running operators failed:", e)
                traceback.print_exc()

            # 3) 最终执行全面资源销毁（后端/纹理/context 等）
            try:
                GlobalImgui.get().shutdown_all_resources()
                print('[DEBUG]: ImGui 资源清理完毕。')
                self.report({'INFO'}, "ImGui 资源清理完毕。")
            except Exception as e:
                print(f'[ERROR]: ImGui 资源清理失败，可能导致崩溃: {e}')
                traceback.print_exc()
                self.report({'ERROR'}, f"ImGui 资源清理失败: {e}")
                # 仍然返回 FINISHED，因为我们记录了错误
                return {'FINISHED'}

        except Exception as e:
            # 最后兜底
            print("[ERROR] unexpected error while shutting down ImGui:", e)
            traceback.print_exc()
            self.report({'ERROR'}, f"Shutdown failed: {e}")
            return {'CANCELLED'}

        return {'FINISHED'}
