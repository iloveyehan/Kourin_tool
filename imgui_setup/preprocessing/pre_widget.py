import bpy
import sys
from imgui_bundle import imgui
from imgui_bundle import ImVec2, ImVec4
from ..imgui_global import GlobalImgui
from ..mirror_reminder import open_mirror_tip, open_tip
def pre_widget(self):
    opened = imgui.collapsing_header("预处理")
  
    # print(GlobalImgui.get().hover_header,GlobalImgui.get().header_open["预处理"])
    if opened:
        GlobalImgui.get().btn_image.new("##set_viewport_display_random", 
                            self.btn_set_viewport_display_random,tp='设置每个物体不同颜色')
        imgui.same_line()
        GlobalImgui.get().btn_image.new("##clean_skeleton", 
                            self.btn_clean_skeleton,tp='清理选中的骨骼,\n移除没有权重的骨骼')
        imgui.same_line()
        GlobalImgui.get().btn_text.new("棍##make_skeleton",tp='设置激活骨骼为棍型\n其他骨骼为八面锥')
        imgui.same_line()
        GlobalImgui.get().btn_text.new("骨名##show_bonename",tp='显示骨骼名称')
        imgui.same_line()
        GlobalImgui.get().btn_text.new("前##in_front", tp='把骨骼在前面显示')
        imgui.same_line()
        GlobalImgui.get().btn_text.new("轴##show_axes",tp='显示骨骼轴向')
        
        GlobalImgui.get().btn_text.new('应用##pose_to_reset',tp='把当前POSE设置为默认POSE\n注意:需要选中骨骼')
        open_tip('应用##pose_to_reset','需要选择骨骼')
        imgui.same_line()
        GlobalImgui.get().btn_text.new('合骨##combine_selected_bone_weights',tp='合并到激活骨骼(包括权重)\n注意:需要选中骨骼')
        open_tip('合骨##combine_selected_bone_weights','需要选择骨骼')
        imgui.same_line()
        GlobalImgui.get().btn_text.new('改名##rename_armature',tp='把骨骼命名统一\n以激活骨架为准\n注意:可能有错误,需要检查')
        open_tip('改名##rename_armature','需要选择两个骨架')
        imgui.same_line()
        GlobalImgui.get().btn_text.new('合并##merge_armature',tp='合并骨架\n注意:会合并到激活骨架')
        open_tip('合并##merge_armature','需要选择两个骨架')
        imgui.same_line()
        GlobalImgui.get().btn_text.new('统一##unify_nvname',tp='统一所有物体uv名称')


        GlobalImgui.get().btn_text.new('递归子集##select_bone_with_children',tp='递归选择所有子集,然后弃选自己')
        imgui.same_line()
        GlobalImgui.get().btn_text.new('弃选顶级##remove_top_bones',tp='弃选每根骨链的最顶级骨骼,方便实现连接父级骨骼操作')
        imgui.same_line()
        GlobalImgui.get().btn_text.new('连接父级##use_connect',tp='相连项,连接父级')


