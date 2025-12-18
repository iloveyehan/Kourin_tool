import time
import bpy
from imgui_bundle import imgui
from functools import partial

from ..imgui_setup import toast_drawer
from ..utils.armature import comfirm_one_arm

from ..utils.utils import undoable
from .mirror_reminder import open_mirror_tip, open_tip


def armature_poll():
    if bpy.context.active_object is None:
        return False
    armatures = [obj for obj in bpy.context.selected_objects if obj.type == 'ARMATURE']
    return (len(armatures) == 2 and bpy.context.active_object.type == 'ARMATURE')



# --- 1. 核心操作逻辑基类 ---
class ButtonActions:
    """
    所有按钮操作处理函数的中央容器。
    ImageButton 和 TextButton 都将继承此类。
    """
    
    # 统一的事件处理函数
    def button_handler(self, btn):
        """
        根据按钮的 ID 动态查找并执行对应的处理函数。
        """
        # 提取 ID 部分（例如 'Label###handle_vg_mirror' -> 'vg_mirror'）
        # 兼容 '###' 和 '##' 分隔符
        self.weight=btn.split('#')[0]
        # print('self.weight1',self.weight)
        name_id = btn.split('#')[-1] 
        # 构造方法名，例如 'handle_vg_mirror'
        method_name = f"handle_{name_id}"
        func = getattr(self, method_name, None)
        
        # print(f'处理函数: {btn}, 查找方法: {method_name}')
        
        # 如果函数存在，则执行
        if func and callable(func):
            # 使用 TextButton 中更安全的 Timer 注册方式来执行 Blender 操作，
            # 以确保在 ImGui 绘制上下文之外执行。
            # 注意：这里假设 func 接受 self 和一个参数 (btn)。
            try:
                # 假设所有操作方法都被定义为接受至少一个参数（btn 或 c）
                bpy.app.timers.register(partial(func)) 
            except Exception as e:
                # 如果是简单的操作（如 ImageButton 的某些操作），可能不需要计时器，
                # 但为了统一和安全，保持计时器。
                print(f"执行 {method_name} 失败: {e}")
        else:
            print(f"未找到处理函数: {name_id}")
        return True
    # --- ImageButton 原始操作（已修改为接受 *args 以兼容计时器 partial） ---
    #预处理
    @undoable
    def handle_set_viewport_display_random(self, *args):
        bpy.ops.kourin.set_viewport_display_random()
    @undoable
    def handle_unify_nvname(self, *args):
        bpy.ops.kourin.unify_uv_name()
    @undoable
    def handle_select_bone_with_children(self, *args):
        bpy.ops.kourin.select_bone_with_children()
    @undoable
    def handle_remove_top_bones(self, *args):
        bpy.ops.kourin.remove_top_bones()
    @undoable
    def handle_use_connect(self, *args):
        bpy.ops.kourin.use_connect()
        
    @undoable
    def handle_clean_skeleton(self, *args):
        obj = bpy.context.active_object
        if not obj or obj.type != 'ARMATURE':
            print("请选择一个骨骼对象")
            return
        bpy.ops.kourin.delete_unused_bones()
        
    @undoable
    def handle_make_skeleton(self, *args):
        bpy.ops.kourin.set_bone_display()
        
    @undoable
    def handle_show_bonename(self, *args):
        obj=bpy.context.active_object
        if obj is None:
            return
        if obj.type =='MESH':
            for modi in obj.modifiers:
                if modi.type=='ARMATURE' and modi.object is not None:
                    modi.object.data.show_names = not modi.object.data.show_names 
                    return
        for b in bpy.context.selected_objects:
            if b.type=='ARMATURE':
                b.data.show_names = not b.data.show_names
    @undoable
    def handle_show_axes(self, *args):
        obj=bpy.context.active_object
        if obj is None:
            return
        if obj.type =='MESH':
            for modi in obj.modifiers:
                if modi.type=='ARMATURE' and modi.object is not None:
                    modi.object.data.show_axes = not modi.object.data.show_axes 
                    return
        for b in bpy.context.selected_objects:
            if b.type=='ARMATURE':
                b.data.show_axes = not b.data.show_axes
        # bpy.ops.kourin.show_bone_name()
    @undoable
    def handle_in_front(self):
        obj=bpy.context.active_object
        if obj is None:
            return
        if obj.type =='MESH':
            for modi in obj.modifiers:
                if modi.type=='ARMATURE' and modi.object is not None:
                    modi.object.show_in_front = not modi.object.show_in_front
                    return
        if obj.type=='ARMATURE':
            obj.show_in_front = not obj.show_in_front
    @undoable
    def handle_pose_to_reset(self):
        # from .imgui_global import GlobalImgui 
        # global_data = GlobalImgui.get()
        # if bpy.context.active_object.type != "ARMATURE":
        #     setattr(global_data, f"{btn}", True)
        #     setattr(global_data, f"{btn}_time", time.time())
        #     return None
        # bpy.ops.kourin.pose_to_reset()
        def temp_pose_to_rest():
            bpy.ops.rename_cats_manual.pose_to_rest()
            return None
        bpy.app.timers.register(temp_pose_to_rest)

        # bpy.ops.rename_cats_manual.pose_to_rest()
    @undoable
    def handle_combine_selected_bone_weights(self):
        obj=bpy.context.object


        if obj is not None and obj.type=='ARMATURE':

            md=obj.mode
            bpy.ops.object.mode_set(mode='POSE')
            bpy.ops.kourin.combine_selected_bone_weights()
            bpy.ops.object.mode_set(mode=md)
    

    @undoable
    def handle_merge_armature(self):

        bpy.ops.kourin.merge_armatures()
    @undoable    
    def handle_rename_armature(self):

        bpy.ops.kourin.rename_armatures()
    @undoable    
    def handle_pose_to_obj(self):
        bpy.ops.object.posemode_toggle()

    
    
    #顶点组
    @undoable
    def handle_vg_mirror(self):
        bpy.ops.kourin.vg_mirror_weight()
    
    def handle_vg_left(self):
        # 假设 GlobalImgui 引用已正确设置
        from .imgui_global import GlobalImgui 
        global_data = GlobalImgui.get()
        if not (global_data.vg_middle or global_data.vg_mul):
            print('return', global_data.vg_middle, global_data.vg_mul)
            return None
        global_data.vg_left = True
        global_data.vg_right = not global_data.vg_left
        print('当前handle_vg_left', not global_data.vg_left, global_data.vg_right)
        
    def handle_vg_right(self):
        from .imgui_global import GlobalImgui 
        global_data = GlobalImgui.get()
        if not (global_data.vg_middle or global_data.vg_mul):
            return None
        global_data.vg_right = True
        global_data.vg_left = not global_data.vg_right
        print('当前handle_vg_r', not global_data.vg_right, global_data.vg_left)
        
    def handle_vg_select(self):
        from .imgui_global import GlobalImgui 
        global_data = GlobalImgui.get()
        if not global_data.vg_mul:
            return None
        global_data.vg_select = not global_data.vg_select
        
    def handle_vg_middle(self):
        from .imgui_global import GlobalImgui 
        global_data = GlobalImgui.get()
        if global_data.vg_middle:
            if global_data.vg_left:
                global_data.last_side = 'vg_left'
            if global_data.vg_right:
                global_data.last_side = 'vg_right'
            if not global_data.vg_mul:
                global_data.vg_left = False
                global_data.vg_right = False
        else:
            if not (global_data.vg_left and global_data.vg_right):
                if len(global_data.last_side):
                    if global_data.last_side == 'vg_left':
                        global_data.vg_left = True
                    elif global_data.last_side == 'vg_right':
                        global_data.vg_right = True
                    else:
                        global_data.vg_left = True
                else:
                    global_data.vg_left = True
                
        global_data.vg_middle = not global_data.vg_middle
        
    def handle_vg_mul(self):
        from .imgui_global import GlobalImgui 
        global_data = GlobalImgui.get()
        if global_data.vg_mul:
            global_data.vg_select = False
        if global_data.vg_mul:
            if global_data.vg_left:
                global_data.last_side = 'vg_left'
            if global_data.vg_right:
                global_data.last_side = 'vg_right'
            if not global_data.vg_middle:
                global_data.vg_left = False
                global_data.vg_right = False
        else:
            if not (global_data.vg_left and global_data.vg_right):
                if len(global_data.last_side):
                    if global_data.last_side == 'vg_left':
                        global_data.vg_left = True
                    elif global_data.last_side == 'vg_right':
                        global_data.vg_right = True
                    else:
                        global_data.vg_left = True
                else:
                    global_data.vg_left = True

        global_data.vg_mul = not global_data.vg_mul
    @undoable
    def handle_add_vg(self):
        bpy.ops.object.vertex_group_add()
    @undoable
    def handle_rm_vg(self):
        bpy.ops.object.vertex_group_remove(all=False, all_unlocked=False)
    @undoable
    def handle_vg_rm_select(self):
        bpy.ops.kourin.vg_rm_select()
    @undoable
    def handle_vg_select_v(self):
        mode_t=bpy.context.object.mode
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.vertex_group_select()
        bpy.ops.object.mode_set(mode=mode_t)
    @undoable
    def handle_vg_asign(self):
        bpy.ops.kourin.vg_asign_new_group()

    

    @undoable
    def handle_clear_sync_col(self, *args):
        pass
    @undoable
    def handle_add_sk(self, *args):
        bpy.ops.object.shape_key_add(from_mix=False)
    @undoable
    def handle_rm_sk(self, *args):
        bpy.ops.object.shape_key_remove(all=False)
    @undoable
    def handle_mv_sk_up(self, *args):
        bpy.ops.object.shape_key_move(type='UP')
    @undoable
    def handle_mv_sk_down(self, *args):
        bpy.ops.object.shape_key_move(type='DOWN')
    @undoable
    def handle_clear_all_sk_value(self, *args):
        bpy.ops.object.shape_key_clear()
        
    @undoable
    def handle_solo_active_sk(self, *args):
        bpy.context.object.show_only_shape_key = not bpy.context.object.show_only_shape_key
        
    @undoable
    def handle_sk_edit_mode(self, *args):
        bpy.context.object.use_shape_key_edit_mode = not bpy.context.object.use_shape_key_edit_mode
    
    @undoable
    def handle_faceset_from_edit(self, *args):
        bpy.ops.object.mode_set(mode='SCULPT')
        bpy.ops.sculpt.face_sets_create(mode='SELECTION')
        
    @undoable
    def handle_faceset_from_visible(self, *args):
        bpy.ops.sculpt.face_sets_create(mode='VISIBLE')
    @undoable
    def handle_asign_weight(self, *args):
        # print('self.weight2',self.weight)
        from fractions import Fraction
        weight=float(Fraction(self.weight))
        # print(' weight', weight)
        
        bpy.ops.kourin.set_weight(weight=weight,normalize="None",type_another_mode='REPLACE')
        if bpy.context.mode=='EDIT_MESH':
            self.handle_edit_to_paint_with_a()
        print('权重设置为',weight)
    @undoable
    def handle_lazy_weight_toggle(self, *args):
        prop=bpy.context.scene.kourin_weight_transfer_settings
        prop.lazyweight_enable = not prop.lazyweight_enable
        
    @undoable
    def handle_use_automasking_topology(self, *args):
        sculpt = bpy.context.scene.tool_settings.sculpt
        sculpt.use_automasking_topology = not sculpt.use_automasking_topology
        
    @undoable
    def handle_use_automasking_face_sets(self, *args):
        sculpt = bpy.context.scene.tool_settings.sculpt
        sculpt.use_automasking_face_sets = not sculpt.use_automasking_face_sets

    @undoable
    def handle_use_automasking_boundary_edges(self, *args):
        sculpt = bpy.context.scene.tool_settings.sculpt
        sculpt.use_automasking_boundary_edges = not sculpt.use_automasking_boundary_edges
        
    @undoable
    def handle_use_automasking_boundary_face_sets(self, *args):
        sculpt = bpy.context.scene.tool_settings.sculpt
        sculpt.use_automasking_boundary_face_sets = not sculpt.use_automasking_boundary_face_sets
    @undoable
    def handle_smooth_mask(self, *args):
        bpy.ops.sculpt.mask_filter(filter_type='SMOOTH')

    # --- TextButton 原始操作（已包含 btn 参数） ---
    
    
  
    @undoable
    def handle_edit_to_paint_with_a(self):
        # 假设 comfirm_one_arm 存在
        # from ..utils.armature import comfirm_one_arm
        comfirm_one_arm = lambda obj: True # 临时占位
        pos=imgui.get_mouse_pos()
        print(pos)
        if not comfirm_one_arm(bpy.context.active_object):  
            print('有多个可用的骨骼修改器,先禁用多余的')
            return
        for m in bpy.context.active_object.modifiers:
            if m.type == 'ARMATURE' and m.show_viewport and m.object is not None:
                m.object.select_set(True)
        f=bpy.ops.paint.weight_paint_toggle()
        # if f=={'FINISHED'}:
        #     toast_drawer.open_tip("操作完成", seconds=1.0, position=(pos.x, self.ops.region.height-pos.y),font_size=28,text_color=(1,1,1,1))
    @undoable
    def handle_pose_to_paint_with_a(self):
        from ..utils.armature import comfirm_one_arm
        # n=0     
        # for m in bpy.context.active_object.modifiers:
        #     if m.type=='ARMATURE' and m.show_viewport and m.object is not None:
        #         n=n+1
        # if n>1:
        #     self.msg='有多个可用的骨骼修改器,先禁用多余的'
        #     return False
        from .imgui_global import GlobalImgui
        gp=GlobalImgui.get()
        # if gp.last_mesh_obj_ptr is None:
        #     print('没有历史mesh记录')
        #     # self.msg=self.tr('没有历史mesh记录')
        #     return
        # gp.get_last_obj()
        if not comfirm_one_arm(gp.last_mesh_obj):
            print('有多个可用的骨骼修改器,先禁用多余的')
            # self.msg=self.tr('有多个可用的骨骼修改器,先禁用多余的')
            return
        for m in gp.last_mesh_obj.modifiers:
            if m.type=='ARMATURE' and m.show_viewport and m.object is not None:
                m.object.select_set(True)
                gp.last_mesh_obj.select_set(True)
                bpy.context.view_layer.objects.active=gp.last_mesh_obj
        bpy.ops.paint.weight_paint_toggle()
    
    @undoable
    def handle_pose_to_edit(self):
        # from ..utils.armature import comfirm_one_arm

        from .imgui_global import GlobalImgui
        gp=GlobalImgui.get()
    
        bpy.ops.object.posemode_toggle()

        bpy.context.active_object.select_set(False)
        gp.last_mesh_obj.select_set(True)
        bpy.context.view_layer.objects.active=gp.last_mesh_obj
        bpy.ops.object.editmode_toggle()

    
    
    ###权重模式
    

    @undoable
    def handle_weight_by_modi(self):
        from ..utils.armature import comfirm_one_arm,get_arm_modi_obj
        obj=bpy.context.object
        if not comfirm_one_arm(obj):
            # self.msg=self.tr('有多个可用的骨骼修改器,先禁用多余的')
            print('有多个可用的骨骼修改器,先禁用多余的')
            return
        modi_arm=get_arm_modi_obj(obj)
        settings = bpy.context.scene.kourin_weight_transfer_settings
        if not settings.source_object:
            # self.msg=self.tr('先设置权重来源')
            print('先设置权重来源')
            return
        
        mode_t=obj.mode
        bpy.ops.kourin.vg_asign_new_group()
        bpy.ops.object.mode_set(mode='OBJECT')
        if modi_arm:
            pose_t=modi_arm.object.data.pose_position
            modi_arm.object.data.pose_position='REST'
        bpy.ops.kourin.vg_trans_modi()
        modi=obj.modifiers.active
        bpy.ops.object.datalayout_transfer(modifier=modi.name)
        try:
            bpy.ops.object.modifier_apply(modifier=modi.name, report=True)
        except:
            bpy.ops.kourin.apply_modi_with_shapekey(mod_name=modi.name)
        if modi_arm:
            modi_arm.object.data.pose_position=pose_t
        bpy.ops.object.mode_set(mode=mode_t)
    @undoable
    def handle_weight_by_algorithm(self):
        from ..utils.armature import comfirm_one_arm,get_arm_modi_obj
        obj=bpy.context.object
        if not comfirm_one_arm(obj):
            print('有多个可用的骨骼修改器,先禁用多余的')
            return
        modi=get_arm_modi_obj(obj)
        print(1)

        settings = bpy.context.scene.kourin_weight_transfer_settings
        if not settings.source_object:
            print('先设置权重来源')
            # self.msg=self.tr('先设置权重来源')
            # print(self.msg)
            return
        print(2)
        mode_t=obj.mode
        # pose_t=bpy.context.object.data.pose_position = 'POSE'

        bpy.ops.kourin.vg_asign_new_group()
        print(3)
        vg=bpy.context.object.vertex_groups.active
        object_settings = obj.kourin_weight_transfer_settings
        object_settings.vertex_group=vg.name
        bpy.ops.object.mode_set(mode='OBJECT')
        if modi:
            pose_t=modi.object.data.pose_position
            modi.object.data.pose_position='REST'
        bpy.ops.kourin.skin_weight_transfer()
        if modi:
            modi.object.data.pose_position=pose_t
        bpy.ops.object.mode_set(mode=mode_t)
        try:
            obj.vertex_groups.remove(vg) 
        except:
            print('顶点组不存在')
    @undoable
    def handle_paste_basis_pos(self):
        bpy.ops.kourin.paste_to_shapekey()
    @undoable
    def handle_rest_to_pose(self):
        from ..utils.armature import comfirm_one_arm,get_arm_modi_obj
        obj=bpy.context.object
        if not comfirm_one_arm(obj):
            # self.msg=self.tr('有多个可用的骨骼修改器,先禁用多余的')
            print('有多个可用的骨骼修改器,先禁用多余的')
            return
        modi_arm=get_arm_modi_obj(obj)
        modi_arm.object.data.pose_position = 'POSE'

    @undoable
    def handle_pose_clear_grs(self):
        bpy.ops.kourin.pose_clear_grs()
    @undoable
    def handle_sym_to_left(self):
        from .imgui_global import GlobalImgui
        if not comfirm_one_arm(bpy.context.active_object):
            print('有多个可用的骨骼修改器,先禁用多余的')
            # self.msg=self.tr('有多个可用的骨骼修改器,先禁用多余的')
            return
        temp=self.get_mirror_prop()

        GlobalImgui.get().vg_left=True
        GlobalImgui.get().vg_right=False
        GlobalImgui.get().vg_middle=True
        GlobalImgui.get().vg_mul=False
        GlobalImgui.get().vg_select=False

        bpy.ops.kourin.vg_mirror_weight()

        for k in temp:
            setattr(GlobalImgui.get(),k,temp[k])
    def get_mirror_prop(s):
        from .imgui_global import GlobalImgui
        temp={
            'vg_mul':GlobalImgui.get().vg_mul,
            'vg_select':GlobalImgui.get().vg_select,
            'vg_middle':GlobalImgui.get().vg_middle,
            'vg_select':GlobalImgui.get().vg_left,
            'vg_select':GlobalImgui.get().vg_right,
        }
        return temp
    @undoable
    def handle_sym_to_right(self):
        from .imgui_global import GlobalImgui
        if not comfirm_one_arm(bpy.context.active_object):
            print('有多个可用的骨骼修改器,先禁用多余的')
            # self.msg=self.tr('有多个可用的骨骼修改器,先禁用多余的')
            return
        temp=self.get_mirror_prop()

        GlobalImgui.get().vg_left=False
        GlobalImgui.get().vg_right=True
        GlobalImgui.get().vg_middle=True
        GlobalImgui.get().vg_mul=False
        GlobalImgui.get().vg_select=False

        bpy.ops.kourin.vg_mirror_weight()

        for k in temp:
            setattr(GlobalImgui.get(),k,temp[k])

    @undoable
    def handle_weight_mirror(self):
        from .imgui_global import GlobalImgui
        if not comfirm_one_arm(bpy.context.active_object):
            print('有多个可用的骨骼修改器,先禁用多余的')
            # self.msg=self.tr('有多个可用的骨骼修改器,先禁用多余的')
            return
        temp=self.get_mirror_prop()

        GlobalImgui.get().vg_left=False
        GlobalImgui.get().vg_right=False
        GlobalImgui.get().vg_middle=False
        GlobalImgui.get().vg_mul=False
        GlobalImgui.get().vg_select=False

        bpy.ops.kourin.vg_mirror_weight()

        for k in temp:
            setattr(GlobalImgui.get(),k,temp[k])
    @undoable
    def handle_weight_cut(self):
        bpy.ops.kourin.copy_vertex_group_weights()
    @undoable
    def handle_weight_cut_combine(self):
        bpy.ops.kourin.combine_selected_bone_weights(delete=False)


    @undoable
    def handle_weight_paste(self):

        bpy.ops.kourin.paste_vertex_group_weights()
    @undoable
    def handle_vg_asign(self):
        bpy.ops.kourin.vg_asign_new_group()
    @undoable
    def handle_surface_deform(self):
        from ..imgui_setup.imgui_global import GlobalImgui as gp
        # 备份
        this_obj=bpy.context.active_object
        bpy.ops.kourin.vg_asign_new_group()
        vg=bpy.context.object.vertex_groups.active
        mode_t=this_obj.mode
        selected_t=bpy.context.selected_objects
        scene_settings = bpy.context.scene.kourin_weight_transfer_settings
        source_object=scene_settings.source_object
        #开始
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.kourin.load_surfacedeform(file_name=gp.get().surface_deform_name + '_fitting_surface')
        surface_obj=bpy.context.active_object
        bpy.ops.object.shape_key_clear()
        sk_surface_obj=surface_obj.data.shape_keys.key_blocks
        sk_num=len(surface_obj.data.shape_keys.key_blocks)
        temp_objs=[]#创建了根据sk命名的临时obj
        for i in range(sk_num):
            if i:
                o = this_obj.copy()
                o.data = this_obj.data.copy()
                o.name = f'temp_{sk_surface_obj[i].name}'
                o.data.name = f'temp_{sk_surface_obj[i].name}'
                bpy.context.collection.objects.link(o)
                temp_objs.append(o)
                print('temp创建完成',i,o.name)
        #切换this_obj绑定到sk_surface_obj,依次切换value
        bpy.ops.object.select_all(action='DESELECT')
        
        # for o in temp_objs:
        #     print('temp_objs',o.name)
        #     mod=o.modifiers.new('temp_sd','SURFACE_DEFORM')     
        #     mod.target=surface_obj
        #     mod.vertex_group=vg.name
        #     o.select_set(True)
        #     bpy.context.view_layer.objects.active=o
        #     if o.data.shape_keys:
        #         bpy.ops.object.shape_key_clear()
        #         bpy.ops.object.shape_key_remove(all=True, apply_mix=True)

        #     print('设置激活')
        #     sk_surface_obj[o.name[5:]].value=0
        #     bpy.ops.object.surfacedeform_bind(modifier=mod.name)
        for o in temp_objs:
            print('temp_objs', o.name)
            mod = o.modifiers.new('temp_sd', 'SURFACE_DEFORM')     
            mod.target = surface_obj
            mod.vertex_group = vg.name
            
            # 使用 context override，避免修改全局上下文
            with bpy.context.temp_override(
                active_object=o,
                selected_objects=[o],
                object=o
            ):
                if o.data.shape_keys:
                    bpy.ops.object.shape_key_clear()
                    o.active_shape_key_index=0
                    bpy.ops.object.shape_key_remove(all=True, apply_mix=True)
                
                print('设置激活')
                sk_surface_obj[o.name[5:]].value = 0
                bpy.ops.object.surfacedeform_bind(modifier=mod.name)

                print('设置绑定')
                sk_surface_obj[o.name[5:]].value=1
                bpy.ops.object.modifier_apply(modifier=mod.name)

            # bpy.ops.kourin.apply_modi_with_shapekey(mod_name=mod.name)
            # print('设置应用')
            sk_surface_obj[o.name[5:]].value=0
            o.select_set(False)
        #合并到this_obj
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active=this_obj
        this_obj.select_set(True)
        object_settings = this_obj.kourin_weight_transfer_settings
        object_settings.vertex_group=vg.name
        #传权重
        scene_settings.source_object=surface_obj
        bpy.ops.kourin.skin_weight_transfer()
        for o in temp_objs:
            o.select_set(True)
        bpy.ops.object.join_shapes()
        for o in temp_objs:
            bpy.data.meshes.remove(o.data)
        bpy.data.meshes.remove(surface_obj.data)
        
        for sk in this_obj.data.shape_keys.key_blocks:
            if 'temp' in sk.name:
                sk.name=sk.name[5:]

        # bpy.ops.kourin.skin_weight_transfer()
        #还原设置
        bpy.ops.object.select_all(action='DESELECT')
        for o in selected_t:
            o.select_set(True)
        bpy.context.view_layer.objects.active=this_obj
        scene_settings.source_object=source_object
        bpy.ops.object.mode_set(mode=mode_t)
        
    @undoable
    def handle_surface_deform_loose(self):
        from ..imgui_setup.imgui_global import GlobalImgui as gp
        # 备份
        this_obj=bpy.context.active_object
        bpy.ops.kourin.vg_asign_new_group()
        vg=bpy.context.object.vertex_groups.active
        mode_t=this_obj.mode
        selected_t=bpy.context.selected_objects
        scene_settings = bpy.context.scene.kourin_weight_transfer_settings
        source_object=scene_settings.source_object
        #开始
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.kourin.load_loose_surfacedeform(file_name=gp.get().surface_deform_name + '_loose_surface')
        surface_obj=bpy.context.active_object
        bpy.ops.object.shape_key_clear()
        sk_surface_obj=surface_obj.data.shape_keys.key_blocks
        sk_num=len(surface_obj.data.shape_keys.key_blocks)
        temp_objs=[]#创建了根据sk命名的临时obj
        for i in range(sk_num):
            if i:
                o = this_obj.copy()
                o.data = this_obj.data.copy()
                o.name = f'temp_{sk_surface_obj[i].name}'
                o.data.name = f'temp_{sk_surface_obj[i].name}'     
                bpy.context.collection.objects.link(o)
                temp_objs.append(o)
                print('temp创建完成',i)
        #切换this_obj绑定到sk_surface_obj,依次切换value
        bpy.ops.object.select_all(action='DESELECT')
        for o in temp_objs:
            mod=o.modifiers.new('temp_sd','SURFACE_DEFORM')     
            mod.target=surface_obj
            mod.vertex_group=vg.name

            with bpy.context.temp_override(
                active_object=o,
                selected_objects=[o],
                object=o
            ):
                if o.data.shape_keys:
                    bpy.ops.object.shape_key_clear()
                    o.active_shape_key_index=0
                    bpy.ops.object.shape_key_remove(all=True, apply_mix=True)
                
                print('设置激活')
                sk_surface_obj[o.name[5:]].value = 0
                bpy.ops.object.surfacedeform_bind(modifier=mod.name)

                print('设置绑定')
                sk_surface_obj[o.name[5:]].value=1
                bpy.ops.object.modifier_apply(modifier=mod.name)

            # bpy.ops.kourin.apply_modi_with_shapekey(mod_name=mod.name)
            # print('设置应用')
            sk_surface_obj[o.name[5:]].value=0
            o.select_set(False)
        #合并到this_obj
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active=this_obj
        this_obj.select_set(True)
        object_settings = this_obj.kourin_weight_transfer_settings
        object_settings.vertex_group=vg.name
        #传权重
        scene_settings.source_object=surface_obj
        bpy.ops.kourin.skin_weight_transfer()
        for o in temp_objs:
            o.select_set(True)
        bpy.ops.object.join_shapes()
        for o in temp_objs:
            bpy.data.meshes.remove(o.data)
        bpy.data.meshes.remove(surface_obj.data)
        
        for sk in this_obj.data.shape_keys.key_blocks:
            if 'temp' in sk.name:
                sk.name=sk.name[5:]

        # bpy.ops.kourin.skin_weight_transfer()
        #还原设置
        bpy.ops.object.select_all(action='DESELECT')
        for o in selected_t:
            o.select_set(True)
        bpy.context.view_layer.objects.active=this_obj
        scene_settings.source_object=source_object
        bpy.ops.object.mode_set(mode=mode_t)
    
    
    # def handle_surface_deform_loose(self):
    @undoable
    def handle_compute(self):
        """
        Called when user clicks Recompute Now.
        If running inside Blender and operator exists, call it.
        Otherwise simulate with demo values.
        """

        from .imgui_global import GlobalImgui
        gp=GlobalImgui.get()

        try:
            # Try calling the operator you registered in Blender
            op = bpy.ops.kourin.recompute_overinfluence()

            self._refresh_cached_labels()

        except Exception:
            pass
    @undoable
    def handle_show_excessive(self):
        """
        Toggle drawing on Blender side if possible; otherwise toggle demo flag.
        """
  
        try:
            bpy.ops.kourin.toggle_draw_overinfluence()
    
        except Exception:
            pass

        # self._update_toggle_text()
    @undoable
    def handle_rm_excessive(self):
        """
        Toggle drawing on Blender side if possible; otherwise toggle demo flag.
        """
  
        try:
            bpy.ops.kourin.remove_extra_weights()
    
        except Exception:
            pass
        return None
        # self._update_toggle_text()

    # def _update_toggle_text(self):
    #     self.btn_toggle.setText("绘制:开" if STATE.drawing_enabled else "绘制:关")

    def _refresh_cached_labels(self):
        from .imgui_global import GlobalImgui
        gp=GlobalImgui.get()
        self.lbl_cached_obj.setText(f"物体: {gp._cached_obj_name if gp._cached_obj_name else '—'}")
        self.lbl_cached_count.setText(f"顶点: {gp._cached_over_count}")
    @undoable
    def handle_check_scene(self):
        from .imgui_global import GlobalImgui
        gp=GlobalImgui.get()
        import bpy, re
        results = []

        # 1. 材质重复后缀
        dup_mat = [m.name for m in bpy.data.materials if re.search(r"\.\d{3,}$", m.name)]
        results.append(f"重复后缀的材质: {', '.join(dup_mat) or '无'}")

        # 2. Mesh 重复后缀
        dup_mesh = [o.name for o in bpy.data.objects 
                    if o.type == 'MESH' and re.search(r'\.\d{3,}$', o.name)]
        results.append(f"重复后缀的Mesh: {', '.join(dup_mesh) or '无'}")

        # 3. 多 UV 层
        uv_multi = [f"{o.name} ({len(o.data.uv_layers)}个UV)" 
                    for o in bpy.data.objects
                    if o.type == 'MESH' and len(o.data.uv_layers) > 1]
        results.append(f"多UV层Mesh: {', '.join(uv_multi) or '无'}")

        # 4. UV 分组
        uv_group = {}
        for obj in bpy.data.objects:
            if obj.type == 'MESH' and obj.data.uv_layers:
                for layer in obj.data.uv_layers:
                    uv_group.setdefault(layer.name, []).append(obj.name)

        if len(uv_group) > 1:
            results.append("UV层分组:")
            for uv_name, objs in uv_group.items():
                results.append(f"  {uv_name}: {', '.join(objs)}")
        elif len(uv_group) == 0:
            results.append("无UV层检测到")

        # 5. 多余集合
        def collect_extra(layer_col, base_names):
            extras = []
            for child in layer_col.children:
                if child.name not in base_names:
                    extras.append(child.name)
                extras.extend(collect_extra(child, base_names))
            return extras

        root = bpy.context.view_layer.layer_collection
        base_names = {root.name, 'Collection'}
        extra_cols = collect_extra(root, base_names)
        results.append(f"删除多余集合: {', '.join(extra_cols) or '无'}")

        # 6. 骨骼父级检查
        arm = next((o for o in bpy.context.scene.objects if o.type == 'ARMATURE'), None)
        if arm:
            non_child = [o.name for o in bpy.context.scene.objects 
                        if o.parent != arm and o != arm]
            results.append(f"没把骨骼设为父级: {', '.join(non_child) or '无'}")
        else:
            results.append("场景中无骨骼Armature")

        # 7. 灯光 / 相机
        lights = [o.name for o in bpy.context.scene.objects if o.type == 'LIGHT']
        cams = [o.name for o in bpy.context.scene.objects if o.type == 'CAMERA']
        results.append(f"删除灯光对象: {', '.join(lights) or '无'}")
        results.append(f"删除相机对象: {', '.join(cams) or '无'}")
        # print(results)
        gp.check_scene_result=results
        def draw_uv_result(win):
                    imgui.text("UV 检查结果：")
                    imgui.separator()
                    for line in win["content"]:
                        if line.startswith("  "):
                            # imgui.indent(20)
                            # imgui.text_colored(imgui.ImVec4(1.0, 0.4, 0.4, 1.0),line)
                            # imgui.unindent(20)
                            imgui.push_style_color(imgui.Col_.text, imgui.ImVec4(1.0, 0.4, 0.4, 1.0))
                            imgui.text_wrapped(line)
                            imgui.pop_style_color()
                        else:
                            imgui.text_wrapped(line)
                
        GlobalImgui.get().window_mgr.open_window(
            "检查场景结果",
            content=GlobalImgui.get().check_scene_result,
            draw_callback=draw_uv_result,
            force_open=True  # 允许重新打开
        )
        return None



    @undoable
    def handle_clean_scene(self):
        from .imgui_global import GlobalImgui
        results = []
        # 当前视图层可见对象
        visible_objs = set(bpy.context.view_layer.objects)
        removed_names = []
        # 清理不在视图层或未链接到集合的Mesh对象
        for obj in list(bpy.data.objects):
            if obj.type == 'MESH':
                in_col = bool(obj.users_collection)
                if obj not in visible_objs or not in_col:
                    removed_names.append(obj.name)
                    bpy.data.objects.remove(obj, do_unlink=True)
        results.append("删除对象: "+f"{', '.join(removed_names) or '无'}")

        # 清理孤立的 Mesh 数据块
        removed_mesh_data = []
        for mesh in list(bpy.data.meshes):
            if mesh.users == 0:
                removed_mesh_data.append(mesh.name)
                bpy.data.meshes.remove(mesh)
        results.append("删除Mesh数据: "+f"{', '.join(removed_mesh_data) or '无'}")

        # 清理未使用的材质，包括 fake user
        removed_mats = []
        for mat in list(bpy.data.materials):
            if getattr(mat, 'use_fake_user', False):
                mat.use_fake_user = False
            if mat.users == 0:
                removed_mats.append(mat.name)
                bpy.data.materials.remove(mat)
        results.append("删除材质: "+f"{', '.join(removed_mats) or '无'}")

        # 更新结果视图
        def update_view():
            # self.result_view.setPlainText("\n".join(results))
            return "\n".join(results)
        # bpy.app.timers.register(update_view)
        GlobalImgui.get().clean_scene_result=update_view()
        return None


