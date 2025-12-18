from pathlib import Path
import bpy
from bpy.app.translations import pgettext as _
from ..utils.vertex_group import vg_clean_advanced,vg_clear_unused
from ..imgui_setup.imgui_global import GlobalImgui as GP



class Kourin_vg_clean_advanced(bpy.types.Operator):
    """清理所有顶点组中的非法权重（0、负值、NaN）"""
    
    bl_idname = "kourin.vg_clean_advanced"
    bl_label = "高级清理顶点组 (0/负值/NaN)"
    bl_options = {'UNDO'}
    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH'
    def execute(self, context):
        obj = context.active_object
        report_buffer=vg_clean_advanced(obj)
        if report_buffer:
            final_report = (
                f"清理完成，共发现 {len(report_buffer)} 个非法权重：\n" +
                "\n".join(report_buffer[:10]) + 
                ("\n......" if len(report_buffer)>10 else "")
            )
            self.report({'INFO'}, final_report)
        else:
            self.report({'INFO'}, "未发现需要清理的非法权重")
        context.view_layer.update()
        return {'FINISHED'}
class Kourin_vg_clear_unused(bpy.types.Operator):
    """删除没有使用的顶点组（形变骨骼，修改器），不包括被其他物体使用的顶点组"""

    bl_idname = "kourin.vg_clear_unused"
    bl_label = "删除没有使用的顶点组"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return bpy.context.object is not None

    def execute(self, context):
        '''遍历当前激活骨骼修改器中的骨骼，加入列表，遍历修改器使用的顶点组'''
        obj = bpy.context.object
        vg_clear_unused(obj)
        return {'FINISHED'}
class Kourin_vg_remove_zero(bpy.types.Operator):
    """删除权重为0的顶点组 耗时有点久"""

    bl_idname = "kourin.vg_remove_zero"
    bl_label = "删除权重为0的顶点组"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return bpy.context.object is not None

    def execute(self, context):
        '''遍历所有顶点组，大于0的跳过'''
        obj = bpy.context.object
        unused_vg = []

        # 确保物体是一个网格
        if obj.type == 'MESH':
            # 遍历所有顶点组
            for v_group in obj.vertex_groups:
                used = False  # 假设顶点组未被使用

                # 遍历所有顶点检查是否属于当前顶点组
                for vertex in obj.data.vertices:
                    for group in vertex.groups:
                        if group.group == v_group.index and group.weight != 0:
                            used = True  # 顶点分配给顶点组
                            break

                    if used:
                        break  # 退出顶点循环

                # 输出顶点组及其使用状态
                if not used:
                    unused_vg.append(v_group.name)
            for vg_name in unused_vg:
                obj.vertex_groups.remove(obj.vertex_groups[vg_name])

        return {'FINISHED'}
class Kourin_vg_metarig_to_rig(bpy.types.Operator):
    """将顶点组转换为rigifiy类型"""

    bl_idname = "kourin.vg_metarig_to_rigify"
    bl_label = "将顶点组转换为rigifiy类型"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return bpy.context.object is not None

    def execute(self, context):
        for i in bpy.context.object.vertex_groups:
            if i.name[:4] != 'DEF-':
                i.name = 'DEF-' + i.name
        return {'FINISHED'} 
class Kourin_vg_remove_zerofast(bpy.types.Operator):
    """快速删除权重全为 0 的顶点组"""
    bl_idname = "kourin.vg_rm_all_unused"
    bl_label = "快速删除权重为0的顶点组"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return 1

    def execute(self, context):
        for obj in bpy.context.scene.objects:
            if obj.type=='MESH' and len(obj.vertex_groups):
                mesh = obj.data
                
                # —— 一次遍历：收集所有“有非零权重”的顶点组索引 —— 
                used_indices = set()
                for v in mesh.vertices:
                    for g in v.groups:
                        if g.weight != 0.0:
                            used_indices.add(g.group)
                
                # —— 所有顶点组索引 —— 
                all_indices = {vg.index for vg in obj.vertex_groups}
                
                # —— 需要删除的那些组 —— 
                to_remove = sorted(all_indices - used_indices, reverse=True)
                # reverse=True 保证按从大到小删除，不会破坏索引顺序
                
                for idx in to_remove:
                    # 根据 index 找到 Group，然后删除
                    vg = obj.vertex_groups[idx]
                    obj.vertex_groups.remove(vg)

        return {'FINISHED'}
class Kourin_vg_rig_to_metarig(bpy.types.Operator):
    """将顶点组转换为metarig类型，去除def前缀"""

    bl_idname = "kourin.vg_rigify_to_metarig"
    bl_label = "去除顶点组DEF前缀"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return bpy.context.object is not None

    def execute(self, context):
        for i in bpy.context.object.vertex_groups:
            if i.name[:4] == 'DEF-':
                i.name = i.name[4:]
        return {'FINISHED'}


