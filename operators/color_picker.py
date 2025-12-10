import copy
import time
import bpy

from ..utils.utils import get_brush_color_based_on_mode, get_prefs

from ..widget import color_bar, color_palette, colorpicker, get_wheeL_tri, picker_switch_button
from ..widget import colors, color_palette_size,color_hsv,color_rgb,color_palette_dict,color_tmp
from ..operators.base_ops import BaseDrawCall
from imgui_bundle import imgui

class Imgui_Color_Picker_Imgui(bpy.types.Operator, BaseDrawCall):
    bl_idname = "imgui.color_picker"
    bl_label = "color picker"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if bpy.context.mode == 'SCULPT' and bpy.context.tool_settings.sculpt.brush == bpy.data.brushes['Paint']:
            sculpt = True
            return sculpt
        if context.area.type == 'IMAGE_EDITOR':
            if context.area.spaces.active.ui_mode=='PAINT':
                image_paint=True
                return image_paint
        if (context.mode in {'PAINT_VERTEX', 'PAINT_TEXTURE', 'PAINT_GPENCIL', 'VERTEX_GPENCIL', }) and context.area.type == 'VIEW_3D':
            return True
        return False
    def draw(self, context: bpy.types.Context):
        a = time.time()

        self.cover = False
        self.cover_style_editor = False
        # 展示一个 ImGui 测试窗口
        wf = imgui.WindowFlags_

        window_flags = wf.no_title_bar | wf.no_resize | wf.no_scrollbar | wf.always_auto_resize

        imgui.set_next_window_pos(
            imgui.ImVec2(self.show_window_pos[0] - 127 - imgui.get_style().indent_spacing * 0.5,
                         context.region.height - self.show_window_pos[1] - 129 - 10))
        _mian_show,_mian_x=imgui.begin("VRC", self.main_window[0], window_flags)

        # imgui.text("")
        start_pos = imgui.ImVec2(imgui.get_cursor_pos().x, +imgui.get_cursor_pos().y+ 10)
        imgui.set_cursor_pos(start_pos)
        im_cf = imgui.ColorEditFlags_
        if get_prefs().picker_switch:
            picker_type=im_cf.picker_hue_wheel
        else:
            picker_type=im_cf.picker_hue_bar
        misc_flags = picker_type | im_cf.no_options | im_cf.input_rgb | im_cf.no_alpha | im_cf.no_side_preview | im_cf.no_label
        color = get_brush_color_based_on_mode()
        if imgui.is_mouse_clicked(0):
            self.pre_color = copy.deepcopy(color)

        colorpicker_changed, picker_pos, picker_pos2, wheel_center = colorpicker('##aa', color, misc_flags, self)
        imgui.same_line()
        imgui.begin_group()
        global color_hsv, color_rgb, color_tmp, color_palette_dict
        color_bar_changed = color_bar(color, color_hsv, color_rgb, self)
        if imgui.is_mouse_down(0):
            if color_bar_changed:
                color_tmp = copy.deepcopy(color)
            id = imgui.get_current_context().hovered_id
            if hasattr(color_palette_dict, f'c{id}'):
                self.color_palette.insert(0, copy.deepcopy(color_palette_dict[id]))
        elif imgui.is_mouse_released(0):
            if colorpicker_changed:
                self.color_palette.insert(0, copy.deepcopy(color))

        if imgui.is_mouse_released(0):
            if color_tmp != [] and not colorpicker_changed:

                ids = [imgui.get_id(i) for i in ['H ', 'S ', 'V ', 'R ', 'G ', 'B ']]
                if imgui.get_current_context().hovered_id in ids:
                    self.color_palette.insert(0, copy.deepcopy(color_tmp))
        color_palette('##color_palette', color, self.backup_color, self.pre_color, self.color_palette)
        imgui.end_group()
        picker_switch_button(' ##1')
        start_pos = imgui.ImVec2(imgui.get_cursor_pos().x, imgui.get_cursor_pos().y -15)
        imgui.set_cursor_pos(start_pos)
        imgui.text('')
        # imgui.show_demo_window()
        self.track_any_cover()
        if imgui.is_item_hovered():
            imgui.set_keyboard_focus_here(-1)

        imgui.end()

    def invoke(self, context, event):
        self.cover = False
        self.cover_style_editor = False
        self.show_window_pos = (event.mouse_region_x, event.mouse_region_y)
        self.show_window_imgui = False
        self.verts = get_wheeL_tri(self.show_window_pos)
        self.backup_color = copy.deepcopy(get_brush_color_based_on_mode())
        self.area=context.area
        self.pre_color = copy.deepcopy(self.backup_color)
        global colors, color_palette_size
        if len(colors) > color_palette_size:
            del colors[color_palette_size:]
        try:
            self.color_palette=[list(c) for c in bpy.context.scene['color_picker_col']]
        except:
            self.color_palette = colors
        self.init_imgui(context)

        context.window_manager.modal_handler_add(self)

        return {'RUNNING_MODAL'}
    def refresh(self):
        for area in bpy.context.screen.areas:
            if area.type in ['VIEW_3D','IMAGE_EDITOR']:
                area.tag_redraw()
    def modal(self, context, event):
        if event.type == 'SPACE' and event.value == 'RELEASE':
            self.call_shutdown_imgui()
            self.refresh()
            return {'FINISHED'}
        if event.type == 'Z' and event.value == 'RELEASE':
            self.call_shutdown_imgui()
            self.refresh()
            return {'FINISHED'}
        a = time.time()
        if context.area:
            context.area.tag_redraw()

        gx, gy = event.mouse_x, event.mouse_y

        # —— 动态查找当前鼠标在 screen 哪个 region 上 —— 
        region = None
        for area in context.window.screen.areas:
            for r in area.regions:
                # r.x, r.y 是 region 在窗口中的左下角坐标
                if (gx >= r.x and gx <= r.x + r.width
                and gy >= r.y and gy <= r.y + r.height):
                    region = r
                    break
            if region:
                break

        # 找不到就透传，让 Blender 处理
        if region is None:
            return {'PASS_THROUGH'}
        if region:
            region.tag_redraw()
        # —— 计算区域内坐标 —— 
        mx = gx - region.x
        my = gy - region.y
        self.mpos=(gx,my)
        # （如果 ImGui 需要底部为 0，向上为正，这里就不翻转——mouse_region_y 已经是底部起算）
        # print(region)
        # —— 越界检测（可选） —— 
        if mx < 0 or mx > region.width or my < 0 or my > region.height:
            return {'PASS_THROUGH'}
        if event.type in {"ESC",'WINDOW_DEACTIVATE'}:
            self.call_shutdown_imgui()
            self.refresh()
            return {'FINISHED'}
        if event.type in {'RIGHTMOUSE'}:
            self.call_shutdown_imgui()
            self.refresh()
            return {'FINISHED'}
        if event.type == 'X' and event.value == 'RELEASE':
            from ..utils import exchange_brush_color_based_on_mode
            exchange_brush_color_based_on_mode(exchange=True)

        if region:
            # region = context.region
            pass
        else:
            self.call_shutdown_imgui()
            self.refresh()
            return {'FINISHED'}
        self.poll_mouse(context, event)
        if not self.cover:
            return {"PASS_THROUGH"}
        self.poll_events(context, event)

        return {"RUNNING_MODAL"}
