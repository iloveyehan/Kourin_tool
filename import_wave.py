import bpy
import os
import re
import struct

def parse_mod_ini(ini_path):
    """
    解析 mod.ini 文件，获取其中的关键信息。
    返回一个包含资源信息的字典，比如:
    {
      'mesh_vertex_count': 224027,
      'ResourcePositionBuffer': {
         'filename': 'Meshes/Position.buf',
         'format': 'DXGI_FORMAT_R32G32B32_FLOAT',
         'stride': 12
      },
      'ResourceIndexBuffer': {...},
      'ResourceTexCoordBuffer': {...},
      ...
    }
    """
    data_dict = {}
    current_section = None

    # 存储段名 -> {key->value} 的映射
    sections = {}

    # 新的正则
    import re
    re_section = re.compile(r'^\[(.+)\]\s*$')
    # 加 ?: 表示不捕获分组 “(global\s+|local\s+)?”，只捕获后面真正的key
    re_key_value = re.compile(r'^\s*(?:global\s+|local\s+)?([^;].*?)\s*=\s*(.+)$')

    with open(ini_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if not line or line.startswith(';'):
            continue

        m_sec = re_section.match(line)
        if m_sec:
            current_section = m_sec.group(1)
            sections[current_section] = {}
            continue

        if current_section:
            m_kv = re_key_value.match(line)
            if m_kv:
                key = m_kv.group(1).strip()
                val = m_kv.group(2).strip()
                sections[current_section][key] = val

    # 后续就可以直接拿 `"$mesh_vertex_count"` 而不是 `"global $mesh_vertex_count"`
    if 'Constants' in sections:
        constants_sec = sections['Constants']
        if '$mesh_vertex_count' in constants_sec:
            data_dict['mesh_vertex_count'] = int(constants_sec['$mesh_vertex_count'])
        else:
            print("无法从 mod.ini 中获取 $mesh_vertex_count，脚本停止。")
            return data_dict

    # 解析所有 ResourceXxxBuffer
    for sec_name, kv_map in sections.items():
        # 我们只关心 ResourcexxxBuffer 段
        if sec_name.startswith('Resource') and sec_name.endswith('Buffer'):
            buffer_info = {}

            # 读取 filename
            if 'filename' in kv_map:
                buffer_info['filename'] = kv_map['filename']

            # 读取 format
            if 'format' in kv_map:
                buffer_info['format'] = kv_map['format']

            # 读取 stride
            if 'stride' in kv_map:
                buffer_info['stride'] = int(kv_map['stride'])

            # 额外：如有 "type"、"array" 等，可以按需解析
            if 'type' in kv_map:
                buffer_info['type'] = kv_map['type']

            # 以段名作为 key 存入 data_dict
            data_dict[sec_name] = buffer_info

    return data_dict

def load_positions(filepath, format_str, stride, vertex_count):
    """
    读取顶点位置数据。
    - format_str 一般为 'DXGI_FORMAT_R32G32B32_FLOAT'
    - stride 通常为 12（3个float）
    - vertex_count 顶点总数
    返回 [(x,y,z), ... ] 列表
    """
    positions = []
    if format_str != 'DXGI_FORMAT_R32G32B32_FLOAT':
        print(f"Warning: 目前示例只处理 R32G32B32_FLOAT，实际格式 = {format_str}")
        return positions

    floats_per_vertex = 3  # x,y,z
    with open(filepath, 'rb') as f:
        for _ in range(vertex_count):
            # 每个顶点3个float => 3*4=12字节
            x, y, z = struct.unpack('fff', f.read(stride))
            positions.append((x, y, z))
    return positions

def load_indices(filepath, format_str, stride):
    """
    读取索引数据。
    - format_str 应该是 'DXGI_FORMAT_R32_UINT' 等
    - stride=12 在 WWMI 中可能表示“每个三角形占12字节”，即3个uint32。
    返回一个 [ (i1, i2, i3), ... ] 的三角列表 或者 扁平的索引列表
    """
    indices = []
    if format_str != 'DXGI_FORMAT_R32_UINT':
        print(f"Warning: 目前示例只处理 R32_UINT，实际格式 = {format_str}")
        return indices

    file_size = os.path.getsize(filepath)
    # 如果 stride=12，意味着每个“三角形”占12字节 => 3个uint32
    triangle_count = file_size // stride

    with open(filepath, 'rb') as f:
        for _ in range(triangle_count):
            i1, i2, i3 = struct.unpack('III', f.read(12))
            indices.append((i1, i2, i3))

    # 如果你想要 Blender 中的扁平索引，可以展开：
    # flat_indices = []
    # for tri in indices:
    #     flat_indices.extend(tri)
    # return flat_indices
    return indices

def load_uvs(filepath, format_str, stride, vertex_count):
    """
    读取UV数据。示例仅支持 DXGI_FORMAT_R16G16_FLOAT (stride=4?) 或 stride=16？（需要确认数据排布）
    在 .ini 中是:
      format = DXGI_FORMAT_R16G16_FLOAT
      stride = 16
    但很多情况下 2个half就只需要4字节，示例逻辑取决于实际 buf 的存储方式。
    """
    if format_str != 'DXGI_FORMAT_R16G16_FLOAT':
        print(f"Warning: 目前示例只处理 R16G16_FLOAT，实际格式 = {format_str}")
        return []

    uvs = []
    # half 浮点需要 struct.unpack('HH') 然后手动转 float，Python 中可用 `mathutils.geometry.half_to_float` 或自己实现
    # 但 stride=16 表明可能有额外数据(？) 需根据实际格式解析
    with open(filepath, 'rb') as f:
        for _ in range(vertex_count):
            # 示例: 如果只存 (u,v) 各 half => 4字节，那么 stride=4
            # 如果 stride=16，可能是 (u,v) + 8字节保留/其他用途
            # 这里仅演示先读 2个 half:
            half_u, half_v = struct.unpack('HH', f.read(4))
            # 跳过剩余（如果 stride=16）
            if stride > 4:
                f.read(stride - 4)
            # half->float 转换(简化版，可能需要特殊函数)
            u = half_u / 65535.0
            v = half_v / 65535.0
            uvs.append((u, v))
    return uvs

def create_mesh_in_blender(positions, indices, uvs=None, mesh_name="WWMI_ImportedMesh"):
    """
    在 Blender 中创建一个 Mesh 对象，名称为 mesh_name。
    positions: [(x,y,z), ... ]
    indices: [ (i1,i2,i3), ... ]  (三角列表)
    uvs: 可选 [(u,v), ... ]，长度与 positions 相同
    """
    # 创建空Mesh和空Object
    mesh_data = bpy.data.meshes.new(mesh_name)
    mesh_obj = bpy.data.objects.new(mesh_name, mesh_data)
    bpy.context.scene.collection.objects.link(mesh_obj)

    # 设置顶点
    mesh_data.from_pydata(positions, [], indices)

    # 如果有UV，设置UV层
    if uvs and len(uvs) == len(positions):
        # Blender的UV需要基于Loop赋值，先确保有UV层
        mesh_data.uv_layers.new(name="UVMap")
        uv_layer = mesh_data.uv_layers.active.data

        # mesh_data从_pydata创建后会有对应数量的loops
        # 每个面有3个Loop(三角面的情况)
        # 我们需要把顶点的uv匹配到loop上
        loop_index = 0
        for face in mesh_data.polygons:
            for vert_idx in face.vertices:
                uv_layer[loop_index].uv = uvs[vert_idx]
                loop_index += 1

    mesh_data.update()
    return mesh_obj

def import_wwmi_model(mod_ini_path):
    """
    主函数：解析 mod.ini，加载网格数据并在 Blender 中生成一个 Mesh
    """
    parsed_data = parse_mod_ini(mod_ini_path)
    base_dir = os.path.dirname(mod_ini_path)

    # 读取顶点数量
    mesh_vertex_count = parsed_data.get('mesh_vertex_count', 0)
    if mesh_vertex_count == 0:
        print("无法从 mod.ini 中获取 $mesh_vertex_count，脚本停止。")
        return

    # 获取 PositionBuffer 信息
    pos_info = parsed_data.get('ResourcePositionBuffer', {})
    if not pos_info:
        print("在 mod.ini 中未找到 ResourcePositionBuffer 定义，脚本停止。")
        return
    pos_file = os.path.join(base_dir, pos_info['filename'])
    pos_format = pos_info['format']
    pos_stride = pos_info['stride']

    # 获取 IndexBuffer 信息
    idx_info = parsed_data.get('ResourceIndexBuffer', {})
    if not idx_info:
        print("在 mod.ini 中未找到 ResourceIndexBuffer 定义，脚本停止。")
        return
    idx_file = os.path.join(base_dir, idx_info['filename'])
    idx_format = idx_info['format']
    idx_stride = idx_info['stride']

    # 可选：获取 UVBuffer 信息（若有）
    uv_info = parsed_data.get('ResourceTexCoordBuffer', None)

    print("开始加载顶点 Position...")
    positions = load_positions(pos_file, pos_format, pos_stride, mesh_vertex_count)
    print(f"加载完毕，顶点数: {len(positions)}")

    print("开始加载索引 Index...")
    triangles = load_indices(idx_file, idx_format, idx_stride)
    print(f"加载完毕，三角形数: {len(triangles)}")

    # 如果需要UV
    if uv_info:
        uv_file = os.path.join(base_dir, uv_info['filename'])
        uv_format = uv_info['format']
        uv_stride = uv_info['stride']
        print("开始加载UV...")
        uvs = load_uvs(uv_file, uv_format, uv_stride, mesh_vertex_count)
        print(f"加载完毕，UV数: {len(uvs)}")
    else:
        uvs = None

    print("开始在Blender中创建Mesh...")
    create_mesh_in_blender(positions, triangles, uvs=uvs, mesh_name="WWMI_ImportedMesh")
    print("导入完成！")


mod_ini_file = r"C:\Users\Administrator\Downloads\散华-海上私语v1.0-by 狩野樱\Sanhua v1.0\Sanhua\mod.ini"
import_wwmi_model(mod_ini_file)