import re

sides = [
    {"left": "_L_", "right": "_R_"},
    {"left": "_l_", "right": "_r_"},
    {"left": "_l", "right": "_r"},
    {"left": "_L", "right": "_R"},
    {"left": ".l", "right": ".r"},
    {"left": ".L", "right": ".R"},
    {"left": "Left", "right": "Right"},
    {"left": "left", "right": "right"},
]


def determine_and_convert(vertex_group_name: str, LR: str = None):
    """
    参数：
      vertex_group_name: 要检测或转换的顶点组名称
      LR: '-x' 只检测并替换左侧标签
          '+x' 只检测并替换右侧标签
          'center' 只检测是否为中间（既不含左也不含右），不替换
          None 双向替换左右标签
    返回： [是否匹配, 匹配到的标签, (转换后名称或原名称)]
    """
    def _pattern_for(tag: str) -> str:
        # 前缀标签：r_ 或 l_ 形式，需要前边界
        if re.match(r"^[rR]_$|^[lL]_", tag):
            return rf"(?:(?<=^)|(?<=[^A-Za-z])){re.escape(tag)}"
        # 后缀标签： _r 或 _l 形式，需要后边界
        if re.search(r"_[rRlL]$", tag):
            return rf"{re.escape(tag)}(?:(?=$)|(?=[^A-Za-z]))"
        # 其它标签（如 .L/.R/Left/Right）使用完整匹配
        return re.escape(tag)

    # 根据 LR 构建要匹配的模式列表及替换映射
    patterns = []
    replace_map = {}
    for side in sides:
        left, right = side["left"], side["right"]
        if LR == "-x":
            patterns.append(_pattern_for(left))
            replace_map[left] = right
        elif LR == "+x":
            patterns.append(_pattern_for(right))
            replace_map[right] = left
        elif LR == "center":
            patterns.append(_pattern_for(left))
            patterns.append(_pattern_for(right))
            # 不构建替换表
        else:  # LR is None
            patterns.append(_pattern_for(left))
            patterns.append(_pattern_for(right))
            replace_map[left] = right
            replace_map[right] = left
    patterns = sorted(patterns, key=len, reverse=True)
    regex = re.compile("|".join(patterns))

    if LR == "center":
        # 中心：不含任何左右标签即为中间
        return [not bool(regex.search(vertex_group_name)), None, vertex_group_name]

    # 寻找所有匹配
    matches = list(regex.finditer(vertex_group_name))
    if not matches:
        return [False, None, vertex_group_name]

    # 只替换最后一个匹配
    last = matches[-1]
    tag = last.group(0)
    start, end = last.span()
    new_name = vertex_group_name[:start] + replace_map.get(tag, tag) + vertex_group_name[end:]

    return [True, tag, new_name]

def clean_vertex_groups(obj, keep_groups):
    """
    删除不在 keep_groups 列表中的顶点组。

    :param obj: 要处理的Blender对象。
    :param keep_groups: 要保留的顶点组名称列表。
    """
    # 确保对象有顶点组
    if not hasattr(obj, 'vertex_groups'):
        print(_("The object does not have vertex groups."))
        return

    # 循环遍历顶点组
    for vg in obj.vertex_groups[:]:
        if vg.name not in keep_groups:
            # 删除不在列表中的顶点组
            obj.vertex_groups.remove(vg)


def check_for_matching_pairs(string_list, sides):
    # 对于每对标识符，检查是否在列表中的某个字符串中出现
    for side in sides:
        left_pattern = re.compile(re.escape(side['left']))
        right_pattern = re.compile(re.escape(side['right']))

        left_exists = any(left_pattern.search(string) for string in string_list)
        right_exists = any(right_pattern.search(string) for string in string_list)

        if left_exists and right_exists:
            print(_("Found matching pairs:"))
            return True  # 找到至少一对匹配的标识符

    return False


