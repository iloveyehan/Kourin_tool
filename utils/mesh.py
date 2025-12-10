import bpy
import numpy as np
def has_shape_key(obj):
    """
    判断物体是否为 Mesh 并且包含 Shape Keys。
    如果是 Mesh 并且包含 Shape Keys，返回 True，否则返回 False。
    """
    if obj is not None and obj.type == 'MESH':
        return obj.data.shape_keys is not None
    return False