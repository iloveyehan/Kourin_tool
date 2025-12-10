# -*- coding: utf-8 -*-
"""
Blender-friendly ImGui renderer (Blender.gpu backend compatible)
This file is a self-contained Renderer class to replace the OpenGL-only path and
work in Blender whether the GPU backend is OpenGL or Vulkan.

Usage: instantiate Renderer() once (the code registers a persistent handler to
refresh fonts on file load). The imgui_bundle side should call renderer.render(draw_data)
as the imgui draw callback (depending on how you integrate with imgui_bundle).
"""
import hashlib
import json
import platform
import uuid
import subprocess
def get_mac():
    try:
        mac = uuid.getnode()
        return f"{mac:012x}"
    except Exception:
        return ""

def run_cmd(cmd):
    try:
        out = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL, timeout=2)
        return out.decode(errors='ignore').strip()
    except Exception:
        return ""

def get_windows_serials():
    info = {}
    info['bios_serial'] = run_cmd('wmic bios get serialnumber /value').split('=')[-1].strip()
    # info['disk_serial'] = run_cmd('wmic diskdrive get serialnumber /value').split('=')[-1].strip()
    info['baseboard_serial'] = run_cmd('wmic baseboard get serialnumber /value').split('=')[-1].strip()
    return info

def get_linux_ids():
    info = {}
    try:
        with open('/etc/machine-id','r') as f:
            info['machine_id'] = f.read().strip()
    except Exception:
        pass
    return info

def get_macos_ids():
    info = {}
    out = run_cmd("system_profiler SPHardwareDataType | awk -F': ' '/Serial/ {print $2; exit}'")
    info['serial'] = out
    return info

def collect_raw():
    system = platform.system()
    data = {
        "platform": system,
    }
    data['mac'] = get_mac()
    if system == "Windows":
        data.update(get_windows_serials())
    elif system == "Linux":
        data.update(get_linux_ids())
    elif system == "Darwin":
        data.update(get_macos_ids())
    data['processor'] = platform.processor() or run_cmd("uname -m")
    return data

def compute_hwid(data: dict) -> str:
    keys = ["platform","mac","processor","bios_serial","baseboard_serial","disk_serial","machine_id","serial"]
    s = [f"{k}={data.get(k,'')}" for k in keys]
    raw = "|".join(s).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()