class Kourin_mirror_weight(bpy.types.Operator):
    """Mirror vertex groups weights"""

    bl_idname = "kourin.vg_mirror_weight"
    bl_label = "Mirror weights"
    bl_options = {'UNDO'}
    # 这里可以定义一些属性，如文字信息等
    message: bpy.props.StringProperty(default=_("Multiple vertex groups will be mirrored."))

    @classmethod
    def poll(cls, context):
        model_a = bpy.context.view_layer.objects.active
        return model_a is not None and model_a.type == 'MESH' and len(model_a.vertex_groups)

    def invoke(self, context, event):

        if GP.get().vg_mul:
        # if bpy.context.object.mirror_settings.is_multiple:
            wm = context.window_manager
            return wm.invoke_props_dialog(self)
        else:
            # 如果条件不满足，可以直接执行execute，或者返回{'CANCELLED'}
            return self.execute(context)

    def draw(self, context):
        layout = self.layout
        # 在弹出框中显示信息
        layout.label(text=self.message)

    def mirror_based_on_selection(self):
        '''返回选择的顶点组'''
        # 获取当前活动对象
        objs = bpy.context.selected_objects
        rig = next((obj for obj in objs if obj.type == 'ARMATURE'), None)
        if not rig:
            return {'CANCELLED'}

        # 获取选择顶点组
        select_vg = []
        for b in rig.pose.bones:
        # for b in rig.data.bones:
            if b.select:
                select_vg.append(b.name)
        return select_vg

    def mirror_based_on_LR(self):
        '''返回左右两边的其中一边的顶点组'''
        obj = bpy.context.object
        v_groups = []
        if GP.get().vg_left:
            LR='-x'
        else:
            LR='+x'
        # LR = ms.left_right
        if obj.type == 'MESH':

            for vg in obj.vertex_groups:
                if determine_and_convert(vg.name, LR)[0]:
                    v_groups.append(vg.name)
        return v_groups

    def mirror_based_on_center(self):
        '''返回处于模型中心的顶点组'''
        obj = bpy.context.object
        v_groups = []

        if obj.type == 'MESH':
            for vg in obj.vertex_groups:
                if determine_and_convert(vg.name, 'center')[0]:
                    v_groups.append(vg.name)
        return v_groups

    def create_mirrored(self, model_a, name_weight, name_trans):
        '''创建权重模型，权重转移模型，
        返回原模型，
        权重模型，
        传输模型，
        激活顶点组名'''
        # 获取当前激活的模型A

        # 记录模型A当前激活顶点组a_g的名称
        active_vg_name = model_a.vertex_groups.active.name

        # 创建模型B和模型C为模型A的副本
        model_b = model_a.copy()
        model_b.data = model_a.data.copy()
        model_b.name = name_weight
        model_b.data.name = name_weight
        bpy.context.collection.objects.link(model_b)

        model_c = model_a.copy()
        model_c.data = model_a.data.copy()
        model_c.name = name_trans
        model_c.data.name = name_trans

        bpy.context.collection.objects.link(model_c)

        bpy.context.view_layer.objects.active = model_b
        return model_b, model_c, active_vg_name

    def symmetriy_ops(self, model_b):
        '''对称中间骨权重'''
        # 激活模型B
        # 添加并应用镜像修改器
        mirror_mod = model_b.modifiers.new(name="Mirror", type='MIRROR')
        mirror_mod.use_axis[0] = True
        mirror_mod.use_bisect_axis[0] = True
        if GP.get().vg_left:
        # if ms.left_right == '-x':
            mirror_mod.use_bisect_flip_axis[0] = False
        else:
            mirror_mod.use_bisect_flip_axis[0] = True

        for window in bpy.context.window_manager.windows:
            screen = window.screen
            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    with bpy.context.temp_override(window=window, area=area, active_object=model_b):
                        # bpy.ops.screen.screen_full_area()
                        if model_b.active_shape_key is not None:
                            if model_b.active_shape_key.value or model_b.show_only_shape_key:
                                bpy.ops.object.shape_key_remove(all=True, apply_mix=True)
                        model_b.shape_key_clear()

                        bpy.ops.object.modifier_apply(modifier='Mirror')
                    break

        # 添加并应用切分修改器

    def transfer_vg(self, origin, source, result):

        '''转移权重，应用修改器'''
        bpy.context.view_layer.objects.active = result
        result.select_set(True)

        # 为模型C添加DataTransfer修改器，传递模型B的顶点组
        bpy.context.view_layer.objects.active = result
        result.select_set(True)
        data_transfer_mod = result.modifiers.new(name="DataTransferC", type='DATA_TRANSFER')
        data_transfer_mod.object = source
        data_transfer_mod.use_vert_data = True
        data_transfer_mod.data_types_verts = {'VGROUP_WEIGHTS'}
        if not GP.get().vg_mirror_search:
        # if origin.mirror_settings.mirror_method == 'POLYINTERP_NEAREST':
            data_transfer_mod.vert_mapping = 'POLYINTERP_NEAREST'
        else:
            data_transfer_mod.vert_mapping = 'NEAREST'
        # 应用DataTransfer修改器到模型C
        for window in bpy.context.window_manager.windows:
            screen = window.screen
            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    with bpy.context.temp_override(window=window, area=area, active_object=source):
                        # bpy.ops.screen.screen_full_area()
                        bpy.ops.object.datalayout_transfer(modifier="DataTransferC")
                        bpy.ops.object.modifier_apply(modifier="DataTransferC")
                    break

    def execute(self, context):

        temp_mode = context.object.mode
        maybe_a=[]
        true_a=None
        pose_position=False
        for o in context.selected_objects:
            if o.type=='ARMATURE':
                maybe_a.append(o)
        if len(context.object.modifiers):#确保只有一个可用的骨骼修改器
            n=0
            for m in context.object.modifiers:
                if m.type=='ARMATURE' and m.show_viewport and m.object:
                    n=n+1
            if n>1:
                self.msg='有多个可用的骨骼修改器,先禁用多余的'
                self.report({"INFO"}, _(self.msg))
                bpy.ops.object.mode_set(mode=temp_mode)
                return {'CANCELLED'}
            for m in context.object.modifiers:
                if m.type=='ARMATURE' and m.show_viewport and m.object:
                    if m.object in maybe_a and m.object.mode=='POSE':
                        pose_position=m.object.data.pose_position
                        true_a=m.object
                        m.object.data.pose_position = 'REST'

        # 确保Blender处于对象模式
        bpy.ops.object.mode_set(mode='OBJECT')
        model_a = context.view_layer.objects.active
        model_a.select_set(True)
        if not hasattr(model_a.vertex_groups.active,'name'):
            self.report({"INFO"}, _("选中了没权重的骨骼!"))
            bpy.ops.object.mode_set(mode=temp_mode)
            if true_a:
                true_a.data.pose_position=pose_position
            return {'CANCELLED'}
        # ms = model_a.mirror_settings
        '''按选择骨骼镜像时，处理方式不同'''
        # 处理选择的骨骼顶点组 权重
        if GP.get().vg_select:
        # if ms.is_selected:
            v_groups = self.mirror_based_on_selection()
            if check_for_matching_pairs(v_groups, sides):
                self.report({"ERROR"}, "You cannot select both left and right bones simultaneously!")
                bpy.ops.object.mode_set(mode=temp_mode)
                if true_a:
                    true_a.data.pose_position=pose_position
                return {'CANCELLED'}
            # 对称权重
            model_b_sym, model_c_sym, active_vg_name = self.create_mirrored(model_a, 'model_b_sym', 'model_c_sym')
            self.symmetriy_ops( model_b_sym)
            self.transfer_vg(model_a, model_b_sym, model_c_sym)

            # 镜像权重
            model_b_mir, model_c_mir, active_vg_name = self.create_mirrored(model_a, 'model_b_mir', 'model_c_mir')
            model_b_mir.scale.x *= -1
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
            self.transfer_vg(model_a, model_b_mir, model_c_mir)


        # 处理单个顶点组
        else:
            model_b, model_c, active_vg_name = self.create_mirrored(model_a, 'model_b', 'model_c')
            if GP.get().vg_middle:
            # if ms.is_center:
                self.symmetriy_ops(model_b)
            else:
                # 在X轴上缩放模型B为-1，实现镜像
                model_b.scale.x *= -1
                bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
            self.transfer_vg(model_a, model_b, model_c)
        # 确保变更生效
        # bpy.context.view_layer.update()

        # 单个顶点组
        if not GP.get().vg_mul:
        # if not ms.is_multiple:
            # 清理模型C的顶点组，只留下a_g
            clean_vertex_groups(model_c, [active_vg_name])

            # 更改镜像后的顶点组名称
            if GP.get().vg_middle:
            # if ms.is_center:
                mirrored = model_c.vertex_groups.active.name
            else:
                mirrored = determine_and_convert(model_c.vertex_groups.active.name)[2]
            model_c.vertex_groups.active.name = mirrored
            # 为模型A添加DataTransfer修改器，传递模型C的a_g顶点组
            self.transfer_vg(model_a, model_c, model_a)

        # 多个顶点组
        else:

            # 按中间镜像
            if GP.get().vg_middle and not GP.get().vg_select:
            # if ms.is_center and not ms.is_selected:
                v_groups = self.mirror_based_on_center()
                for vg in model_c.vertex_groups[:]:
                    if vg.name not in v_groups:
                        model_c.vertex_groups.remove(vg)

                self.transfer_vg(model_a, model_c, model_a)
            # 按左右镜像
            elif not GP.get().vg_middle and not GP.get().vg_select:
            # elif not ms.is_center and not ms.is_selected:
                v_groups = self.mirror_based_on_LR()

                for vg in model_c.vertex_groups[:]:
                    if vg.name not in v_groups:
                        model_c.vertex_groups.remove(vg)
                for vg in model_c.vertex_groups[:]:
                    vg.name = determine_and_convert(vg.name)[2]
                self.transfer_vg(model_a, model_c, model_a)
            # 按选择镜像
            elif GP.get().vg_select:
            # elif ms.is_selected:
                v_groups = self.mirror_based_on_selection()

                # 留下中间的顶点组
                for vg in model_c_sym.vertex_groups[:]:
                    # print(vg.name)
                    if not determine_and_convert(vg.name, 'center')[0]:
                        # print(f'shanchu{vg.name}')
                        model_c_sym.vertex_groups.remove(vg)
                clean_vertex_groups(model_c_sym, v_groups)
                # 留下对应的左右边顶点组
                for vg in model_c_mir.vertex_groups[:]:
                    if determine_and_convert(vg.name, 'center')[0]:
                        model_c_mir.vertex_groups.remove(vg)

                clean_vertex_groups(model_c_mir, v_groups)
                for vg in model_c_mir.vertex_groups[:]:
                    vg.name = determine_and_convert(vg.name)[2]
                self.transfer_vg(model_a, model_c_sym, model_a)
                self.transfer_vg(model_a, model_c_mir, model_a)

            # 激活顶点组
            mirrored = determine_and_convert(active_vg_name)[2]
        try:
            bpy.data.meshes.remove(model_b.data)
            bpy.data.meshes.remove(model_c.data)

        except:
            bpy.data.meshes.remove(model_b_mir.data)
            bpy.data.meshes.remove(model_b_sym.data)
            bpy.data.meshes.remove(model_c_mir.data)
            bpy.data.meshes.remove(model_c_sym.data)

        model_a.vertex_groups.active_index = model_a.vertex_groups.find(mirrored)
        bpy.context.view_layer.objects.active = model_a
        bpy.ops.object.mode_set(mode=temp_mode)
        #还原骨架的姿态
        if true_a:
            true_a.data.pose_position=pose_position

        self.report({"INFO"}, _("Mirror completed!"))
        return {'FINISHED'}

