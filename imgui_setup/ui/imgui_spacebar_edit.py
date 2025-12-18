from pathlib import Path
import bpy
from imgui_bundle import imgui

from ...imgui_setup.mirror_reminder import open_tip
from ..imgui_global import GlobalImgui
from ...operators.base_ops import BaseDrawCall

import zipfile
import xml.etree.ElementTree as ET

def read_xlsx_strings(filepath):
    # xlsx 文件其实是 zip
    with zipfile.ZipFile(filepath, "r") as z:
        # 读取共享字符串表 sharedStrings.xml
        with z.open("xl/sharedStrings.xml") as f:
            tree = ET.parse(f)
            root = tree.getroot()

            # Excel 的 XML 使用命名空间，需要处理
            ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
            strings = [t.text for t in root.findall(".//a:t", ns)]

            return strings
filepath = Path(__file__).parent.parent.parent.resolve() /'surface_deform'/ "name_list.xlsx"
# 测试
strings_list = read_xlsx_strings(filepath)
class State3:
    current = 0

def combo_with_string_demo(str_list:list):
    """combo() 还可以使用 '\\0' 分隔的字符串格式"""
    clicked, idx = imgui.combo(
        "##combo3",
        State3.current,
        str_list
    )
    State3.current = idx
    if clicked:
        imgui.text(f"选择索引: {State3.current}")
        print("Current index:", idx, "string:", strings_list[idx] if idx < len(strings_list) else None)
        from ..imgui_global import GlobalImgui
        GlobalImgui.get().surface_deform_name=strings_list[idx]
class Imgui_Spacebar_Edit(bpy.types.Operator, BaseDrawCall):
    bl_idname = "imgui.spacebar_edit"
    bl_label = "spacebar edit"
    bl_options = {'REGISTER','UNDO'}

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type=='MESH' and context.object.mode=='EDIT'

    def load_icon(self):
        self.faceset_from_edit=self.load_icon_texture("editmode_hlt.png")
        self.edit_to_paint_with_a=self.load_icon_texture("armature_data.png")
    def draw(self, context: bpy.types.Context):
        self.cover = False
        self.cover_style_editor = False
        # 展示一个 ImGui 测试窗口
        wf = imgui.WindowFlags_

        window_flags = wf.no_title_bar | wf.no_resize | wf.no_scrollbar | wf.always_auto_resize

        imgui.set_next_window_pos(
            imgui.ImVec2(self.show_window_pos[0] - 50 - imgui.get_style().indent_spacing * 0.5,
                         context.region.height - self.show_window_pos[1] - 40 ))
        _mian_show,_mian_x=imgui.begin("spacebar edit", self.main_window[0], window_flags)

        # Show source object name (similar to QLabel(name))
        scene_settings = bpy.context.scene.kourin_weight_transfer_settings
        source_obj = scene_settings.source_object if hasattr(scene_settings, "source_object") else None
        name = "None"
        if source_obj is not None and source_obj.type == 'MESH':
            if source_obj.name == bpy.context.active_object.name:
                name = "权重来源不能是自己"
            else:
                name = source_obj.name
        imgui.text(name)
        imgui.separator()
        GlobalImgui.get().btn_image.new("##faceset_from_edit", 
                            self.faceset_from_edit,tp='从选中的顶点创建面组',ops=self)
        imgui.same_line()
        GlobalImgui.get().btn_image.new("##edit_to_paint_with_a", 
                            self.edit_to_paint_with_a,tp='选中骨架,并进入权重绘制',ops=self)
        prop=bpy.context.scene.kourin_weight_transfer_settings
        if prop.lazyweight_enable:
            from .weight import lazy_weight
            lazy_weight(self)
        


        GlobalImgui.get().btn_text.new('新建组##vg_asign',tp='从所选创建值为1的顶点组',ops=self)
        GlobalImgui.get().btn_text.new('传权重,修改器##weight_by_modi',tp='用数据传递修改器',ops=self)
        GlobalImgui.get().btn_text.new('传权重,算法##weight_by_algorithm',tp='用算法',ops=self)
        
        imgui.set_next_item_width(100)
        combo_with_string_demo(strings_list)
        GlobalImgui.get().btn_text.new('紧身##surface_deform',tp='紧身衣',ops=self)
        imgui.same_line()
        GlobalImgui.get().btn_text.new('宽松##surface_deform_loose',tp='宽松T恤,外套等',ops=self)
        # GlobalImgui.get().btn_text.new('复制##copy_basis_pos',tp='选中顶点:复制默认形态键的位置')
        # imgui.same_line()
        GlobalImgui.get().btn_text.new('粘贴##paste_basis_pos',tp='选中顶点:粘贴默认形态键位置到激活形态键\n这样可以保证切换形态键时\n选中顶点的位置不变',ops=self)
        GlobalImgui.get().btn_text.new('LazyWeight##lazy_weight_toggle',tp='开启或关闭lazyweight快捷按钮',ops=self)
        
        




        imgui.separator()

    
        self.track_any_cover()
        if imgui.is_item_hovered():
            imgui.set_keyboard_focus_here(-1)

        imgui.end()                                                                                                                                                                                                                                                                                                                                                       

    def invoke(self, context, event):
        self.cover = False
        self.cover_style_editor = False
        self.show_window_pos = (event.mouse_region_x, event.mouse_region_y)
        self.show_window_imgui = False
        self.area=context.area
        self.region , self.mpos = self._get_current_region_and_mpos(context, event)
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
        if event.type == 'SPACE' and event.value == 'RELEASE':
            self.call_shutdown_imgui()
            self.refresh()
            return {'FINISHED'}
        if event.type == 'Z' and event.value == 'RELEASE':
            self.call_shutdown_imgui()
            self.refresh()
            return {'FINISHED'}
        if context.area:
            context.area.tag_redraw()

        gx, gy = event.mouse_x, event.mouse_y


        # —— 计算区域内坐标 —— 
        mx = gx - self.region.x
        my = gy - self.region.y
        self.mpos=(mx,my)

        # —— 越界检测（可选） —— 
        if mx < 0 or mx > self.region.width or my < 0 or my > self.region.height:
            print('越界检测')
            # 告诉 ImGui 鼠标移出了
            try:
                io = imgui.get_io()
                io.mouse_pos = (-1, -1)
            except Exception:
                pass
            return {'PASS_THROUGH'}


        if event.type == 'MIDDLEMOUSE':
            return {'PASS_THROUGH'}
        # 修改右键点击处理（关键修改）
        if event.type=='TAB':
            return {'PASS_THROUGH'}
        if event.type == 'RIGHTMOUSE':
            if  self.cover and event.value == 'PRESS':
                # 发送右键释放事件到ImGui
                io = imgui.get_io()
                io.add_mouse_button_event(1, True)  # 无论点击哪里都发送释放事件
  
                return {'RUNNING_MODAL'}
            else:
                io = imgui.get_io()
                io.add_mouse_button_event(1, False)
                print('non right mouse and cover')
                return {'PASS_THROUGH'}
 

        self.poll_mouse(context, event)
        
        self.poll_events(context, event)
        # print([x for x in gc.get_objects() if isinstance(x, Imgui_Window_Imgui)])
        # print(self.cover ,self.cover_style_editor)
        return {"RUNNING_MODAL" if self.cover or self.cover_style_editor else "PASS_THROUGH"}  # 焦点决策


