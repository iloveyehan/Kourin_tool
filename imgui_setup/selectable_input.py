from .imgui_global import GlobalImgui
from imgui_bundle import imgui
import bpy

from .text_input_event import on_text_edit

def selectable_input(label: str, selected: bool, buf1: list[str], buf2: list[float], width=0, flags=0) -> bool:
    """
    selectable_input with tightly adjacent Copy/Paste buttons, drag_float showing 2 decimals,
    and a checkbox after the numeric control that auto-syncs with the numeric value:
      - numeric > 0.5 -> checkbox checked
      - numeric <= 0.5 -> checkbox unchecked
      - toggling checkbox sets numeric to 1 (checked) or 0 (unchecked)
    Additionally: when checkbox is toggled manually, the current row will be set as selected/active.
    Returns: (changed_any, changed_float, selected_out, current_text)
    """
    imgui.push_id(label)
    imgui.push_style_var(imgui.StyleVar_.item_spacing,
                         (0, imgui.get_style().frame_padding.y * 2))
    try:
        selectable_flags = (
            flags |
            imgui.SelectableFlags_.allow_double_click |
            imgui.SelectableFlags_.no_auto_close_popups |
            imgui.SelectableFlags_.allow_overlap
        )
        # 注意：这里的 20 是硬编码高度，如果你的 get_frame_height() 远大于20，可能需要调整
        _, selected_out = imgui.selectable("##Selectable", selected, selectable_flags, imgui.ImVec2(width, 20))
    finally:
        imgui.pop_style_var()

    selectable_min = imgui.get_item_rect_min()
    item_rect_size = imgui.get_item_rect_size()
    height = item_rect_size.y
    total_width = 80 if width == 0 else width

    # ========== 新增：如果当前窗口出现垂直滚动条，提前在 total_width 中预留出滚动条宽度 ==========
    try:
        # get_scroll_max_y() 在有内容溢出时通常大于 0
        scrollbar_visible = False
        try:
            scrollbar_visible = imgui.get_scroll_max_y() > 0.0
        except Exception:
            # 某些绑定可能没有该函数，尝试通过比较内容区宽度与窗口宽度等其他方式可选扩展
            scrollbar_visible = False

        style = imgui.get_style()
        # scrollbar_size 是滚动条本身宽度，额外加一点 padding 保险起见
        scrollbar_reserve = getattr(style, "scrollbar_size", 12.0) + style.window_padding.x * 0.5
        if scrollbar_visible:
            # 从总宽度中减去预留的滚动条宽度，避免右侧控件被遮挡
            total_width = max(8.0, total_width - scrollbar_reserve)
    except Exception:
        # 出错时保守处理：不改变 total_width
        pass
    # ======================================================================

    # 分区：左 80% 文本+按钮，右侧剩余给 数字 + checkbox（数字占右区域的大部分）
    left_w = total_width * 0.7
    right_total_w = total_width - left_w

    # 在右侧区域中将数字占 80%，checkbox 占 20%
    drag_w = right_total_w*0.7 -10
    # drag_w = right_total_w -0.8-15
    chk_w = right_total_w * 0.2

    # 计算用于对齐的控件高度
    try:
        control_h = imgui.get_frame_height()
    except Exception:
        try:
            style = imgui.get_style()
            font_h = imgui.calc_text_size("A").y
            control_h = font_h + style.frame_padding.y * 2
        except Exception:
            control_h = max(16.0, height)

    # 这是所有标准控件（Input, Drag, Checkbox, Button）的顶部Y坐标，用于居中
    control_y = selectable_min.y + max(0.0, (height - control_h) / 2.0)

    # 左侧文本区域 rect（固定）
    rect1_min = selectable_min
    rect1_max = imgui.ImVec2(rect1_min.x + left_w, rect1_min.y + height)

    # 预估按钮宽度
    try:
        style = imgui.get_style()
        pad_x = style.frame_padding.x
        w_copy_text = imgui.calc_text_size("复").x
        w_paste_text = imgui.calc_text_size("粘").x
        # 使用 imgui.button，宽度计算可能需要调整（small_button 的 +8 可能是特定值）
        # 标准 button 宽度是 text_w + pad_x * 2
        btn_w_copy = w_copy_text + pad_x * 2   # 暂时保留 +8，如果太宽可以去掉
        btn_w_paste = w_paste_text + pad_x * 2 # 暂时保留 +8
        total_btn_w = btn_w_copy + btn_w_paste
    except Exception:
        total_btn_w = 48
        btn_w_copy = btn_w_paste = total_btn_w / 2

    inner_padding = 2
    input_area_w = max(8.0, left_w - total_btn_w - inner_padding * 2)

    # 编辑态存储
    input_id1 = imgui.get_id("Input1")
    storage = imgui.get_state_storage()
    active1 = storage.get_bool(input_id1, False)

    # 双击进入编辑
    try:
        if imgui.is_mouse_double_clicked(0) and imgui.is_mouse_hovering_rect(rect1_min, rect1_max):
            storage.set_bool(input_id1, True)
    except Exception:
        pass

    changed_any = False
    changed_text_confirmed = False
    changed_float = False
    current_text = buf1[0] if buf1 and len(buf1) > 0 else ""

    # 文本输入水平起点
    input_cursor_x = rect1_min.x + inner_padding

    # ---------- 文本编辑 / 显示 与 Copy/Paste 按钮（位置在 left_w 的右侧） ----------
    if active1:
        # 编辑态：input_text 固定宽度、基线
        try:
            imgui.set_cursor_screen_pos(imgui.ImVec2(input_cursor_x, control_y))
        except Exception:
            pass

        imgui.push_item_width(input_area_w)
        try:
            flags_input = (imgui.InputTextFlags_.auto_select_all
                           | imgui.InputTextFlags_.enter_returns_true
                           | imgui.InputTextFlags_.callback_always.value)
            try:
                changed_res, new_str = imgui.input_text(f"##Input1_{label}", current_text,
                                                        flags=flags_input, callback=on_text_edit)
            except TypeError:
                try:
                    changed_res, new_str = imgui.input_text(f"##Input1_{label}", current_text,
                                                            flags=imgui.InputTextFlags_.auto_select_all | imgui.InputTextFlags_.enter_returns_true)
                except Exception:
                    changed_res = False
                    new_str = current_text
            current_text = new_str
            if buf1 is not None and len(buf1) > 0:
                buf1[0] = current_text
            changed_text_confirmed = bool(changed_res)
        finally:
            try:
                imgui.pop_item_width()
            except Exception:
                pass

        # 结束编辑判定
        try:
            if (imgui.is_mouse_clicked(0) and not imgui.is_mouse_hovering_rect(rect1_min, rect1_max)) or imgui.is_key_down(imgui.Key.enter):
                storage.set_bool(input_id1, False)
                changed_any = True
        except Exception:
            pass
        try:
            active_id = imgui.get_active_id()
            current_input_unique = imgui.get_id("Input1")
            if imgui.is_mouse_clicked(0) and active_id != current_input_unique:
                storage.set_bool(input_id1, False)
                changed_any = True
        except Exception:
            pass

        # 按钮（固定位置）
        try:
            btn_area_right = rect1_min.x + left_w - inner_padding
            paste_btn_x = btn_area_right - btn_w_paste
            copy_btn_x = paste_btn_x - btn_w_copy
            imgui.set_cursor_screen_pos(imgui.ImVec2(copy_btn_x, control_y))
        except Exception:
            pass

        imgui.push_style_var(imgui.StyleVar_.item_spacing, (0.0, 0.0))
        try:
            # <--- 更改：使用 imgui.button 保证高度一致
            if imgui.button(f"复##{label}_copy"): 
                try:
                    bpy.context.window_manager.clipboard = current_text or ""
                except Exception:
                    pass
            imgui.same_line(0.0, 0.0)
             # <--- 更改：使用 imgui.button 保证高度一致
            if imgui.button(f"粘##{label}_paste"):
                try:
                    paste_text = bpy.context.window_manager.clipboard or ""
                    if buf1 is not None and len(buf1) > 0:
                        buf1[0] = paste_text
                        current_text = paste_text
                        changed_any = True
                except Exception:
                    pass
        finally:
            imgui.pop_style_var()

    else:
        # 非编辑态：绘制文本并绘制按钮（与编辑态位置一致）
        def truncate_text_to_fit(text, max_w):
            if not text:
                return ""
            whole_w = imgui.calc_text_size(text).x
            if whole_w <= max_w:
                return text
            res = ""
            total = 0.0
            for ch in text:
                w = imgui.calc_text_size(ch).x
                if total + w > max_w:
                    break
                res += ch
                total += w
            if res and len(res) < len(text):
                ell = "..."
                ell_w = imgui.calc_text_size(ell).x
                while res and total + ell_w > max_w:
                    last = res[-1]
                    total -= imgui.calc_text_size(last).x
                    res = res[:-1]
                res = res + ell if res else ""
            return res

        truncated_text = truncate_text_to_fit(current_text, input_area_w)
        try:
            # 微调 Y 使文字视觉居中
            # 注意：这个 text_y 的计算可能也需要调整，以匹配标准控件内的文字位置
            # 标准控件内的文字Y = control_y + style.frame_padding.y
            style = imgui.get_style()
            text_y = control_y + style.frame_padding.y 
            # text_y = control_y + imgui.get_style().frame_padding.y / 2.0 # 旧代码
            
            imgui.get_window_draw_list().add_text(
                imgui.ImVec2(input_cursor_x, text_y),
                imgui.get_color_u32(imgui.Col_.text),
                truncated_text
            )
        except Exception:
            pass

        try:
            btn_area_right = rect1_min.x + left_w - inner_padding
            paste_btn_x = btn_area_right - btn_w_paste
            copy_btn_x = paste_btn_x - btn_w_copy
            imgui.set_cursor_screen_pos(imgui.ImVec2(copy_btn_x, control_y))
        except Exception:
            pass

        imgui.push_style_var(imgui.StyleVar_.item_spacing, (0.0, 0.0))
        try:
             # <--- 更改：使用 imgui.button 保证高度一致
            if imgui.button(f"复##{label}_copy"):
                try:
                    bpy.context.window_manager.clipboard = current_text or ""
                except Exception:
                    pass
            imgui.same_line(0.0, 0.0)
             # <--- 更改：使用 imgui.button 保证高度一致
            if imgui.button(f"粘##{label}_paste"):
                try:
                    paste_text = bpy.context.window_manager.clipboard or ""
                    if buf1 is not None and len(buf1) > 0:
                        buf1[0] = paste_text
                        current_text = paste_text
                        changed_any = True
                except Exception:
                    pass
        finally:
            imgui.pop_style_var()

    # ---------- 右侧 drag_float (宽 drag_w) 和 checkbox (宽 chk_w) ----------
    # drag_float 放在 selectable_min.x + left_w
    try:
        drag_x = selectable_min.x + left_w
        imgui.set_cursor_screen_pos(imgui.ImVec2(drag_x, control_y))
    except Exception:
        pass

    imgui.push_style_color(imgui.Col_.frame_bg, imgui.ImVec4(0.2, 0.2, 0.5, 0))
    imgui.push_style_color(imgui.Col_.frame_bg_hovered, imgui.ImVec4(0.3, 0.3, 0.6, 0))
    imgui.push_style_color(imgui.Col_.frame_bg_active, imgui.ImVec4(0.4, 0.4, 0.7, 0))
    imgui.push_item_width(drag_w)
    try:
        # drag_float 显示两位小数
        try:
            changed2, new_val = imgui.drag_float(f"##Input2_{label}", buf2[0], v_speed=0.01, format="%.2f")
        except TypeError:
            changed2, new_val = imgui.drag_float(f"##Input2_{label}", buf2[0], v_speed=0.01)
        # 将 buf2 四舍五入到两位小数
        try:
            new_val_num = round(float(new_val), 2)
        except Exception:
            new_val_num = new_val
        if buf2 is not None and len(buf2) > 0:
            # 如果用户用 drag 改变值，则写回并标记 changed
            if new_val_num != buf2[0]:
                buf2[0] = new_val_num
                changed_any = True
                changed_float = True
    finally:
        try:
            imgui.pop_item_width()
        except Exception:
            pass
        try:
            imgui.pop_style_color(3)
        except Exception:
            try:
                imgui.pop_style_color(); imgui.pop_style_color(); imgui.pop_style_color()
            except Exception:
                pass

    # 复选框位置：紧接 drag_float 之后（在 drag_x + drag_w 位置）
    try:
        chk_x = selectable_min.x + left_w + drag_w + 4  # 4 px padding
        imgui.set_cursor_screen_pos(imgui.ImVec2(chk_x, control_y))
    except Exception:
        pass

    # checkbox 的初始状态由当前数值决定（>0.5 为 True）
    try:
        checked_initial = bool(buf2[0] > 0.5)
    except Exception:
        checked_initial = False

    # draw checkbox and处理交互
    try:
        try:
            chk_changed, checked_val = imgui.checkbox(f"##Chk_{label}", checked_initial)
        except TypeError:
            chk_changed = False
            checked_val = checked_initial
    except Exception:
        chk_changed = False
        checked_val = checked_initial

    # 如果用户手动切换 checkbox，则把数值设置为 1 或 0，并将当前行设为选中/激活
    if chk_changed:
        try:
            if buf2 is not None and len(buf2) > 0:
                buf2[0] = 1.0 if checked_val else 0.0
            changed_any = True
            changed_float = True
            # 把行标记为选中：修改 selected_out，并尝试给 selectable 聚焦
            selected_out = True
            try:
                # 尽力设置焦点到该项（不同绑定表现可能不同）
                imgui.set_item_default_focus()
            except Exception:
                pass
            try:
                # 在某些绑定中可以使用键盘焦点移动，使用 -1 表示当前项之前一个控件
                imgui.set_keyboard_focus_here(-1)
            except Exception:
                pass
        except Exception:
            pass

    imgui.pop_id()
    # 返回 (任何改变, 数值改变, selected_out, current_text)
    return changed_any or changed_text_confirmed, changed_float, selected_out, buf1[0]