class Kourin_vg_asign_new_group(bpy.types.Operator):
    """ctrl G """
    bl_idname = "kourin.vg_asign_new_group"
    bl_label = "Ctrl G 新建组"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type=='MESH'

    def execute(self, context):
        obj = context.object
        if not obj or obj.type != 'MESH':
            return {'CANCELLED'}
        mode_t=obj.mode
        vg_w_t=context.scene.tool_settings.vertex_group_weight
        use_auto_normalize_t=context.scene.tool_settings.use_auto_normalize
        bpy.ops.object.mode_set(mode='EDIT') 
        context.scene.tool_settings.vertex_group_weight=1
        context.scene.tool_settings.use_auto_normalize = False

        bpy.ops.object.vertex_group_assign_new()
        context.scene.tool_settings.vertex_group_weight=vg_w_t
        bpy.ops.object.mode_set(mode=mode_t)
        context.scene.tool_settings.use_auto_normalize=use_auto_normalize_t
        return {'FINISHED'}
class Kourin_vg_asign_new_group_for_trans(bpy.types.Operator):
    """ctrl G """
    bl_idname = "kourin.vg_asign_new_group_for_trans"
    bl_label = "Ctrl G 新建组"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type=='MESH'

    def execute(self, context):
        obj = context.object
        if not obj or obj.type != 'MESH':
            return {'CANCELLED'}
        mode_t=obj.mode
        vg_w_t=context.scene.tool_settings.vertex_group_weight
        use_auto_normalize_t=context.scene.tool_settings.use_auto_normalize
        bpy.ops.object.mode_set(mode='EDIT') 
        context.scene.tool_settings.vertex_group_weight=1
        context.scene.tool_settings.use_auto_normalize = False

        bpy.ops.object.vertex_group_assign_new()
        context.scene.tool_settings.vertex_group_weight=vg_w_t
        bpy.ops.object.mode_set(mode=mode_t)
        context.scene.tool_settings.use_auto_normalize=use_auto_normalize_t
        return {'FINISHED'}
