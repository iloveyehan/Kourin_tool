import bpy
import bmesh
import bpy
from mathutils import Vector


def get_pivot_position():
    # 获取当前选中的对象或组件

    obj = bpy.context.object

    # 检查是否是对象（类似 Maya 的 Transform 节点）
    if not isinstance(obj, bpy.types.Object):
        print("Selection is not an object.")
        return Vector((0, 0, 0))

    # 获取 Pivot 点（即 Origin 点的世界位置）
    pivot_point = obj.matrix_world.translation

    # 返回为向量
    return Vector((pivot_point.x, pivot_point.y, pivot_point.z))


# 调用函数
pivot_pos = get_pivot_position()
print(f"Pivot Position: {pivot_pos}")


def compensate_children(obj, old_matrix, new_matrix):
    """
    调整对象的子对象位置，使其在父对象矩阵变换后保持相对位置不变。

    参数:
    obj -- 需要调整的父对象
    old_matrix -- 父对象的原始变换矩阵
    new_matrix -- 父对象的新变换矩阵
    """
    # 计算新旧变换矩阵之间的差异（delta 矩阵）
    delta_matrix = new_matrix.inverted_safe() @ old_matrix

    # 获取父对象的所有子对象
    children = obj.children

    # 遍历每个子对象，调整它们的父级逆矩阵
    for child in children:
        # 当前子对象的父级逆矩阵
        parent_matrix_inverse = child.matrix_parent_inverse

        # 更新父级逆矩阵，使子对象保持相对位置不变
        child.matrix_parent_inverse = delta_matrix @ parent_matrix_inverse


def set_obj_origin(obj, mx, bm=None):
    """
    设置对象的原点位置。

    :param obj: 要调整原点的对象。
    :param mx: 新的矩阵位置。
    :param bm: (可选) 编辑模式下的 BMesh 数据结构。
    """
    # 复制对象的世界矩阵
    omx = obj.matrix_world.copy()

    # 计算子对象的位置补偿
    compensate_children(obj, omx, mx)

    # 计算新旧矩阵之间的差值
    delta_matrix = mx.inverted_safe() @ obj.matrix_world

    # 设置对象的新世界矩阵
    obj.matrix_world = mx

    # 如果提供了 BMesh 数据，则更新 BMesh
    if bm:
        bmesh.ops.transform(bm, verts=bm.verts, matrix=delta_matrix)
        bmesh.update_edit_mesh(obj.data)
    else:
        # 否则，直接更新对象的数据
        obj.data.transform(delta_matrix)

    # 如果对象类型为网格，则更新网格数据
    if obj.type == 'MESH':
        obj.data.update()
