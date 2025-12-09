from pathlib import Path
import bpy
from imgui_bundle import imgui

from ...imgui_setup.mirror_reminder import open_tip
from ..imgui_global import GlobalImgui
from ...operators.base_ops import BaseDrawCall

import zipfile
import xml.etree.ElementTree as ET
class Imgui_Spacebar_Pose(bpy.types.Operator, BaseDrawCall):
    bl_idname = "imgui.spacebar_pose"
    bl_label = "spacebar pose"
    bl_options = {'REGISTER','UNDO'}

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type=='ARMATURE' and context.object.mode=='POSE'

    def load_icon(self):
        self.pose_to_obj=self.load_icon_texture("object_data.png")
        self.edit_to_paint_with_a=self.load_icon_texture("armature_data.png")
        self.pose_to_edit=self.load_icon_texture("editmode_hlt.png")
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
        GlobalImgui.get().btn_image.new("##pose_to_obj", 
                            self.pose_to_obj,tp='进入物体模式')
        imgui.same_line()
        GlobalImgui.get().btn_image.new("##pose_to_edit", 
                            self.pose_to_edit,tp='进入最后选择的mesh编辑模式')
        imgui.same_line()
        GlobalImgui.get().btn_image.new("##pose_to_paint_with_a", 
                            self.edit_to_paint_with_a,tp='进入权重绘制,最后一次选中的模型')
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

        # # —— 动态查找当前鼠标在 screen 哪个 region 上 —— 
        # region = None
        # current_area = None # 🌟 新增：我们需要知道鼠标当前在哪个 area
        # for area in context.window.screen.areas:
        #     for r in area.regions:
        #         # r.x, r.y 是 region 在窗口中的左下角坐标
        #         if (gx >= r.x and gx <= r.x + r.width
        #         and gy >= r.y and gy <= r.y + r.height):
        #             region = r
        #             current_area = area # 🌟 存储找到的 area
        #             break
        #     if region:
                # break

        # 找不到就透传，让 Blender 处理
        # if region is None:
        #     # print('no region')
        #     return {'PASS_THROUGH'}
        # if current_area != self.area:
        #     # 鼠标在 B 视图，但 Operator 在 A 视图
        #     # 我们必须 PASS_THROUGH，并且不发送任何坐标给 ImGui
            
        #     # (可选但推荐) 告诉 ImGui 鼠标已经离开，以取消悬停状态
        #     try:
        #         io = imgui.get_io()
        #         io.mouse_pos = (-1, -1) # 将鼠标位置设置到屏幕外
        #     except Exception:
        #         pass # 忽略 ImGui 上下文可能无效的错误
                
        #     return {'PASS_THROUGH'}
        # if region:
        #     region.tag_redraw()
        #     # if self.region_capture==None:
        #     if self.region==None:
        #         print('没有region',self.region,region)
        #         self.region=region
        #         # self.region_capture=region
        # else:
        #     print('else no region')
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

        # if event.type in {"ESC"}:
        #     print("ESC", self.area, bpy.context.area)
        #     self.call_shutdown_imgui()
        #     self.refresh() 
        #     return {'FINISHED'}
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