class Kourin_vg_rm_select(bpy.types.Operator):
    """把顶点移出顶点组"""
    bl_idname = "kourin.vg_rm_select"
    bl_label = "把顶点移出顶点组"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type=='MESH'

    def execute(self, context):
        obj = context.object
        if not obj or obj.type != 'MESH':
            return {'CANCELLED'}
        if bpy.context.object.mode not in ['EDIT','WEIGHT_PAINT']: 
            return {'CANCELLED'}
        mode_t=obj.mode
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.object.vertex_group_remove_from()
        bpy.ops.object.mode_set(mode=mode_t)
        return {'FINISHED'}
class Kourin_vg_trans_modi(bpy.types.Operator):
    """数据传递修改器"""
    bl_idname = "kourin.vg_trans_modi"
    bl_label = "数据传递修改器"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type=='MESH'

    def execute(self, context):

        obj = context.object
        if not obj or obj.type != 'MESH':
            return {'CANCELLED'}

        mode_t=obj.mode
        bpy.ops.object.mode_set(mode='OBJECT')
        
        
        # 添加 Data Transfer
        mod = obj.modifiers.new(name="TransferToRig", type='DATA_TRANSFER')
        # 源设为已经 rig 的 mesh（假设与 armature 同名后缀）
        settings = bpy.context.scene.kourin_weight_transfer_settings
        mod.object=settings.source_object
        mod.use_vert_data = True
        mod.data_types_verts = {'VGROUP_WEIGHTS'}
        mod.vert_mapping = 'POLYINTERP_NEAREST'
        # mod.generate_data_layers = True
        if obj.vertex_groups.active:
            mod.vertex_group=obj.vertex_groups.active.name
        # 可选设置混合模式
        mod.mix_mode = 'REPLACE'
        mod.mix_factor = 1.0

        bpy.ops.object.mode_set(mode=mode_t)
        return {'FINISHED'}
