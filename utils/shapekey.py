import bpy 
def record_shape_keys(obj):
    """
    记录指定物体的形态键名称和当前值的字典
    
    参数:
        obj_name (str): 物体名称
    
    返回:
        dict: 包含形态键名称和对应值的字典，如果物体没有形态键则返回None
    """
    # 获取物体

    if not obj or not obj.data.shape_keys:
        print(f"物体 {obj.name} 不存在或没有形态键")
        return None
    
    # 获取形态键
    shape_keys = obj.data.shape_keys.key_blocks
    shape_key_dict = {}
    
    # 记录所有形态键的值（排除 Basis）
    for key in shape_keys:
        shape_key_dict[key.name] = key.value
    
    return shape_key_dict
 
def apply_shape_keys(obj, shape_key_dict):
    """
    根据字典还原指定物体的形态键值
    
    参数:
        obj_name (str): 物体名称
        shape_key_dict (dict): 包含形态键名称和对应值的字典
    
    返回:
        bool: 操作是否成功
    """
    # 获取物体
    if not obj or not obj.data.shape_keys:
        print(f"物体 {obj.name} 不存在或没有形态键")
        return False
    
    # 获取形态键
    shape_keys = obj.data.shape_keys.key_blocks
    
    # 应用记录的形态键值
    for key_name, value in shape_key_dict.items():
        if key_name in shape_keys:
            shape_keys[key_name].value = value
    
    return True