import ctypes
import time
import numpy as np
import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from gpu.types import GPUShaderCreateInfo
from imgui_bundle import imgui
from .secure_license import get_secret_list,get_hwid
# Renderer class
class Renderer(object):
    instance = None
    _texture_cache = {}  # key -> gpu.types.GPUTexture
    _next_texture_id=2
    _path_to_id_map = {}
    debug = 0  # set True to enable debug prints


    _interval: float = 0.3  # 默认 0.5 秒执行一次
    _start_time = time.perf_counter()
    _last_tick = _start_time

    def __init__(self):
        license_list = get_secret_list()
        print('hwid:',compute_hwid(collect_raw()))
        print('hwid:',get_hwid())
        if get_hwid() not in license_list and compute_hwid(collect_raw()) not in license_list:
        # if compute_hwid(collect_raw()) not in license_list:
            raise RuntimeError("HWID 验证失败")
        Renderer.instance = self

        # Blender gpu shader object
        self._bl_shader = None
        # cached font GPU texture (GPUTexture)
        self._font_tex = None
        # logical key in _texture_cache for font
        self._font_texture = 1

        self.io = imgui.get_io()
        self.io.delta_time = 1.0 / 60.0

        # create shader (via create_from_info)
        self._create_device_objects()

        # Inform ImGui that backend supports textures
        try:
            self.io.backend_flags |= imgui.BackendFlags_.renderer_has_textures.value
        except Exception:
            # some bindings may differ; ignore if fails
            pass

        # set renderer texture limits from Blender capabilities
        try:
            max_tex = self.get_max_texture_size()
            try:
                imgui.get_platform_io().renderer_texture_max_width = max_tex
                imgui.get_platform_io().renderer_texture_max_height = max_tex
            except Exception:
                # ignore if platform_io not present
                pass
        except Exception:
            pass

        # register persistent handler to refresh font texture on file load
        # try:
        #     if self.refresh_font_texture_ex not in bpy.app.handlers.load_post:
        #         bpy.app.handlers.load_post.append(self.refresh_font_texture_ex)
        # except Exception:
        #     pass

        # attempt initial font upload
        # try:
        #     self.refresh_font_texture_ex()
        # except Exception as e:
        #     if Renderer.debug:
        #         print("Initial refresh_font_texture_ex failed:", e)

    # ---------------- utilities ----------------
    @staticmethod
    def get_max_texture_size():
        try:
            # Blender gpu capability (may differ by version)
            return gpu.capabilities.max_texture_size_get()
        except Exception:
            # fallback
            return 16384

    @staticmethod
    def to_imgui_texref(tex_id):
        """
        Convert integer key to imgui's ImTextureRef/ImTextureID if available.
        Otherwise return the integer.
        """
        try:
            ImTextureRef = getattr(imgui, "ImTextureRef", None) or getattr(imgui, "ImTextureID", None)
            if ImTextureRef is not None:
                try:
                    return ImTextureRef(int(tex_id))
                except Exception:
                    try:
                        return ImTextureRef(ctypes.c_void_p(int(tex_id)))
                    except Exception:
                        return tex_id
        except Exception:
            pass
        return tex_id

    # ---------------- shader creation ----------------
    def create_imgui_shader(self):
        """
        Create a GPU shader via GPUShaderCreateInfo compatible with Blender's gpu module.
        Matches vertex attributes: Position(vec3), UV(vec2), Color(vec4)
        """
        shader_info = GPUShaderCreateInfo()
        vert_out = gpu.types.GPUStageInterfaceInfo("my_interface")
        vert_out.smooth('VEC2', "Frag_UV")
        vert_out.smooth('VEC4', "final_col")

        shader_info.vertex_in(0, "VEC3", "Position")
        shader_info.vertex_in(1, "VEC2", "UV")
        shader_info.vertex_in(2, "VEC4", "Color")
        shader_info.vertex_out(vert_out)

        shader_info.push_constant("MAT4", "ProjMtx")
        shader_info.sampler(0, "FLOAT_2D", "Texture")

        # vertex source
        shader_info.vertex_source('''
            void main() {
                Frag_UV = UV;
                final_col = Color;
                gl_Position = ProjMtx * vec4(Position.xy, 0.0, 1.0);
            }
        ''')

        # fragment source
        shader_info.fragment_source('''
            void main() {
                vec4 tex_color = texture(Texture, Frag_UV);
                vec4 col = final_col;
                // simple gamma correction; keep as-is (optional)
                                    
                col.rgb = pow(col.rgb, vec3(2.2));
                col.a = 1.0 - pow(1.0 - col.a, 2.2);
                Frag_Color = tex_color * col;
            }
        ''')

        shader_info.fragment_out(0, "VEC4", "Frag_Color")
        return gpu.shader.create_from_info(shader_info)

    def _create_device_objects(self):
        try:
            self._bl_shader = self.create_imgui_shader()
            if Renderer.debug:
                print("Created Blender GPU shader for ImGui.")
        except Exception as e:
            print("Failed to create shader:", e)
            self._bl_shader = None

    def _invalidate_device_objects(self):
        # free shader
        try:
            if self._bl_shader:
                self._bl_shader.free()
        except Exception:
            pass
        self._bl_shader = None

        # clear font cache
        try:
            Renderer._texture_cache.clear()
            Renderer._next_texture_id=2
            Renderer._path_to_id_map.clear()
            self._font_tex = None
            self._font_texture = 0
        except Exception:
            pass

    # ---------------- font atlas -> Blender GPU texture ----------------
    # @staticmethod
    # @bpy.app.handlers.persistent
    def refresh_font_texture_ex(self,scene=None):
        """
        Robustly obtain ImGui font atlas bytes and upload them into a Blender Image + GPUTexture.
        Stores the GPU texture in Renderer._texture_cache[0] and sets io.fonts.texture_id accordingly.
        """
        # self = Renderer.instance
        if self is None:
            return
        # if self._font_tex is not None:
        #     return
        io = imgui.get_io()

  
        width = height = None
        pixels = None

        get_tex = io.fonts.tex_data
        width  =get_tex.width
        height = get_tex.height
        pixels = get_tex.get_pixels_array()
        # print('get_tex',get_tex.unique_id)
        # print('get_tex',get_tex.tex_id)

        
        # Create GPU texture from image (preferred)
        try:
            arr = np.frombuffer(pixels, dtype=np.uint8).astype(np.float32) / 255.0
            # arr = np.frombuffer(pixels, dtype=np.uint8)
            # 确保形状正确
            if arr.size != width * height * 4:
                arr = arr.reshape((height, width, 4)).ravel()
            
            # ✅ 使用 FLOAT 格式创建 Buffer
            buf = gpu.types.Buffer('FLOAT', (width * height * 4), arr)
            # buf = gpu.types.Buffer('FLOAT', width * height * 4, arr.tolist())
            
            # 创建 GPUTexture
            gpu_tex = gpu.types.GPUTexture(
                size=(width, height),
                format='RGBA8',
                data=buf
            )
            
            # 保存引用
            key = 0
            Renderer._texture_cache[key] = gpu_tex
            # print('self._font_tex',self._font_tex)
            self._font_tex = gpu_tex
            # self._font_tex = Renderer._texture_cache[key]
            # print('self._font_tex',self._font_tex)
            # self._font_texture = key

            # inform ImGui of texture id mapping
            # try:
            io.fonts.python_set_texture_id(0) 
            # except Exception:
            #     try:
            #         io.fonts.texture_id = key
            #     except Exception:
            #         pass

            if Renderer.debug:
                print("refresh_font_texture_ex: uploaded font atlas, size:", width, height)
            return gpu_tex

        except Exception as e:
            print("refresh_font_texture_ex: exception during GPU texture creation:", e)
            return

    # ---------------- main render ----------------
    def render(self, draw_data: imgui.ImDrawData):
        """
        draw_data is imgui draw lists. This function translates those lists into
        Blender GPU draw calls via batch_for_shader.
        """
        if self._bl_shader is None:
            return

        io = self.io
        shader = self._bl_shader

        # framebuffer size
        try:
            display_width, display_height = io.display_size
            fb_width = int(display_width * io.display_framebuffer_scale[0])
            fb_height = int(display_height * io.display_framebuffer_scale[1])
        except Exception:
            return

        if fb_width == 0 or fb_height == 0:
            return

        # scale clip rects if method exists
        try:
            draw_data.scale_clip_rects(io.display_framebuffer_scale)
        except Exception:
            pass

        # set GPU state
        last_blend = gpu.state.blend_get()
        last_depth = gpu.state.depth_test_get()
        gpu.state.blend_set('ALPHA')
        gpu.state.depth_test_set('LESS_EQUAL')
        gpu.state.program_point_size_set(False)
        gpu.state.scissor_test_set(True)

        # ensure font uploaded
        # print(1,hash(self._font_tex))
        # try:
        #     self.refresh_font_texture_ex()
        #     # print(2,hash(self._font_tex))
        # except Exception:
        #     pass
        # print()
        from .imgui_setup.imgui_global import GlobalImgui
        if not getattr(GlobalImgui.get(),'main_window',False):
            # print('没有主窗口')
            self.refresh_font_texture_ex()
        # print('self._font_tex.width',self._font_tex.width)
        # if self._font_tex is None:
        #     if Renderer.debug:
        #         print("Lazy loading font texture...")
        #     self.refresh_font_texture_ex()
        
        # 双重检查：如果刷新后还是 None，说明真的出错了，跳过本次渲染避免报错
        # if self._font_tex is None:
        #     self._restore_gpu_state(last_blend, last_depth) # 记得恢复状态
        #     return
        # 确保 ImGui 知道当前的字体纹理 ID (防止 ImGui 内部重置)
        # if self.io.fonts.texture_id != self._font_texture:
        #     self.io.fonts.texture_id = self._font_texture


        # bind shader and projection
        try:
            shader.bind()
            shader.uniform_float("ProjMtx", self._create_projection_matrix(display_width, display_height))
        except Exception as e:
            if Renderer.debug:
                print("shader bind/uniform failed:", e)
            return

        # iterate cmd lists
        for commands in draw_data.cmd_lists:
            # parse index buffer
            try:
                num_indices = int(commands.idx_buffer.size())
                addr_idx = commands.idx_buffer.data_address()
                idx_bytes_len = num_indices * imgui.INDEX_SIZE
                idx_bytes = ctypes.string_at(addr_idx, idx_bytes_len)
                if imgui.INDEX_SIZE == 2:
                    idx_dtype = np.uint16
                else:
                    idx_dtype = np.uint32
                idx_buffer_np = np.frombuffer(idx_bytes, dtype=idx_dtype).astype(np.uint32)
            except Exception as e:
                if Renderer.debug:
                    print("parse idx_buffer failed:", e)
                continue

            # parse vertex buffer
            try:
                num_vertices = int(commands.vtx_buffer.size())
                addr_vtx = commands.vtx_buffer.data_address()
                bytes_per_vert = int(imgui.VERTEX_SIZE)  # e.g. 20
                total_bytes = num_vertices * bytes_per_vert
                raw_bytes = ctypes.string_at(addr_vtx, total_bytes)
                floats = np.frombuffer(raw_bytes, dtype=np.float32)
                vtx_floats = floats.reshape((num_vertices, imgui.VERTEX_SIZE // 4))
                vertices = vtx_floats[:, 0:2].astype(np.float32, copy=False)
                uvs = vtx_floats[:, 2:4].astype(np.float32, copy=False)
                # packed color at float index 4 -> reinterpret as uint32
                packed_color = vtx_floats[:, 4].view(np.uint32)
                r = (packed_color & 0xFF).astype(np.float32) / 255.0
                g = ((packed_color >> 8) & 0xFF).astype(np.float32) / 255.0
                b = ((packed_color >> 16) & 0xFF).astype(np.float32) / 255.0
                a = ((packed_color >> 24) & 0xFF).astype(np.float32) / 255.0
                colors = np.stack([r, g, b, a], axis=1).astype(np.float32, copy=False)
            except Exception as e:
                if Renderer.debug:
                    print("parse vtx_buffer failed:", e)
                continue

            idx_offset = 0
            for command in commands.cmd_buffer:
                try:
                    x, y, z, w = command.clip_rect
                    gpu.state.scissor_set(int(x), int(fb_height - w), int(z - x), int(w - y))
                except Exception:
                    # skip invalid clip rect
                    continue

                # resolve texture id robustly
                current_texture_id = None
                try:
                    if hasattr(command, "tex_ref") and command.tex_ref is not None:
                        try:
                            current_texture_id = command.tex_ref.get_tex_id()
                        except Exception:
                            try:
                                current_texture_id = int(command.tex_ref)
                            except Exception:
                                current_texture_id = None
                    if current_texture_id is None and hasattr(command, "texture_id"):
                        try:
                            current_texture_id = int(command.texture_id)
                        except Exception:
                            current_texture_id = None
                except Exception:
                    current_texture_id = None

                # map to cached GPU texture
                gpu_tex = None
                # print('current_texture_id',current_texture_id,int(current_texture_id))
                try:
                    if current_texture_id is None or int(current_texture_id) == 0:
                        gpu_tex = self._font_tex
                    else:
                        gpu_tex = Renderer._texture_cache.get(current_texture_id, None) or Renderer._texture_cache.get(int(current_texture_id), None)
                        if gpu_tex is None:
                            gpu_tex = self._font_tex
                except Exception:
                    gpu_tex = self._font_tex

                if gpu_tex is None:
                    # skip draw if no texture
                    idx_offset += getattr(command, "elem_count", 0)
                    continue

                # get indices for this draw
                elem_count = getattr(command, "elem_count", 0)
                indices = idx_buffer_np[idx_offset: idx_offset + elem_count].astype(np.uint32, copy=False)

                # batch and draw
                try:
                    batch = batch_for_shader(shader, 'TRIS', {
                        "Position": vertices,
                        "UV": uvs,
                        "Color": colors
                    }, indices=indices)
                    # bind sampler (some blender versions accept GPUTexture directly)
                    try:

                        shader.uniform_sampler("Texture", gpu_tex)
                    except Exception:
                        # ignore if binding fails here; some versions use different API
                        pass
                    batch.draw(shader)
                except Exception as e:
                    if Renderer.debug:
                        print("batch.draw failed:", e)

                idx_offset += elem_count

        # restore state (best-effort)
        try:
            gpu.state.blend_set('ALPHA')
            gpu.state.scissor_test_set(False)
        except Exception:
            pass

    # ---------------- projection matrix ----------------
    def _create_projection_matrix(self, width, height):
        """
        Column-major or row-major depends on Blender expectation.
        This layout matches the shader multiplication in create_imgui_shader.
        """
        ortho_projection = (
            2.0 / width, 0.0, 0.0, 0.0,
            0.0, 2.0 / -height, 0.0, 0.0,
            0.0, 0.0, -1.0, 0.0,
            -1.0, 1.0, 0.0, 1.0
        )
        return ortho_projection