class Kourin_vg_shrink_modi(bpy.types.Operator):
    """数据传递修改器"""
    bl_idname = "kourin.vg_shrink_modi"
    bl_label = "缩裹修改器"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type=='MESH'

    def execute(self, context):
        obj = context.object
        if not obj or obj.type != 'MESH':
            return {'CANCELLED'}

        mode_t=obj.mode
        bpy.ops.object.mode_set(mode='OBJECT')


        
        # 添加 Data Transfer
        mod = obj.modifiers.new(name="Shrinkwrap", type='SHRINKWRAP')
        # 源设为已经 rig 的 mesh（假设与 armature 同名后缀）
        # mod.object = mesh  # 若骨架本身是 mesh（有权重），这里指向 source mesh
        mod.wrap_mode = 'ABOVE_SURFACE'
        # mod.generate_data_layers = True
        if obj.vertex_groups.active:
            mod.vertex_group=obj.vertex_groups.active.name


        bpy.ops.object.mode_set(mode=mode_t)
        return {'FINISHED'}
class CopyVertexGroupWeights(bpy.types.Operator):
    bl_idname = "kourin.copy_vertex_group_weights"
    bl_label = "Copy Vertex Group Weights"
    bl_description = "复制当前顶点组中选中顶点的权重到临时存储"
# 
    _weight_cache = {}

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.type == 'MESH' and obj.vertex_groups.active

    def execute(self, context):
        obj = context.object
        vg = obj.vertex_groups.active
        bm = bpy.context.object.data
        # 清空缓存
        # from ..imgui_setup.imgui_global import GlobalImgui as GP
        # GP.get()._weight_cache.clear()
        CopyVertexGroupWeights._weight_cache.clear()
        for v in obj.data.vertices:
            # 选中顶点
            if v.select:
                # 在该组中的权重
                for g in v.groups:
                    if g.group == vg.index:
                        CopyVertexGroupWeights._weight_cache[v.index] = g.weight
                        g.weight=0
        self.report({'INFO'}, f"已复制 {len(CopyVertexGroupWeights._weight_cache)} 个顶点权重")
        return {'FINISHED'}

class PasteVertexGroupWeights(bpy.types.Operator):
    bl_idname = "kourin.paste_vertex_group_weights"
    bl_label = "Paste Vertex Group Weights"
    bl_description = "将缓存的顶点权重粘贴到当前顶点组，并与现有权重相加"

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.type == 'MESH' and obj.vertex_groups.active and CopyVertexGroupWeights._weight_cache

    def execute(self, context):
        obj = context.object
        vg = obj.vertex_groups.active
        cache = CopyVertexGroupWeights._weight_cache
        for vidx, w in cache.items():
            # 获取当前顶点的现有权重
            try:
                existing = 0.0
                for g in obj.data.vertices[vidx].groups:
                    if g.group == vg.index:
                        existing = g.weight
                        break
                new_weight = existing + w
                vg.add([vidx], new_weight, 'REPLACE')
            except Exception:
                continue
        self.report({'INFO'}, f"已粘贴 {len(cache)} 个顶点权重（累加）")
        return {'FINISHED'}
    
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Vector

# ----------------- 默认配置 -----------------
DEFAULT_THRESHOLD = 4     # 被超过 4 根影响判定为“过多影响”（即 >4）
DEFAULT_POINT_SIZE = 6.0
POINT_COLOR = (1.0, 0.0, 0.0, 1.0)
KEEP_TOP_N = 4            # 保留最强的前 N 个骨骼影响（保留用于其他操作）
# --------------------------------------------

# _draw_handle = None



# ---------- 帮助函数 ----------
def get_armature_of_obj(obj: bpy.types.Object):
    if obj is None:
        return None
    for mod in obj.modifiers:
        if mod.type == 'ARMATURE' and mod.object is not None:
            return mod.object
    return None