# --- 2. 图像按钮（继承 ButtonActions） ---
class ImageButton(ButtonActions):
    def __init__(self):
        # 默认参数
        self.btn_dict = {
            'image_size': imgui.ImVec2(20.0, 20.0),
            'uv0': imgui.ImVec2(0, 0),
            'uv1': imgui.ImVec2(1, 1),
            'bg_col': imgui.ImVec4(0.1, 0.1, 0.1, 0.0),  # 黑色背景
            'tint_col': imgui.ImVec4(1.0, 1.0, 1.0, 1.0),  # 白色图像
            'tp':'',
            'close':True,
            'ops':None,
            'report':True,
        }

    def new(self, btn, texture_id, **kwargs):
        """
        自定义的 image_button 函数
        """
        params = {**self.btn_dict, **kwargs}
        if isinstance(texture_id, int):
            tex_ref = imgui.ImTextureRef(texture_id)
        else:
            tex_ref = texture_id
            
        clicked = imgui.image_button(
            btn,
            tex_ref,
            params['image_size'],
            params['uv0'],
            params['uv1'],
            params['bg_col'],
            params['tint_col'],

        )
        self.ops=params['ops']
        if not self.ops:
            self.report=False
        else:
            self.report=params['report']
        # ... (工具提示逻辑保持不变)
        if not params['tp']=='':
            if imgui.is_item_hovered():
                imgui.begin_tooltip()
                side=5
                imgui.dummy((-side, 0)) 
                imgui.same_line()
                imgui.text(params['tp'])
                imgui.same_line()
                imgui.dummy((-side, 0)) 
                imgui.dummy((0, 0)) 
                imgui.end_tooltip()

        if clicked:
            # 关键：调用继承自 ButtonActions 的处理函数
            done=self.button_handler(btn) 
            if self.report and done:
                pos=imgui.get_mouse_pos()
                toast_drawer.open_tip("操作完成", seconds=1.0, position=(pos.x, self.ops.region.height-pos.y),font_size=28,text_color=(1,1,1,1))
            if params['close']:
                from .imgui_global import GlobalImgui
                GlobalImgui.get().close_ui=params['close']
        return clicked

