import math
import bpy
import numpy as np
def vg_clean_advanced(obj):
    '''清理所有顶点组中的非法权重（0、负值、NaN）
        返回:报告'''
    report_buffer = []  # 用于存储清理报告
    # 优化：预先获取顶点组索引映射
    vg_index_map = {vg.index: vg for vg in obj.vertex_groups}
    
    # 并行遍历顶点数据
    for v in obj.data.vertices:
        for group in v.groups:
            vg = vg_index_map.get(group.group)
            if not vg:
                continue
            
            weight = group.weight
            # 检测非法权重条件
            if math.isnan(weight) or weight <= 0.0:
                # 使用顶点组自身的remove方法
                vg.remove([v.index])
                report_buffer.append(
                    f"顶点 {v.index} -> {vg.name}: "
                    f"非法权重 { 'NaN' if math.isnan(weight) else f'{weight:.4f}'}")
    return report_buffer
def vg_clear_unused(obj):
    '''删除没有使用的顶点组（形变骨骼，修改器），不包括被其他物体使用的顶点组'''
    used_vg = []
    armature = []
    # 检查所有修改器
    for mod in obj.modifiers:
        # 这里我们检查几个常见的修改器属性
        if hasattr(mod, 'vertex_group') and mod.vertex_group is not None:
            used_vg.append(mod.vertex_group)
        # 需要骨骼激活状态
        if mod.type == 'ARMATURE' and mod.object is not None and mod.show_viewport:
            armature.append(mod.object)
    # 检查形变骨骼
    for a in armature:
        for b in a.data.bones:
            if b.use_deform:
                used_vg.append(b.name)
    # 检查顶点组
    for vg in obj.vertex_groups:
        if vg.name not in used_vg:
            obj.vertex_groups.remove(vg)
def is_vertex_group_deform_bone(obj, group_name):
    armature_mod = None
    for mod in obj.modifiers:
        if mod.type == 'ARMATURE':
            armature_mod = mod
            break

    if not armature_mod or not armature_mod.object or armature_mod.object.type != 'ARMATURE':
        return False

    armature_obj = armature_mod.object
    bone = armature_obj.data.bones.get(group_name)

    if bone and bone.use_deform:
        return True

    return False
def get_groups_arr(obj: bpy.types.Object, include_groups: list[bool]=None):
    mesh: bpy.types.Mesh = obj.data
    if not isinstance(mesh, bpy.types.Mesh): return

    arr = np.zeros((len(mesh.vertices), len(obj.vertex_groups)), dtype=np.float32)
    for i, v in enumerate(mesh.vertices):
        current_vertex = arr[i]
        for g in v.groups:
            if g.group >= arr.shape[1]:
                print(f"WARNING: group index {g.group} out of bounds ({arr.shape[1]} vertex groups) for vertex {i}")
                continue
            if include_groups and include_groups[g.group]:
                current_vertex[g.group] = g.weight
            elif not include_groups:
                current_vertex[g.group] = g.weight
    return arr
def is_group_valid(vertex_groups, group_name):
    return len(group_name) > 0 and group_name in vertex_groups
def get_group_arr(obj: bpy.types.Object, group_name):
    mesh: bpy.types.Mesh = obj.data
    if not isinstance(mesh, bpy.types.Mesh): return
    group_index = obj.vertex_groups[group_name].index
    arr = np.zeros(len(mesh.vertices), dtype=np.float32)
    for i, v in enumerate(mesh.vertices):
        for g in v.groups:
            if g.group == group_index:
                arr[i] = g.weight
    return arr
def draw_debug_vertex_colors(obj, matched):
    mesh: bpy.types.Mesh = obj.data
    if not isinstance(mesh, bpy.types.Mesh): return

    if "RBT Matched" in mesh.vertex_colors:
        color_layer = mesh.vertex_colors["RBT Matched"]
    else:
        color_layer = mesh.vertex_colors.new(name="RBT Matched")
    if not color_layer: return False
    color_layer.active = True
    loop_ind = np.zeros(len(mesh.loops), dtype=np.int64)
    mesh.loops.foreach_get('vertex_index', loop_ind)
    loop_matched = matched[loop_ind]
    color_data = np.ones((len(mesh.loops), 4), dtype=np.float32)
    color_data[~loop_matched] = [234/255, 0, 255/255, 1.0]
    color_layer.data.foreach_set("color", color_data.reshape(-1))
    mesh.update()
    mesh.vertex_colors.active = color_layer
    return True