def compute_overinfluenced(obj: bpy.types.Object, threshold: int):
    """
    计算并返回 (indices_list, world_positions_list)；
    规则：统计顶点的 vertex groups 中，名字与 armature bones 匹配且 weight>0 的数量，
    如果数量 > threshold，则认为 over-influenced。
    使用 evaluated mesh 获取变形后位置（尝试）。
    """
    indices = []
    positions = []
    
    if obj is None or obj.type != 'MESH':
        return indices, positions

    arm = get_armature_of_obj(obj)
    bone_names = set()
    if arm and arm.type == 'ARMATURE':
        bone_names = {b.name for b in arm.data.bones}

    # vg index -> name 映射
    vg_index_to_name = {i: vg.name for i, vg in enumerate(obj.vertex_groups)}

    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_mesh = None
    eval_obj = None
    try:
        eval_obj = obj.evaluated_get(depsgraph)
        eval_mesh = eval_obj.to_mesh()
    except Exception:
        eval_mesh = None

    mesh_src = eval_mesh if eval_mesh is not None else obj.data
    mat_world = obj.matrix_world

    # 遍历顶点，使用原始 obj.data.vertices 的 groups 权重判断影响
    for vidx, v in enumerate(mesh_src.vertices):
        # prefer original vertex group weight entries
        try:
            orig_groups = obj.data.vertices[vidx].groups
        except Exception:
            orig_groups = v.groups

        cnt = 0
        for g in orig_groups:
            g_index = g.group
            w = getattr(g, "weight", 0.0)
            if w <= 0.0:
                continue
            name = vg_index_to_name.get(g_index)
            if name and name in bone_names:
                cnt += 1

        if cnt > threshold:
            indices.append(vidx)
            positions.append(mat_world @ v.co)

    # 清理 eval mesh（如果有）
    if eval_mesh is not None and eval_obj is not None:
        try:
            eval_obj.to_mesh_clear()
        except Exception:
            try:
                bpy.data.meshes.remove(eval_mesh)
            except Exception:
                pass

    return indices, positions

# ---------- GPU 绘制回调（**不再计算**，只绘制缓存） ----------
def draw_callback(_self, _context):
    """
    绘制使用缓存的 positions；不会进行任何计算。
    """

    from ..imgui_setup.imgui_global import GlobalImgui as GP
    gp=GP.get()
    if not gp._cached_positions:
        return

    # 仍从场景读取点大小（方便用户调试）
    point_size = gp.overinfluence_point_size

    shader = gpu.shader.from_builtin('POINT_UNIFORM_COLOR')
    # 将 Vector 转为 tuple（若已是 tuple 则不变）
    coords = [tuple(p) for p in gp._cached_positions]
    batch = batch_for_shader(shader, 'POINTS', {"pos": coords})

    gpu.state.depth_test_set('LESS_EQUAL')
    gpu.state.point_size_set(point_size)

    shader.bind()
    shader.uniform_float("color", POINT_COLOR)
    batch.draw(shader)
def safe_remove_draw_handle(handle):
    """返回 True 如果成功移除；否则 False（并打印错误）。"""
    try:
        bpy.types.SpaceView3D.draw_handler_remove(handle, 'WINDOW')
        return True
    except Exception as e:
        print("safe_remove_draw_handle: remove failed:", e)
        return False

# ---------- Operators ----------
class VIEW3D_OT_toggle_draw_overinfluence(bpy.types.Operator):
    bl_idname = "kourin.toggle_draw_overinfluence"
    bl_label = "Toggle Draw Over-Influenced"

    def execute(self, context):
        from ..imgui_setup.imgui_global import GlobalImgui
        gp = GlobalImgui.get()

        # 确保 list 存在
        if not hasattr(gp, "_draw_handles"):
            gp._draw_handles = []

        # 如果已有 handlers，则尝试全部移除（作为一次关闭）
        if gp._draw_handles:
            removed_any = False
            # 逐个尝试移除，这样即使某个失败，其它也能被清掉
            remaining = []
            for h in gp._draw_handles:
                ok = safe_remove_draw_handle(h)
                if ok:
                    removed_any = True
                else:
                    # 如果失败，不要丢掉引用，保留以便下次尝试
                    remaining.append(h)
            gp._draw_handles = remaining

            # 如果全部移除了，设置状态并刷新视图
            if removed_any:
                for area in context.screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()
                self.report({'INFO'}, "Over-influence drawing stopped.")
            else:
                self.report({'WARNING'}, "未能移除部分 draw handlers（查看控制台）。")
            return {'FINISHED'}

        # 否则没有 handler -> 添加一个
        handle = bpy.types.SpaceView3D.draw_handler_add(draw_callback, (None, None), 'WINDOW', 'POST_VIEW')
        gp._draw_handles.append(handle)

        # 重绘所有 3D 视图
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

        self.report({'INFO'}, "Over-influence drawing started (uses cached results).")
        return {'FINISHED'}

