import bpy
from mathutils import Vector, Quaternion

def set_cursor(matrix=None, location=Vector(), rotation=Quaternion()):
    # 获取当前场景的光标对象
    cursor = bpy.context.scene.cursor
    print('matrix', matrix)
    print('location', location)
    # 如果传入了矩阵，就使用矩阵设置光标的位置和旋转
    if matrix:
        # 提取矩阵的位置信息
        print('matrix.to_translation()', matrix.to_translation())
        cursor.location = matrix.to_translation()
        # 提取矩阵的旋转信息（四元数形式）
        cursor.rotation_quaternion = matrix.to_quaternion()
        # 设置旋转模式为四元数
        cursor.rotation_mode = 'QUATERNION'
    else:
        # 如果没有传入矩阵，就使用手动传入的位置和旋转
        cursor.location = location

        # 根据当前的旋转模式来设置旋转
        if cursor.rotation_mode == 'QUATERNION':
            # 如果是四元数模式，直接使用传入的四元数
            cursor.rotation_quaternion = rotation

        elif cursor.rotation_mode == 'AXIS_ANGLE':
            # 如果是轴角模式，将传入的四元数转换为轴角
            cursor.rotation_axis_angle = rotation.to_axis_angle()

        else:
            # 如果是欧拉角模式，将传入的四元数转换为欧拉角
            cursor.rotation_euler = rotation.to_euler(cursor.rotation_mode)

