import bpy
import time
from imgui_bundle import imgui
from .selectable_input import selectable_input
from .imgui_global import GlobalImgui
from ..utils.mesh import has_shape_key
from ..utils.scene import get_all_collections

selected = False
image_size=imgui.ImVec2(20.0, 20.0)
def set_toggle_style_color(name, texture_id, condition, close=True,image_size=image_size, tp=''):
    """
    Draw a toggle-like image button with different colors depending on condition.
    push 3 colors then pop 3 colors to keep ImGui stack balanced.
    """
    button_color = imgui.ImVec4(0.33, 0.33, 0.33, 1)
    button_active_color = imgui.ImVec4(71/255.0, 114/255.0, 179/255.0, 1)
    if condition:
        imgui.push_style_color(imgui.Col_.button.value, button_active_color)
        imgui.push_style_color(imgui.Col_.button_hovered.value, button_active_color)
        imgui.push_style_color(imgui.Col_.button_active.value, button_active_color)
    else:
        imgui.push_style_color(imgui.Col_.button.value, button_color)
        imgui.push_style_color(imgui.Col_.button_hovered.value, button_color)
        imgui.push_style_color(imgui.Col_.button_active.value, button_color)

    # use GlobalImgui image_btn; keep original calling pattern
    try:
        if GlobalImgui.get().btn_image.new(name, texture_id, close=close,image_size=image_size, tp=tp):
            pass
    except Exception:
        # be tolerant if image_btn is missing or new() fails
        try:
            _ = GlobalImgui.get().btn_image
        except Exception:
            pass

    # pop exactly 3 colors
    imgui.pop_style_color()
    imgui.pop_style_color()
    imgui.pop_style_color()