class VIEW3D_OT_recompute_overinfluence(bpy.types.Operator):
    """Recompute over-influenced verts for the active mesh object (only when clicked)"""
    bl_idname = "kourin.recompute_overinfluence"
    bl_label = "Recompute Over-Influenced Now"

    def execute(self, context):
        from ..imgui_setup.imgui_global import GlobalImgui as GP
        gp=GP.get()
        obj = context.object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Select a mesh object in Object Mode to recompute.")
            return {'CANCELLED'}

        threshold = gp.threshold
        indices, positions = compute_overinfluenced(obj, threshold)

        gp._cached_obj_name = obj.name
        # gp._cached_indices = indices
        gp._cached_positions = positions
        gp._cached_over_count = len(indices)

        # 刷新 3D 视图以立即看到效果
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

        self.report({'INFO'}, f"Recomputed: found {gp._cached_over_count} over-influenced verts on '{gp._cached_obj_name}'.")
        return {'FINISHED'}
class VIEW3D_OT_remove_extra_weights(bpy.types.Operator):
    """Remove weights beyond top-N strongest *deform* bone groups for over-influenced verts"""
    bl_idname = "kourin.remove_extra_weights"
    bl_label = "Remove Extra Weights (keep top 4 deform weights)"
    bl_options = {'REGISTER', 'UNDO'}

    top_n: bpy.props.IntProperty(
        name="Keep Top N",
        default=4,
        min=1,
        description="Keep the top N deform bone weights per vertex"
    )

    def execute(self, context):
        from ..imgui_setup.imgui_global import GlobalImgui as GP
        gp=GP.get()
        obj = context.object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Select a mesh object in Object Mode.")
            return {'CANCELLED'}

        mesh = obj.data
        vgroups = obj.vertex_groups

        # 找到关联的 Armature（第一个有 object 的 ARMATURE modifier）
        arm_obj = None
        for mod in obj.modifiers:
            if mod.type == 'ARMATURE' and getattr(mod, "object", None) is not None:
                arm_obj = mod.object
                break

        # 收集 deform 骨骼的名字集合（若找不到 armature，则设为 None 表示不做筛选）
        deform_bone_names = None
        if arm_obj and arm_obj.type == 'ARMATURE':
            deform_bone_names = {b.name for b in arm_obj.data.bones if getattr(b, "use_deform", True)}
            # 若没有任何 deform bone，则退回为 None（即不做筛选）
            if not deform_bone_names:
                deform_bone_names = None

        # 确保处于 Object 模式
        try:
            if obj.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
        except Exception:
            pass

        top_n = max(1, int(self.top_n))
        changed_count = 0
        vert_count = 0

        for v in mesh.vertices:
            vert_count += 1
            # 收集当前顶点与 vertex_groups 的权重信息
            # 注意：v.groups 是一个 read-only 的集合，需要用 list() 避免迭代时被修改问题
            groups_info = [(g.group, vgroups[g.group].name, g.weight) for g in list(v.groups)]
            if not groups_info:
                continue

            # 从 groups_info 中筛选出 "deform" 的那些项（若 deform_bone_names 是 None 则把所有都视为可候选）
            deform_weights = []
            for idx, name, w in groups_info:
                if deform_bone_names is None or name in deform_bone_names:
                    deform_weights.append((idx, w))

            # 如果 deform 权重数量多于 top_n，则需要删除排名靠后的 deform 权重（仅删除 deform 类别）
            if len(deform_weights) > top_n:
                # 按权重从大到小排序
                deform_weights.sort(key=lambda x: x[1], reverse=True)
                keep_idxs = {idx for idx, _ in deform_weights[:top_n]}
                remove_idxs = {idx for idx, _ in deform_weights[top_n:]}

                # 删除这些 deform 的多余权重（保持非deform组不变）
                for g in list(v.groups):
                    if g.group in remove_idxs:
                        try:
                            vgroups[g.group].remove([v.index])
                            changed_count += 1
                        except Exception:
                            # 若删除失败，忽略（继续处理其它顶点）
                            pass

        # 更新 mesh
        try:
            obj.data.update()
        except Exception:
            pass
        # 如果已有 handlers，则尝试全部移除（作为一次关闭）
        if gp._draw_handles:
            removed_any = False
            # 逐个尝试移除，这样即使某个失败，其它也能被清掉
            remaining = []
            for h in gp._draw_handles:
                ok = safe_remove_draw_handle(h)
                if ok:
                    removed_any = True
                else:
                    # 如果失败，不要丢掉引用，保留以便下次尝试
                    remaining.append(h)
            gp._draw_handles = remaining

            # 如果全部移除了，设置状态并刷新视图
            if removed_any:
                for area in context.screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()

        self.report({'INFO'}, f"处理完成：顶点数 {vert_count}，删除权重条目约 {changed_count}（近似）。")
        return {'FINISHED'}