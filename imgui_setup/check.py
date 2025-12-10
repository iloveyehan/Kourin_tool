import bpy
import time
from imgui_bundle import imgui
from .selectable_input import selectable_input
from .imgui_global import GlobalImgui
from ..utils.mesh import has_shape_key
from ..utils.scene import get_all_collections

# def set_toggle_style_color(name, texture_id, condition, close=True,image_size=image_size, tp=''):
#     """
#     Draw a toggle-like image button with different colors depending on condition.
#     push 3 colors then pop 3 colors to keep ImGui stack balanced.
#     """
#     button_color = imgui.ImVec4(0.33, 0.33, 0.33, 1)
#     button_active_color = imgui.ImVec4(71/255.0, 114/255.0, 179/255.0, 1)
#     if condition:
#         imgui.push_style_color(imgui.Col_.button.value, button_active_color)
#         imgui.push_style_color(imgui.Col_.button_hovered.value, button_active_color)
#         imgui.push_style_color(imgui.Col_.button_active.value, button_active_color)
#     else:
#         imgui.push_style_color(imgui.Col_.button.value, button_color)
#         imgui.push_style_color(imgui.Col_.button_hovered.value, button_color)
#         imgui.push_style_color(imgui.Col_.button_active.value, button_color)

#     # use GlobalImgui image_btn; keep original calling pattern
#     try:
#         if GlobalImgui.get().btn_image.new(name, texture_id, close=close,image_size=image_size, tp=tp):
#             pass
#     except Exception:
#         # be tolerant if image_btn is missing or new() fails
#         try:
#             _ = GlobalImgui.get().btn_image
#         except Exception:
#             pass

#     # pop exactly 3 colors
#     imgui.pop_style_color()
#     imgui.pop_style_color()
#     imgui.pop_style_color()


def widget_check(self):
    """

    """
    window_padding = imgui.get_style().window_padding
    item_spacing = imgui.get_style().item_spacing
    item_inner_spacing = imgui.get_style().item_inner_spacing
    indent_spacing = imgui.get_style().indent_spacing
    frame_padding = imgui.get_style().frame_padding
    global selected

    obj = bpy.context.object
    self.obj = obj
    # if self.obj is None or self.obj.type != 'MESH':
    #     return

    imgui.separator()
    imgui.set_next_item_open(True, cond=imgui.Cond_.once)

    if imgui.collapsing_header("检查"):
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
        imgui.text("做完之后检查!")
        # new=1
        changed, GlobalImgui.get().overinfluence_point_size = imgui.drag_int(
        "绘制大小", 
        GlobalImgui.get().overinfluence_point_size, 
        1, 
        1,20
    )
        GlobalImgui.get().btn_text.new('计算##compute',tp='blender-unity权重不一致的时候点这个计算,然后点显示,\n会显示多余的顶点权重,unity只支持一个顶点4个顶点组')
        imgui.same_line()
        GlobalImgui.get().btn_text.new('显示##show_excessive',tp='在3d视图显示多余的顶点')
        imgui.same_line()
        GlobalImgui.get().btn_text.new('删除##rm_excessive',tp='删除多余的顶点组权重')
        imgui.separator()
        GlobalImgui.get().btn_text.new('检查##check_scene',tp='检查命名,uv后缀是否统一,等等')

        imgui.same_line()
        GlobalImgui.get().btn_text.new('清理##clean_scene',tp='清理不在当前视图层或未链接到集合的Mesh和未使用的材质(包括fake user)')
        # print(getattr(GlobalImgui.get(), 'check_scene_result', False) )
        if getattr(GlobalImgui.get(), 'check_scene_result', False):
            imgui.text("检查结果可用")
            
            # ✅ 查看按钮（可重复打开）
            # if imgui.button("查看详细结果"):
                
            
            # imgui.same_line()
            
            # ✅ 清除按钮（清理数据）
            # if imgui.button("清除结果"):
            #     GlobalImgui.get().check_scene_result = None
            #     GlobalImgui.get().window_mgr.close_window("检查场景结果")

        if hasattr(GlobalImgui.get(), 'window_mgr'):
            GlobalImgui.get().window_mgr.draw_all_windows()
        # print(GlobalImgui.get().window_mgr.windows )
        # GlobalImgui.get().window_mgr.draw_all_windows()

            # opened, _x = imgui.begin(
            #     "新窗口", 
            #     GlobalImgui.get().show_new_window[0],
            #     imgui.WindowFlags_.no_nav | imgui.WindowFlags_.no_focus_on_appearing
            # )
            
            # imgui.text("这是一个新窗口！")
            #     # GlobalImgui.get().show_new_window[0] = True
            # for line in GlobalImgui.get().check_scene_result:
            #     imgui.text_wrapped(line)
            #     # 缩进（UV 分组行以 "  " 开头）
            #     # if line.startswith("  "):
            #     #     uv_name, objs = line.strip().split(": ", 1)

            #     #     # 两格缩进
            #     #     imgui.indent(20)

            #     #     # UV 名称红色
            #     #     imgui.text_colored(f"{uv_name}: ", 1.0, 0.3, 0.3, 1.0)
            #     #     imgui.same_line()
            #     #     imgui.text(objs)

            #     #     imgui.unindent(20)
            #     # else:
            #     #     imgui.text(line)
            # imgui.end()
        if getattr(GlobalImgui.get(),'clean_scene_result',False):
            imgui.text_wrapped(GlobalImgui.get().clean_scene_result)
        imgui.end_group()

 