def shapkey_widget(self):
    """
    Robust version of your original shapekey_widget.
    - Safe access to GlobalImgui.get().item_current_idx
    - Protect against empty collections / missing properties
    """
    from .imgui_global import GlobalImgui
    gp=GlobalImgui.get()
    window_padding = imgui.get_style().window_padding
    item_spacing = imgui.get_style().item_spacing
    item_inner_spacing = imgui.get_style().item_inner_spacing
    indent_spacing = imgui.get_style().indent_spacing
    frame_padding = imgui.get_style().frame_padding
    global selected

    obj = bpy.context.object
    self.obj = obj
    if self.obj is None or self.obj.type != 'MESH':
        return

    imgui.separator()
    imgui.set_next_item_open(True, cond=imgui.Cond_.once)

    if imgui.collapsing_header("形态键"):
        imgui.begin_group()

        # init persistent attributes for this UI object
        if not hasattr(self, "child_window_height"):
            self.child_window_height = 200  # 初始高度
        if not hasattr(self, "is_dragging_resizer_sk"):
            self.is_dragging_resizer_sk = False
        if not hasattr(self, "drag_sk_start_mouse_y"):
            self.drag_sk_start_mouse_y = 0
        if not hasattr(self, "start_height_sk"):
            self.start_height_sk = 200

        w = imgui.get_window_size().x - 25 - indent_spacing*2 - item_spacing.x - frame_padding.x - window_padding.x
        Scroll_width = w if w > 230 else 230

        collections = get_all_collections(bpy.context.scene.collection)
        items = ['##Scene Collection' if cl.name == 'Scene Collection' else cl.name for cl in collections]

        if not hasattr(self, 'select_combo_filter'):
            self.select_combo_filter = imgui.TextFilter()
        if obj.as_pointer() not in gp.obj_sync_col_index:
            gp.obj_sync_col_index[obj.as_pointer()]=0
        # Safely get item_current_idx from GlobalImgui
        if obj.as_pointer() in gp.obj_sync_col_index:
            idx=gp.obj_sync_col_index[obj.as_pointer()]
        # idx = getattr(gp, "item_current_idx", 0)
        # Ensure idx is int and within bounds
        try:
            idx = int(idx)
        except Exception:
            idx = 0
        if not items:
            combo_preview_value = ''
        else:
            if idx < 0 or idx >= len(items):
                idx = 0
            combo_preview_value = items[idx]

        imgui.text("同步集合")
        
        text_len = imgui.calc_text_size('同步集合').x

        imgui.same_line()
        try:
            set_toggle_style_color("##solo_active_sk",
                                   self.btn_solo_active_sk,
                                   bpy.context.object.show_only_shape_key,
                                close=False, tp='单独显示形态键')
        except Exception:
            pass

        imgui.same_line()
        try:
            set_toggle_style_color("##sk_edit_mode",
                                   self.btn_sk_edit_mode,
                                   bpy.context.object.use_shape_key_edit_mode, 
                                   close=False,tp='形态键编辑模式')
        except Exception:
            pass


        imgui.same_line()
        imgui.set_next_item_width(Scroll_width - text_len -20- 40 -40- item_spacing.x*2)

        # # Begin combo safely
        if imgui.begin_combo("##combo", combo_preview_value, imgui.ComboFlags_.no_arrow_button):
            if imgui.is_window_appearing():
                imgui.set_keyboard_focus_here()
                try:
                    self.select_combo_filter.clear()
                except Exception:
                    pass

            imgui.set_next_item_shortcut(imgui.Key.mod_ctrl | imgui.Key.f)
            # draw filter input
            try:
                self.select_combo_filter.draw("##Filter", -1)
            except Exception:
                pass

            # list items
            for n, it in enumerate(items):
                if it == '##Scene Collection':
                    continue
                try:
                    if self.select_combo_filter.pass_filter(it):
                        is_selected = (idx == n)
                        clicked, _ = imgui.selectable(it, is_selected)
                        if clicked:
                            # set new idx; store back into GlobalImgui
                            gp.obj_sync_col_index[obj.as_pointer()]=n
                            # gp.item_current_idx = n
                            idx = n
                        if is_selected:
                            imgui.set_item_default_focus()
                except Exception:
                    # protect from any per-item exceptions
                    pass

            # After selection, apply sync settings (if any)
            # Use safe read of current idx and items
            try:
                # sel_idx = getattr(gp, "item_current_idx", 0)
                if obj.as_pointer() in gp.obj_sync_col_index:
                    sel_idx=gp.obj_sync_col_index[obj.as_pointer()]
                else:sel_idx=0
                if items and 0 <= sel_idx < len(items):
                    selected_text = items[sel_idx]
                else:
                    selected_text = None
                if selected_text and selected_text != '##Scene Collection':
                    gp.obj_sync_col[obj.as_pointer()]=bpy.data.collections[f'{selected_text}']
                else:
                    gp.obj_sync_col[obj.as_pointer()]=None
                #     try:
                #         # try to set mio3sksync.syncs if addon exists
                #         self.obj.mio3sksync.syncs = bpy.data.collections.get(selected_text, None)
                #     except Exception:
                #         print('请安装mio shapekey插件 或者 collection 不存在')
                # else:
                    # try:
                    #     # clear syncs
                    #     self.obj.mio3sksync.syncs = None
                    # except Exception:
                    #     # ignore if property doesn't exist
                    #     pass
                    # if selected_text =='':
                    #     gp.get().obj_sync_col[self.qt_window.obj.as_pointer()]=None
                    # else:
                    #     gp.get().obj_sync_col[self.qt_window.obj.as_pointer()]=bpy.data.collections[f'{selected_text}']

            except Exception:
                pass

            imgui.end_combo()

        # 1. 检查鼠标是否悬停在 Combo 控件上
        if imgui.is_item_hovered():
            io = imgui.get_io()
            wheel_delta = io.mouse_wheel # 获取滚轮滚动值 (向上为正, 向下为负)
            
            if abs(wheel_delta) > 0.0:
                # 获取当前索引和总项目数
                # current_idx = getattr(gp, "item_current_idx", 0)
                if obj.as_pointer() in gp.obj_sync_col_index:
                    current_idx=gp.obj_sync_col_index[obj.as_pointer()]
                else:current_idx=0
                num_items = len(items) if items else 0
                new_idx = current_idx
                
                # 计算新的索引
                if wheel_delta > 0:
                    # 滚轮向上 -> 切换到前一个项目
                    new_idx = max(0, current_idx - 1)
                elif wheel_delta < 0:
                    # 滚轮向下 -> 切换到后一个项目
                    new_idx = min(num_items - 1, current_idx + 1)
                    
                if new_idx != current_idx:
                    # 2. 更新全局索引和同步值
                    # gp.item_current_idx = new_idx
                    if obj.as_pointer() in gp.obj_sync_col_index:
                        gp.obj_sync_col_index[obj.as_pointer()]=new_idx
                    
                    # 3. 立即应用你的同步逻辑 (这部分逻辑需要从你的 Combo 关闭后的同步逻辑中提取)
                    if items and 0 <= new_idx < len(items):
                        selected_text = items[new_idx]
                        if selected_text and selected_text != '##Scene Collection':
                            try:
                                # 尝试设置 mio3sksync.syncs
                                # self.obj.mio3sksync.syncs = bpy.data.collections.get(selected_text, None)
                                gp.obj_sync_col[obj.as_pointer()]=bpy.data.collections[f'{selected_text}']
                            except Exception as e:
                                print(f'切换值时出错: {e}')
                        else:
                             try:
                                # clear syncs
                                # self.obj.mio3sksync.syncs = None
                                 gp.obj_sync_col[obj.as_pointer()]=None
                             except Exception:
                                 pass
        # clear selection button
        # if getattr(gp, "item_current_idx", 0) != 0:
        if obj.as_pointer() in gp.obj_sync_col_index and gp.obj_sync_col_index[obj.as_pointer()] != 0:
            imgui.same_line()
            try:
                if gp.btn_image.new("##clear_sync_col",
                                                   self.btn_clear_all_sk_value,
                                                   image_size=image_size, tp='清除同步集合'):
                    gp.obj_sync_col_index[obj.as_pointer()]=0
                    # gp.item_current_idx = 0
                    try:
                        gp.obj_sync_col[obj.as_pointer()]=None
                        # self.obj.mio3sksync.syncs = None
                    except Exception:
                        print('请安装mio shapekey插件')
            except Exception:
                pass
        
        
        # scrolling child
        imgui.push_style_color(imgui.Col_.child_bg, GlobalImgui.get().child_bg if hasattr(GlobalImgui.get(), "child_bg") else imgui.ImVec4(0,0,0,0))
        visible = imgui.begin_child("ScrollableChild", imgui.ImVec2(Scroll_width, self.child_window_height), True)

        if visible:
            imgui.begin_group()

            if not hasattr(self, "shape_key_buf"):
                self.last_count = -1
                self.selected_index = -1

            # update shape keys list
            if has_shape_key(self.obj):
                try:
                    key_blocks = self.obj.data.shape_keys.key_blocks
                except Exception:
                    key_blocks = []

                if not hasattr(self, "sk") or self.last_count != len(key_blocks):
                    self.sk = key_blocks
                    self.shape_key_rows = []
                    for key in self.sk:
                        self.shape_key_rows.append({
                            "key": key,
                            "buf_name": [key.name],
                            "buf_value": [float(f"{key.value:.3f}")],
                        })
                    self.last_count = len(key_blocks)
                else:
                    self.sk = key_blocks  # keep synced
            else:
                self.sk = []
                self.shape_key_rows = []

            # sync index from Blender -> ImGui
            if has_shape_key(self.obj) and getattr(self.obj, "active_shape_key_index", -1) != getattr(self, "selected_index", -1):
                try:
                    self.selected_index = int(self.obj.active_shape_key_index)
                except Exception:
                    self.selected_index = -1

            # draw each row
            for idx_row, row in enumerate(self.shape_key_rows):
                label = f"key_{idx_row}"
                is_selected = (self.selected_index == idx_row)
                row["buf_name"][0] = row['key'].name
                row["buf_value"][0] = float(f"{row['key'].value:.3f}")

                try:
                    changed_name, changed_val, selected_flag, row["buf_name"][0] = selectable_input(
                        label,
                        is_selected,
                        row["buf_name"],
                        row["buf_value"],
                        width=Scroll_width,
                    )
                except Exception:
                    changed_name = changed_val = selected_flag = False

                if gp.obj_change_sk and is_selected:
                    # 0.5 代表居中 (0.0是顶部, 1.0是底部)
                    imgui.set_scroll_here_y(0.5)
                    # 滚动一次后立即关闭，避免后续帧重复滚动或覆盖滚动操作
                    gp.obj_change_sk = False


                if selected_flag:
                    self.selected_index = idx_row
                    try:
                        if self.obj.active_shape_key_index != idx_row:
                            self.obj.active_shape_key_index = idx_row
                    except Exception:
                        pass

                if changed_name:
                    try:
                        row['key'].name = row["buf_name"][0]
                    except Exception:
                        pass

                if changed_val:
                    try:
                        v = float(row["buf_value"][0])
                        v = max(min(v, row['key'].slider_max), row['key'].slider_min)
                        row["buf_value"][0] = float(f"{v:.3f}")
                        row['key'].value = row["buf_value"][0]
                    except Exception:
                        pass

            imgui.end_group()
        imgui.end_child()

        # pop child bg color
        try:
            imgui.pop_style_color()
        except Exception:
            pass

        # resizer (drag handle)
        resizer_height = 6
        cursor_pos_before_resizer = imgui.get_cursor_screen_pos()
        resizer_min = cursor_pos_before_resizer
        resizer_max = imgui.ImVec2(resizer_min.x + Scroll_width, resizer_min.y + resizer_height)

        imgui.set_cursor_screen_pos(resizer_min)
        imgui.invisible_button("resizer", imgui.ImVec2(Scroll_width, resizer_height))

        is_active = imgui.is_item_active()
        is_hovered = imgui.is_item_hovered()

        color_normal = imgui.get_color_u32(imgui.ImVec4(0.4, 0.4, 0.4, 1.0))
        color_hovered = imgui.get_color_u32(imgui.ImVec4(0.6, 0.6, 0.6, 1.0))
        color_active = imgui.get_color_u32(imgui.ImVec4(0.8, 0.8, 0.8, 1.0))

        resizer_color = color_normal
        if is_active:
            resizer_color = color_active
        elif is_hovered:
            resizer_color = color_hovered

        if is_hovered or is_active:
            imgui.set_mouse_cursor(imgui.MouseCursor_.resize_ns)

        draw_list = imgui.get_window_draw_list()
        draw_list.add_rect_filled(resizer_min, resizer_max, resizer_color)

        if is_active:
            if not self.is_dragging_resizer_sk:
                self.is_dragging_resizer_sk = True
                try:
                    self.drag_sk_start_mouse_y = imgui.get_mouse_pos().y
                except Exception:
                    self.drag_sk_start_mouse_y = 0
                self.start_height_sk = self.child_window_height

            try:
                delta_y = imgui.get_mouse_pos().y - self.drag_sk_start_mouse_y
                self.child_window_height = max(50, self.start_height_sk + delta_y)
            except Exception:
                pass
        else:
            self.is_dragging_resizer_sk = False

        imgui.end_group()

        imgui.same_line()
        imgui.begin_group()

        # image buttons on right
        frame_padding = imgui.get_style().frame_padding
        tex_size=image_size+frame_padding*2
        GlobalImgui.get().btn_text.new("十##add_sk",size= tex_size,tp='新建空白形态键')


        GlobalImgui.get().btn_text.new("一##rm_sk", size= tex_size, tp='移除选中形态键')
        

        try:
            GlobalImgui.get().btn_image.new("##sk_special", self.btn_sk_special,
                                            image_size=image_size, tp='mio占位符\n暂不可用')
        except Exception:
            pass

        try:
            GlobalImgui.get().btn_image.new("##mv_sk_up", self.btn_mv_sk_up,
                                            image_size=image_size, tp='上移形态键')
        except Exception:
            pass

        try:
            GlobalImgui.get().btn_image.new("##mv_sk_down", self.btn_mv_sk_down,
                                            image_size=image_size, tp='下移形态键')
        except Exception:
            pass

        GlobalImgui.get().btn_text.new("X##clear_all_sk_value",size= tex_size, tp='把所有形态键设为0')
        

        imgui.end_group()

        # slider area for active shape key min/max
        slider_width = 0
        if has_shape_key(self.obj) and not self.obj.active_shape_key_index == 0:
            imgui.push_style_color(imgui.Col_.frame_bg, imgui.ImVec4(0.32, 0.32, 0.32, 1))
            imgui.push_style_color(imgui.Col_.frame_bg_hovered, imgui.ImVec4(0.47, 0.47, 0.47, 1))
            imgui.push_style_color(imgui.Col_.frame_bg_active, imgui.ImVec4(0.16, 0.16, 0.16, 1))
            try:
                imgui.push_item_width((Scroll_width - imgui.calc_text_size('minmax').x - 50 - imgui.get_style().item_spacing.x) / 2)
                _, bpy.context.object.active_shape_key.slider_min = imgui.drag_float('min', bpy.context.object.active_shape_key.slider_min, v_speed=0.01)
                imgui.same_line()
                _, bpy.context.object.active_shape_key.slider_max = imgui.drag_float('max', bpy.context.object.active_shape_key.slider_max, v_speed=0.01)
                imgui.pop_item_width()
            except Exception:
                # ensure stack balanced if something failed
                try:
                    imgui.pop_item_width()
                except Exception:
                    pass
            try:
                imgui.pop_style_color(3)
            except Exception:
                # ensure style stack safe
                pass
            

        slider_width = Scroll_width - 25
        

# end of shapekey_widget
