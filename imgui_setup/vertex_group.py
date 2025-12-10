import bpy
from imgui_bundle import imgui
from .imgui_global import GlobalImgui
from .selectable_input import selectable_input_vg
def vertex_group_widget(self):
    
    window_padding=imgui.get_style().window_padding
    item_spacing=imgui.get_style().item_spacing
    item_inner_spacing=imgui.get_style().item_inner_spacing
    indent_spacing=imgui.get_style().indent_spacing
    frame_padding=imgui.get_style().frame_padding
    obj = bpy.context.object
    self.obj = obj

    if self.obj is None or self.obj.type!='MESH':return
    imgui.separator()
    imgui.set_next_item_open(False, cond=imgui.Cond_.once)
    opened = imgui.collapsing_header("顶点组")
 
    if opened:
        # return
    # if imgui.tree_node("顶点组"):
        imgui.begin_group()
        if not hasattr(self, "vg_child_window_height"):
            self.vg_child_window_height = 130  # 初始高度
        if not hasattr(self, "is_dragging_resizer_vg"):
            self.is_dragging_resizer_vg = False
        if not hasattr(self, "drag_vg_start_mouse_y"):
            self.drag_vg_start_mouse_y = 0
        if not hasattr(self, "start_height_vg"):
            self.start_height_vg = 130
        w=imgui.get_window_size().x-25 -indent_spacing*2-item_spacing.x-frame_padding.x-window_padding.x
        Scroll_width=w if w>230 else 230
        # 滚动窗口
        # bg_color = imgui.ImVec4(0.1, 0.1, 0.1, 1.0)  # 深蓝灰色
        # _,GlobalImgui.get().child_bg=imgui.color_edit4("color 1", GlobalImgui.get().child_bg)
        imgui.push_style_color(imgui.Col_.child_bg, GlobalImgui.get().child_bg)
        visible = imgui.begin_child("ScrollableChild_vg", imgui.ImVec2(Scroll_width, self.vg_child_window_height), True)

        

# 在绘制子窗口前压入样式色     
        if visible:
        
            imgui.begin_group()
            if not hasattr(self, "vertex_group_buf"):
                self.vg_last_count = -1
                self.vg_selected_index = -1
            # 每帧更新 obj 和 shape keys
            
            if 1:
                vg = self.obj.vertex_groups
                # 判断 shape key 数量是否变化（或初始化）
                # if hasattr(self, "vg"):

                    # print(len(self.vg),len(vg))
                if not hasattr(self, "vg") or self.vg_last_count != len(vg):
                    self.vg = vg
                    self.vg_rows = []
                    for group in self.vg:
                        self.vg_rows.append({
                            "group": group,
                            "buf_name": [group.name],
                        })
                else:
                    self.vg = vg  # 同步最新 vg

            else:
                self.vg = []
                self.vg_rows = []

            # 同步 Blender -> ImGui（仅当 ImGui 未主动选中时）
            if len(self.vg) and self.obj.vertex_groups.active_index != self.vg_selected_index:
                self.vg_selected_index = self.obj.vertex_groups.active_index

            # UI 绘制
            for idx, row in enumerate(self.vg_rows):
                label = f"vg_{idx}"
                is_selected = (self.vg_selected_index == idx)
                row["buf_name"][0] = row['group'].name
                changed_name, selected ,row["buf_name"][0]= selectable_input_vg(
                    label,
                    self.vg_selected_index == idx,
                    row["buf_name"],
                    width=Scroll_width,
                )
                if selected:
                    self.vg_selected_index = idx
                    if self.obj.vertex_groups.active_index != idx:
                        self.obj.vertex_groups.active_index = idx  # 👈 仅在 ImGui 中点击时更新 Blender
                if changed_name:
                    print(row["buf_name"][0])
                    row['group'].name = row["buf_name"][0]
            imgui.end_group()
            # ... (前面的代码保持不变) ...
        
        imgui.end_child()
        imgui.pop_style_color()
        imgui.end_group()
        imgui.same_line()
        imgui.begin_group()
        GlobalImgui.get().btn_text.new("十##add_vg",tp='新建空白顶点组')
        GlobalImgui.get().btn_text.new("一##rm_vg" ,tp='移除选中顶点组')
        GlobalImgui.get().btn_text.new("选##vg_select_v",tp='只选中当前顶点组的顶点')
        GlobalImgui.get().btn_text.new("减##vg_rm_select",tp='把选定顶点从顶点组移除')
        GlobalImgui.get().btn_text.new("创##vg_asign",tp='从选定顶点创建')
        
        imgui.end_group()
        if GlobalImgui.get().btn_text.new("清##rm_vg",tp='清理顶点组内的非法权重\n或者0权重点'):pass
        imgui.same_line()
        if GlobalImgui.get().btn_text.new("未##rm_vg",tp='删除未使用顶点组\n修改器,无形变权重'):pass
        imgui.same_line()
        if GlobalImgui.get().btn_text.new("零##rm_vg",tp='删除权重为0的顶点组'):pass
        imgui.same_line()
        if GlobalImgui.get().btn_text.new("rigify##rm_vg",tp='添加rigify骨骼DEF-前缀'):pass
        imgui.same_line()
        if GlobalImgui.get().btn_text.new("普通##rm_vg",tp='删除DEF-前缀'):pass

        imgui.separator()
        condition=GlobalImgui.get().vg_middle or GlobalImgui.get().vg_mul
        text_btn_set_toggle_active_style_color("←##vg_left",condition,close=False,tp='把顶点组顶点组复制到左边')
        # if GlobalImgui.get().btn_text.new("←##vg_left",tp='把顶点组顶点组复制到左边'):
        #     pass
            
        imgui.same_line()
        text_btn_set_toggle_active_style_color("→##vg_right",condition,close=False,tp='把顶点组顶点组复制到右边')
        # if GlobalImgui.get().btn_text.new("→##vg_right",tp='把顶点组顶点组复制到右边'):pass
        imgui.same_line()
        text_btn_set_toggle_style_color("  I  ##vg_middle",close=False,tp='中间的顶点组,配合左右使用')
        # if GlobalImgui.get().btn_text.new("  I  ##vg_middle",tp='中间的顶点组,配合左右使用'):pass
        imgui.same_line()
        if GlobalImgui.get().btn_text.new("镜像##vg_mirror",tp='把顶点组顶点组复制到箭头方向'):pass
        imgui.same_line()
        text_btn_set_toggle_style_color("多##vg_mul",close=False,tp='把一半的顶点组镜像到箭头方向')
        # if GlobalImgui.get().btn_text.new("多##vg_mul",tp='把一半的顶点组镜像到箭头方向'):pass
        imgui.same_line()
        text_btn_set_toggle_active_style_color("选##vg_select",GlobalImgui.get().vg_mul,close=False,tp='只镜像选中的顶点组\n姿态模式下选中骨骼')
        # if GlobalImgui.get().btn_text.new("选##vg_select",tp='只镜像选中的顶点组\n姿态模式下选中骨骼'):pass
        if not hasattr(GlobalImgui.get(), 'vg_mirror_search'): GlobalImgui.get().vg_mirror_search = 0
        imgui.same_line()
        imgui.set_next_item_width(70)
        items=['最近','面投射']
        if imgui.begin_combo("##vg_mirror_search", items[GlobalImgui.get().vg_mirror_search],imgui.ComboFlags_.no_arrow_button):
            for n, it in enumerate(items):
                is_selected = (GlobalImgui.get().vg_mirror_search == n)
                if imgui.selectable(it, is_selected)[0]:
                    GlobalImgui.get().vg_mirror_search = n  # ⚠️ 会在下一个 frame 生效
                if is_selected:
                    imgui.set_item_default_focus()
            imgui.end_combo()
        # imgui.tree_pop()
