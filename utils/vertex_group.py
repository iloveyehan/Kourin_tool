import math
import bpy
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
