import math
import numpy as np
from typing import Optional, Dict, Tuple
import bpy
from imgui_bundle import imgui
from imgui_bundle import ImVec4
from ..imgui_global import GlobalImgui
from ...operators.base_ops import BaseDrawCall


class SculptwheelImGui(bpy.types.Operator, BaseDrawCall):
    """Blender中的圆形菜单轮盘 - ImGui版本 (修复 AttributeError: mpos)"""
    
    bl_idname = "imgui.spacebar_sclupt"
    bl_label = "Sculptwheel Menu"
    bl_options = {'REGISTER'}
    
    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == 'MESH' and context.object.mode == 'SCULPT'
    
    # ==================== 初始化 ====================
    
    def setup_params(self):
        """设置参数"""
        self.radius = 80
        self.size = self.radius * 2 + 40
        self.button_size = 40
        
        self.button_infos = [
            ('mesh_sculpt_inflate.png', 'mesh_sculpt_inflate', 'Inflate/Deflate'),
            ('mesh_sculpt_grab.png', 'mesh_sculpt_grab', 'Grab'),
            ('mesh_sculpt_elastic_grab.png', 'mesh_sculpt_elastic_grab', 'Elastic Grab'),
            ('mesh_sculpt_slide_relax.png', 'mesh_sculpt_slide_relax', 'Relax Slide'),
            ('Box_Mask_icon.png', 'mask_box', 'Box Mask'),
            ('mask_bursh.png', 'mask_brush', 'Mask Brush'),
        ]
        self.n_buttons = len(self.button_infos)
        
        # 布局与检测逻辑 (复刻 Qt)
        self._layout_start_angle = -math.pi / 2 
        self._layout_span = math.pi              
        self._layout_step = self._layout_span / (self.n_buttons - 1) if self.n_buttons > 1 else 0
        
        if self.n_buttons < 2:
            self.total_slots = 1
            self._detect_step = 0
            self._detect_start = 0
        else:
            unique_slots = (self.n_buttons - 2) * 2 + 2
            self.total_slots = unique_slots * 2
            self._detect_step = (2 * math.pi) / self.total_slots
            self._detect_start = self._layout_start_angle - self._detect_step

        self._highlighted_idx: Optional[int] = None
        self._button_rects: Dict[int, Tuple[tuple, tuple]] = {}
        
        self.show_window_pos = (0, 0)
        self.main_window = [True]
        self.cover = False
        self.cover_style_editor = False
    
    def load_icon(self):
        self.textures = {}
        for icon, name, _ in self.button_infos:
            self.textures[name] = self.load_icon_texture(icon)
        textures=getattr(GlobalImgui.get(),'textures',None)
        if not textures:
            GlobalImgui.get().textures={}
            GlobalImgui.get().textures['faceset_from_visible']=self.load_icon_texture("hide_off.png")
            GlobalImgui.get().textures['faceset_from_edit']=self.load_icon_texture("editmode_hlt.png")
            GlobalImgui.get().textures['edit_to_paint_with_a']=self.load_icon_texture("armature_data.png")
        self.faceset_from_visible=self.load_icon_texture("hide_off.png")
        self.faceset_from_edit=self.load_icon_texture("editmode_hlt.png")
        self.edit_to_paint_with_a=self.load_icon_texture("armature_data.png")
    # ==================== 几何计算 ====================
    
    def get_button_position(self, button_idx: int) -> np.ndarray:
        angle = self._layout_start_angle + self._layout_step * button_idx
        offset_x = math.cos(angle) * self.radius
        offset_y = math.sin(angle) * self.radius
        return np.array([offset_x, offset_y], dtype=np.float32)
    
    def calculate_highlighted_button(self, mouse_pos_global: np.ndarray, center_pos_global: np.ndarray) -> Optional[int]:
        dx = mouse_pos_global[0] - center_pos_global[0]
        dy = mouse_pos_global[1] - center_pos_global[1]
        
        angle = math.atan2(dy, dx)
        rel = (angle - self._detect_start) % (2 * math.pi)
        slot = int(rel / self._detect_step)
        candidate_idx = slot // 2
        
        if 0 <= candidate_idx < self.n_buttons:
            return candidate_idx
        return None
    
    # ==================== 渲染 ====================
    
    def draw(self, context: bpy.types.Context):
        self.cover = False
        self.cover_style_editor = False
        image_btn=GlobalImgui.get().btn_image
        text_btn=GlobalImgui.get().btn_text
        wf = imgui.WindowFlags_
        window_flags = (wf.no_title_bar | wf.no_resize | wf.no_scrollbar | 
                        wf.always_auto_resize | wf.no_move | wf.no_background)
        
        win_x = self.show_window_pos[0] - self.size / 2
        win_y = context.region.height - self.show_window_pos[1] - self.size / 2
        
        imgui.set_next_window_pos(imgui.ImVec2(win_x, win_y))
        
        _main_show, _main_x = imgui.begin("Sculptwheel", self.main_window[0], window_flags)
        
        if _main_show:
            self._draw_wheel_content()
        
        self.track_any_cover()
        imgui.end()
        imgui.set_next_window_pos(imgui.ImVec2(win_x-20, win_y))
        window_flags = (wf.no_title_bar | wf.no_resize | wf.no_scrollbar | 
                        wf.always_auto_resize | wf.no_move | wf.no_background)
        _main_show, _main_x = imgui.begin("Sculptbuttons", self.main_window[0], window_flags)
        # ========== 添加ImGui按钮 ==========
        imgui.set_cursor_pos(imgui.ImVec2(0, 0))

        image_btn.new("##faceset_from_visible", 
                            self.faceset_from_visible,tp='从视图可见顶点创建面组')
        imgui.same_line(spacing=0)
        image_btn.new("##faceset_from_edit", 
                            self.faceset_from_edit,tp='从选中的顶点创建面组')
        imgui.same_line(spacing=0)
        image_btn.new("##edit_to_paint_with_a", 
                            self.edit_to_paint_with_a,tp='选中骨架,并进入权重绘制')

        imgui.separator()
        text_btn.new_toggle("拓扑##use_automasking_topology", close=False,
                                                condition=self.sculpt.use_automasking_topology,
                            tp='全局:根据拓扑自动遮罩')
        imgui.same_line(spacing=0)
        text_btn.new("光滑##smooth_mask", close=False,
                            tp='光滑遮罩')
        text_btn.new_toggle("面组##use_automasking_face_sets",close=False,
                                                condition=self.sculpt.use_automasking_face_sets, 
                            tp='全局:根据面组自动遮罩')
        text_btn.new_toggle("面组边界##use_automasking_boundary_face_sets", close=False,
                                                condition=self.sculpt.use_automasking_boundary_face_sets,
                            tp='全局:面组边界自动遮罩')
        text_btn.new_toggle("网格边界##use_automasking_boundary_edges",close=False,
                                                condition=self.sculpt.use_automasking_boundary_edges, 
                            tp='全局:网格边界自动遮罩')

        self.track_any_cover()
        imgui.end()
        
    
    def _draw_wheel_content(self):
        # 1. 锁定绘图原点
        p = imgui.get_cursor_screen_pos()
        origin = np.array((p.x, p.y))
        
        # 2. 撑开窗口
        imgui.dummy(imgui.ImVec2(self.size*2, self.size*2))
        
        draw_list = imgui.get_window_draw_list()
        center = origin + np.array([self.size / 2, self.size / 2])
        
        io = imgui.get_io()
        mouse_pos = np.array((io.mouse_pos.x, io.mouse_pos.y))
        self._highlighted_idx = self.calculate_highlighted_button(mouse_pos, center)
        
        # 绘制
        circle_color = imgui.get_color_u32(ImVec4(0.3, 0.3, 0.3, 0.8))
        draw_list.add_circle(tuple(center), self.radius, circle_color, thickness=4)
        
        # ray_color = imgui.get_color_u32(ImVec4(1.0, 0.8, 0.0, 0.8))
        # draw_list.add_line(tuple(center), tuple(mouse_pos), ray_color, thickness=2)
        
        self._button_rects.clear()
        for i in range(self.n_buttons):
            self._draw_button(i, draw_list, center)
        # ========== 最后绘制所有tooltip，确保在最上层 ==========
        for i in range(self.n_buttons):
            if i == self._highlighted_idx:
                offset = self.get_button_position(i)
                btn_center = center + offset
                tooltip = self.button_infos[i][2]
                self._draw_tooltip(draw_list, btn_center, tooltip)
        

    def _draw_button(self, idx: int, draw_list :imgui.ImDrawList, center_pos: np.ndarray):
        offset = self.get_button_position(idx)
        btn_center = center_pos + offset
        is_highlighted = (idx == self._highlighted_idx)
        
        if is_highlighted:
            bg_col = imgui.get_color_u32(ImVec4(0.0, 0.47, 0.82, 1.0))
            border_col = imgui.get_color_u32(ImVec4(1.0, 1.0, 1.0, 1.0))
        else:
            bg_col = imgui.get_color_u32(ImVec4(0.11, 0.11, 0.11, 0.9))
            border_col = imgui.get_color_u32(ImVec4(0.3, 0.3, 0.3, 1.0))
            
        hs = self.button_size / 2
        p_min = (btn_center[0] - hs, btn_center[1] - hs)
        p_max = (btn_center[0] + hs, btn_center[1] + hs)
        
        self._button_rects[idx] = (p_min, p_max)
        
        draw_list.add_rect_filled(p_min, p_max, bg_col, rounding=20.0)
        draw_list.add_rect(p_min, p_max, border_col, rounding=20.0, thickness=2.0)


        # 获取纹理 ID 和文字标签
        icon_key = self.button_infos[idx][1]
        texture_id = self.textures.get(icon_key)
        label = self.button_infos[idx][1].replace('mesh_sculpt_', '').replace('mask_', '')[:4]
        text_col = imgui.get_color_u32(ImVec4(1.0, 1.0, 1.0, 1.0))

        # ================== 图标/文字 绘制决策逻辑 ==================
    
        if texture_id is not None:
            # ** A. 绘制图标 (有图标时) **
            ICON_SIZE_RATIO = 0.8  # 图标可以更大一点，因为它独占空间
            icon_size = self.button_size * ICON_SIZE_RATIO
            icon_hs = icon_size / 2
            
            # 图标中心点就是按钮中心点
            icon_center_x = btn_center[0] 
            icon_center_y = btn_center[1]
            
            icon_p_min = (icon_center_x - icon_hs, icon_center_y - icon_hs)
            icon_p_max = (icon_center_x + icon_hs, icon_center_y + icon_hs)
            
            uv_min_imgui = imgui.ImVec2(0, 0) # 纹理左上角
            uv_max_imgui = imgui.ImVec2(1, 1) # 纹理右下角
            # 绘制图标 (完美居中)
            draw_list.add_image(
                imgui.ImTextureRef(texture_id),
                icon_p_min,
                icon_p_max,
                uv_min_imgui, # 使用 ImVec2
                uv_max_imgui, # 使用 ImVec2
                imgui.get_color_u32(ImVec4(1.0, 1.0, 1.0, 1.0))
            )
            
            # ⚠️ 注意：这里不再执行绘制文字标签的代码
            
        else:
            # ** B. 绘制文字标签 (无图标时，作为备选) **
            text_size = imgui.calc_text_size(label)
            
            # 文字中心点就是按钮中心点
            text_pos = (
                btn_center[0] - text_size.x / 2, 
                btn_center[1] - text_size.y / 2
            )
            
            # 绘制文字标签
            draw_list.add_text(text_pos, text_col, label)
            
        # =========================================================
        
        # label = self.button_infos[idx][1].replace('mesh_sculpt_', '').replace('mask_', '')[:4]
        # text_col = imgui.get_color_u32(ImVec4(1.0, 1.0, 1.0, 1.0))
        # text_size = imgui.calc_text_size(label)
        # text_pos = (btn_center[0] - text_size.x / 2, btn_center[1] - text_size.y / 2)
        # draw_list.add_text(text_pos, text_col, label)
        
        # if is_highlighted:
        #     tooltip = self.button_infos[idx][2]
        #     self._draw_tooltip(draw_list, btn_center, tooltip)

    def _draw_tooltip(self, draw_list, pos: np.ndarray, text: str):
        tip_pos = (pos[0] + 30, pos[1] - 10)
        bg = imgui.get_color_u32(ImVec4(0.2, 0.2, 0.2, 0.9))
        txt = imgui.get_color_u32(ImVec4(1.0, 1.0, 1.0, 1.0))
        sz = imgui.calc_text_size(text)
        pad = 5
        draw_list.add_rect_filled(
            (tip_pos[0] - pad, tip_pos[1] - pad),
            (tip_pos[0] + sz.x + pad, tip_pos[1] + sz.y + pad),
            bg, rounding=4
        )
        draw_list.add_text(tip_pos, txt, text)

    # ==================== 事件处理 ====================
    
    def invoke(self, context, event):
        self.sculpt=bpy.context.scene.tool_settings.sculpt
        self.setup_params()
        self.show_window_pos = (event.mouse_region_x, event.mouse_region_y)
        self.region , self.mpos = self._get_current_region_and_mpos(context, event)
        self.area = context.area
        # self.region = None
        
        # 【修复1】: 初始化 mpos，防止 invoke 期间调用出错（虽然后面 modal 会更新）
        # self.mpos = (0, 0)
        
        self.init_imgui(context)
        self.load_icon()
        
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}
    
    def modal(self, context, event):
        from ..imgui_global import GlobalImgui
        if GlobalImgui.get().close_ui:
            self.call_shutdown_imgui()
            self.refresh()
            return {'FINISHED'}
        # 1. 退出检测
        if event.type in {'SPACE', 'Z'} and event.value == 'RELEASE':
            if self._highlighted_idx is not None:
                self._trigger_button(self._highlighted_idx)
            self.call_shutdown_imgui()
            return {'FINISHED'}
        
        if event.type == 'ESC':
            self.call_shutdown_imgui()
            return {'FINISHED'}

        context.area.tag_redraw()

        # ==================== 【修复2】：重新加入 Region 查找与 mpos 计算逻辑 ====================
        # 这个逻辑块非常重要，poll_mouse 依赖 self.mpos 和 self.region
        
        gx, gy = event.mouse_x, event.mouse_y
        
        # 找到当前鼠标所在的区域 (复制自你的原始代码)
        region = self.region
        # current_area = None
        # for area in context.window.screen.areas:
        #     for r in area.regions:
        #         if (gx >= r.x and gx <= r.x + r.width and
        #             gy >= r.y and gy <= r.y + r.height):
        #             region = r
        #             current_area = area
        #             break
        #     if region:
        #         break
        
        # # 如果找不到 region 或者 area 不匹配，视作 pass through
        # if region is None:
        #      # 如果鼠标移出了 Blender 窗口，可能需要做保护，这里简单返回
        #      return {'PASS_THROUGH'}

        # # 首次获取到 region 时赋值
        # if self.region is None:
        #     self.region = region
            
        # 计算区域内的鼠标局部坐标 (Local Coordinates)
        # poll_mouse 内部使用 self.mpos[0] 和 self.mpos[1]
        mx = gx - region.x
        my = gy - region.y
        self.mpos = (mx, my)
        # ===================================================================================

        # 2. 鼠标点击触发 (左键)
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            if self._highlighted_idx is not None:
                self._trigger_button(self._highlighted_idx)
                self.call_shutdown_imgui()
                return {'FINISHED'}
            # else:
            #     self.call_shutdown_imgui()
            #     return {'FINISHED'}
        
        # 3. ImGui 事件透传 (现在 self.mpos 和 self.region 都有值了，不会报错)
        self.poll_mouse(context, event)
        self.poll_events(context, event)
        
        return {"RUNNING_MODAL"}

    def _trigger_button(self, idx: int):
        name = self.button_infos[idx][1]
        print(f"Triggering: {name}")
        
        if name == 'mesh_sculpt_inflate':
            bpy.ops.brush.asset_activate(
                asset_library_type='ESSENTIALS', relative_asset_identifier="brushes\\essentials_brushes-mesh_sculpt.blend\\Brush\\Inflate/Deflate")
        elif name == 'mesh_sculpt_grab':
            bpy.ops.brush.asset_activate(
                asset_library_type='ESSENTIALS', relative_asset_identifier="brushes\\essentials_brushes-mesh_sculpt.blend\\Brush\\Grab")
        elif name == 'mesh_sculpt_elastic_grab':
            bpy.ops.brush.asset_activate(
                asset_library_type='ESSENTIALS', relative_asset_identifier="brushes\\essentials_brushes-mesh_sculpt.blend\\Brush\\Elastic Grab")
        elif name == 'mesh_sculpt_slide_relax':
            bpy.ops.brush.asset_activate(
                asset_library_type='ESSENTIALS', relative_asset_identifier="brushes\\essentials_brushes-mesh_sculpt.blend\\Brush\\Relax Slide")
        elif name == 'mask_box':
            bpy.ops.wm.tool_set_by_id(name="builtin.box_mask", space_type='VIEW_3D')
        elif name == 'mask_brush':
            bpy.ops.wm.tool_set_by_id(name="builtin_brush.mask", space_type='VIEW_3D')