# --- 3. 文本按钮（继承 ButtonActions） ---
class TextButton(ButtonActions):
    def __init__(self):
        # 默认参数
        self.btn_dict = {
            'tp':'',
            'condition':'',
            'close':True,
            'ops':None,
            'report':True,
            'size':None,
        }

    def new(self, btn, **kwargs):
        """
        自定义的 text_button 函数
        """
        params = {**self.btn_dict, **kwargs}
        self.ops=params['ops']
        if not self.ops:
            self.report=False
        else:
            self.report=params['report']
        if params['size']:
            clicked = imgui.button(btn,params['size'])
        else:
            clicked = imgui.button(btn)
        
        # ... (工具提示逻辑保持不变)
        if not params['tp']=='':
            if imgui.is_item_hovered():
                imgui.begin_tooltip()
                side=5
                imgui.dummy((-side, 0)) 
                imgui.same_line()
                imgui.text(params['tp'])
                imgui.same_line()
                imgui.dummy((-side, 0)) 
                imgui.dummy((0, 0)) 
                imgui.end_tooltip()
                
        if clicked:
            # 关键：调用继承自 ButtonActions 的处理函数
            # self.button_handler(btn)
            done=self.button_handler(btn) 
            if self.report and done and not hasattr(self.ops,'ops_name'):
                pos=imgui.get_mouse_pos()
                toast_drawer.open_tip("操作完成", seconds=2.0, position=(pos.x, self.ops.region.height-pos.y),font_size=28,text_color=(1,1,1,1))
            if params['close']:
                from .imgui_global import GlobalImgui
                GlobalImgui.get().close_ui=params['close']
            
        return clicked
        
    def new_toggle(self, btn, **kwargs):
        """Toggle 版本，保持原样"""
        button_color = imgui.ImVec4(0.33, 0.33, 0.33, 1)
        button_active_color = imgui.ImVec4(71/255.0, 114/255.0, 179/255.0, 1)
        params = {**self.btn_dict, **kwargs}
        if params['condition']:
            imgui.push_style_color(imgui.Col_.button.value, button_active_color)
            imgui.push_style_color(imgui.Col_.button_hovered.value, button_active_color)
            imgui.push_style_color(imgui.Col_.button_active.value, button_active_color)
        else:
            imgui.push_style_color(imgui.Col_.button.value, button_color)
            imgui.push_style_color(imgui.Col_.button_hovered.value, button_color)
            imgui.push_style_color(imgui.Col_.button_active.value, button_color)

        # 这里的 new 调用将执行 self.new(btn)
        if self.new(btn, **params):
            # self.new 中已经调用了 self.button_handler(btn)，所以这里不需要重复操作
            pass 

        imgui.pop_style_color()
        imgui.pop_style_color()
        imgui.pop_style_color()