def text_btn_set_toggle_active_style_color(name,condition,close=True,tp=''):
    text_active_color =  imgui.ImVec4(1, 1, 1, 1)
    text_deactive_color =  imgui.ImVec4(1, 1, 1, 20/255.0)
    if condition:
        imgui.push_style_color(imgui.Col_.text.value, text_active_color)
        pass
        # imgui.push_style_color(imgui.Col_.button_hovered.value, button_active_color)
        # imgui.push_style_color(imgui.Col_.button_active.value, button_active_color)
    else:
        imgui.push_style_color(imgui.Col_.text.value,text_deactive_color)

        # imgui.push_style_color(imgui.Col_.button_hovered.value, button_color)
        # imgui.push_style_color(imgui.Col_.button_active.value, button_color)
    if getattr(GlobalImgui.get(), f"{name.split('##')[-1]}", False):
        imgui.push_style_color(imgui.Col_.button.value, GlobalImgui.get().button_active_color)
        imgui.push_style_color(imgui.Col_.button_hovered.value, GlobalImgui.get().button_active_color)
        imgui.push_style_color(imgui.Col_.button_active.value, GlobalImgui.get().button_active_color)
    else:
        imgui.push_style_color(imgui.Col_.button.value, GlobalImgui.get().button_color)
        imgui.push_style_color(imgui.Col_.button_hovered.value, GlobalImgui.get().button_hovered_color)
        imgui.push_style_color(imgui.Col_.button_active.value, GlobalImgui.get().button_active_color)
    if GlobalImgui.get().btn_text.new(name, 
                            close=close,tp=tp):pass

    imgui.pop_style_color()
    imgui.pop_style_color()
    imgui.pop_style_color()
    imgui.pop_style_color()
    # imgui.pop_style_color()
def text_btn_set_toggle_style_color(name,condition=None,close=True,tp=''):
    # text_active_color =  imgui.ImVec4(1, 1, 1, 1)
    # text_deactive_color =  imgui.ImVec4(1, 1, 1, 20/255.0)
    # if condition:
    #     imgui.push_style_color(imgui.Col_.text.value, text_active_color)
    #     pass
    #     # imgui.push_style_color(imgui.Col_.button_hovered.value, button_active_color)
    #     # imgui.push_style_color(imgui.Col_.button_active.value, button_active_color)
    # else:
    #     imgui.push_style_color(imgui.Col_.text.value,text_deactive_color)

        # imgui.push_style_color(imgui.Col_.button_hovered.value, button_color)
        # imgui.push_style_color(imgui.Col_.button_active.value, button_color)
    if getattr(GlobalImgui.get(), f"{name.split('##')[-1]}", False):
        imgui.push_style_color(imgui.Col_.button.value, GlobalImgui.get().button_active_color)
        imgui.push_style_color(imgui.Col_.button_hovered.value, GlobalImgui.get().button_active_color)
        imgui.push_style_color(imgui.Col_.button_active.value, GlobalImgui.get().button_active_color)
    else:
        imgui.push_style_color(imgui.Col_.button.value, GlobalImgui.get().button_color)
        imgui.push_style_color(imgui.Col_.button_hovered.value, GlobalImgui.get().button_hovered_color)
        imgui.push_style_color(imgui.Col_.button_active.value, GlobalImgui.get().button_active_color)
    if GlobalImgui.get().btn_text.new(name, 
                            close=close,tp=tp):pass

    imgui.pop_style_color()
    imgui.pop_style_color()
    imgui.pop_style_color()