def selectable_input_vg(label: str, selected: bool, buf1: list[str], width=0, flags=0) -> bool:
    imgui.push_id(label)
    imgui.push_style_var(imgui.StyleVar_.item_spacing,
                            (imgui.get_style().item_spacing.x, imgui.get_style().frame_padding.y * 2))

    selectable_flags = (
            flags |
            imgui.SelectableFlags_.allow_double_click |
            imgui.SelectableFlags_.no_auto_close_popups |
            imgui.SelectableFlags_.allow_overlap
    )
    ret, selected_out = imgui.selectable("##Selectable", selected, selectable_flags, imgui.ImVec2(width, 20))
    imgui.pop_style_var()

    selectable_min = imgui.get_item_rect_min()
    height = imgui.get_item_rect_size().y
    width = 80 if width == 0 else width

    input_id1 = imgui.get_id("Input2")
    storage = imgui.get_state_storage()
    active1 = storage.get_bool(input_id1, False)

    rect1_min = selectable_min
    rect1_max = imgui.ImVec2(rect1_min.x + width * .6, rect1_min.y + height)

    if imgui.is_mouse_double_clicked(0) and imgui.is_mouse_hovering_rect(rect1_min, rect1_max):
        storage.set_bool(input_id1, True)
        # try:
        #     imgui.set_keyboard_focus_here(-1)
        # except Exception:
        #     pass

    changed1 = False
    changed = False
    if active1:
        imgui.set_cursor_screen_pos(rect1_min)
        imgui.push_item_width(width * 0.6)
        try:
            flags_input = (imgui.InputTextFlags_.auto_select_all
                           | imgui.InputTextFlags_.enter_returns_true
                           | imgui.InputTextFlags_.callback_always.value)
            try:
                changed_res, new_str = imgui.input_text("##Input1", buf1[0],
                                                        flags=flags_input,
                                                        callback=on_text_edit)
            except TypeError:
                changed_res = False
                new_str = buf1[0]
            buf1[0] = new_str
            changed1 = bool(changed_res)
        finally:
            try:
                imgui.pop_item_width()
            except Exception:
                pass

        try:
            ended_after_edit = imgui.is_item_deactivated_after_edit()
        except Exception:
            ended_after_edit = False

        if ended_after_edit or changed1 or imgui.is_key_down(imgui.Key.enter):
            storage.set_bool(input_id1, False)
            changed = True

        # # 点击其他地方强制结束
        # try:
        #     active_id = imgui.get_active_id()
        #     current_input_unique = imgui.get_id("Input2")
        #     if imgui.is_mouse_clicked(0) and active_id != current_input_unique:
        #         storage.set_bool(input_id1, False)
        #         changed = True
        # except Exception:
        #     pass
        if (imgui.is_mouse_clicked(0) and not imgui.is_mouse_hovering_rect(rect1_min, rect1_max)) or imgui.is_key_down(imgui.Key.enter):
            storage.set_bool(input_id1, False)
            changed=True

    else:
        def truncate_text_to_fit(text, max_width):
            result = ""
            total_width = 0
            for c in text:
                w = imgui.calc_text_size(c).x
                if total_width + w > max_width:
                    break
                result += c
                total_width += w
            return result
        truncated_text = truncate_text_to_fit(buf1[0], max_width=width * 0.6)
        try:
            imgui.get_window_draw_list().add_text(
                imgui.ImVec2(rect1_min.x + 4, rect1_min.y + 2),
                imgui.get_color_u32(imgui.Col_.text),
                truncated_text
            )
        except Exception:
            pass

    imgui.pop_id()
    return changed, selected_out, buf1[0]