class ImguiWindowManager:
    """
    管理多个 ImGui 窗口（可独立开关、独立内容）
    """
    def __init__(self, owner_self=None):
        # 允许依赖注入（你传入 self）
        self.owner = owner_self
        # 窗口存储：
        # { window_id: { "open": [bool], "content": list[str], "draw": callable } }
        self.windows = {}
    
    # ---------------------------------------
    # 打开或刷新窗口
    # ---------------------------------------
    def open_window(self, window_id, content=None, draw_callback=None, force_open=False):
        """
        打开一个窗口（如果存在则刷新）
        window_id: str
        content: list[str]（默认纯文本列表）
        draw_callback: 自定义绘制函数（可选）
        force_open: bool（是否强制重新打开已关闭的窗口）
        """
        if window_id not in self.windows:
            self.windows[window_id] = {
                "open": [True],  # 使用列表包装，以便引用传递
                "content": content or [],
                "draw": draw_callback,
            }
        else:
            win = self.windows[window_id]
            # 更新内容和回调
            win["content"] = content or []
            win["draw"] = draw_callback or win["draw"]
            # 只有在 force_open=True 或窗口已经是打开状态时才打开
            if force_open or win["open"][0]:
                win["open"][0] = True
    
    # ---------------------------------------
    # 关闭窗口
    # ---------------------------------------
    def close_window(self, window_id):
        """手动关闭窗口"""
        if window_id in self.windows:
            self.windows[window_id]["open"][0] = False
    
    # ---------------------------------------
    # 检查窗口是否打开
    # ---------------------------------------
    def is_window_open(self, window_id):
        """检查窗口是否打开"""
        if window_id in self.windows:
            return self.windows[window_id]["open"][0]
        return False
    
    # ---------------------------------------
    # 绘制所有窗口
    # ---------------------------------------
    def draw_all_windows(self):
        """
        在每帧调用，自动绘制所有窗口
        """
        # 创建待删除列表（避免在迭代中修改字典）
        to_remove = []
        
        for win_id, win in list(self.windows.items()):
            # 如果窗口已关闭，跳过绘制
            if not win["open"][0]:
                continue
            
            # =======================================
            # 关键修复：正确处理 imgui.begin() 的返回值
            # =======================================
            # imgui_bundle 的 begin() 返回 (expanded, opened)
            # expanded: 窗口是否展开（非折叠状态）
            # opened: 窗口是否仍然打开（用户是否点击了关闭按钮）
            expanded, opened = imgui.begin(
                win_id,
                True,  # 传入 True 显示关闭按钮
                imgui.WindowFlags_.no_nav | imgui.WindowFlags_.no_focus_on_appearing
            )
            
            # 用户点击了关闭按钮（X）
            if not opened:
                win["open"][0] = False
                imgui.end()
                continue
            
            # ---------------------------------------
            # 窗口内容绘制（两种方式：回调或纯文本）
            # ---------------------------------------
            if win["draw"] is not None:
                # 使用自定义回调绘制内容
                try:
                    win["draw"](win)
                except Exception as e:
                    imgui.text_colored(imgui.ImVec4(1.0, 0.0, 0.0, 1.0),f"绘制错误: {str(e)}")
            else:
                # 默认：绘制纯文本内容
                for line in win["content"]:
                    imgui.text_wrapped(line)
            
            imgui.end()
    
    # ---------------------------------------
    # 清理所有窗口
    # ---------------------------------------
    def clear_all_windows(self):
        """关闭并清除所有窗口"""
        self.windows.clear()




