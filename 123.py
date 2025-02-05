#python文件
import bpy
import os
import re
import struct
import numpy as np
#############################################
# 1) 解析 mod.ini
#############################################
def half_to_float(h):
    """ 将16位半精度浮点转换为Python float """
    return np.frombuffer(struct.pack('H', h), dtype=np.float16)[0].astype(float)
def parse_mod_ini(ini_path):
    """
    读取 mod.ini，将以下内容放进 data_dict:
      - mesh_vertex_count
      - ResourcePositionBuffer / ResourceIndexBuffer / ResourceTexCoordBuffer / ResourceBlendBuffer
      - 组件分段 [TextureOverrideComponentX], 包含 match_first_index, match_index_count, drawindexed
    """
    data_dict = {}
    current_section = None
    sections = {}

    # 改进后的正则：可选忽略 global/local
    re_section = re.compile(r'^\[(.+)\]\s*$')
    re_key_value = re.compile(r'^\s*(?:global\s+|local\s+)?([^;].*?)\s*=\s*(.+)$')

    with open(ini_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 将行先分区段粗分
    for line in lines:
        line_strip = line.strip()
        if not line_strip or line_strip.startswith(';'):
            continue

        m_sec = re_section.match(line_strip)
        if m_sec:
            current_section = m_sec.group(1)
            sections[current_section] = []
            continue

        if current_section:
            sections[current_section].append(line_strip)

    # 将每个 section 内的行做进一步解析
    # import re

    for sec_name, sec_lines in sections.items():
        kv_map = {}
        drawindexed_list = []

        for line_text in sec_lines:

            # 先用正则或 replace 去除常见 BOM、零宽空格等
            # 如果还有其他奇怪字符，可以继续添加
            cleaned_line = line_text.replace('\ufeff', '').replace('\u200b', '')

            # 再 strip() 并转小写
            line_lower = cleaned_line.strip().lower()

            # 检查是否包含 'drawindexed'
            if 'drawindexed' in line_lower:
                # 如果你只要这行“以 drawindexed 开头”，可把上面改成 `startswith`
                # 但这样要保证没有前置空格/BOM等
                # 下面先把 '=' 也去掉
                tmp = line_lower.replace('drawindexed', '', 1)
                tmp = tmp.replace('=', '', 1).strip()
                # 现在 tmp 应该类似 "1380, 1220058, 0"
                parts = [p.strip() for p in tmp.split(',')]
                if len(parts) == 3:
                    try:
                        icount = int(parts[0])
                        sindex = int(parts[1])
                        bvertex = int(parts[2])
                        drawindexed_list.append({
                            'index_count': icount,
                            'start_index': sindex,
                            'base_vertex': bvertex
                        })
                    except ValueError:
                        pass
                # 继续下一行
                continue

            # 否则尝试用正则匹配 key=value
            m_kv = re_key_value.match(line_text)
            if m_kv:
                key = m_kv.group(1).strip()
                val = m_kv.group(2).strip()
                kv_map[key] = val

        sections[sec_name] = {
            'kv_map': kv_map,
            'drawindexed_list': drawindexed_list
        }

    # 读取 mesh_vertex_count
    if 'Constants' in sections:
        const_kv = sections['Constants']['kv_map']
        if '$mesh_vertex_count' in const_kv:
            data_dict['mesh_vertex_count'] = int(const_kv['$mesh_vertex_count'])
        else:
            print("无法获取 $mesh_vertex_count, 脚本停止.")
            return None
    else:
        print("缺少 [Constants] 段, 脚本停止.")
        return None

    # 读取资源段 (ResourceXXXBuffer)
    for sec_name, content in sections.items():
        # if sec_name.startswith("Resource") and sec_name.endswith("Buffer"):
        if sec_name.startswith("Resource"):
            kv = content['kv_map']
            buf_info = {
                'filename': kv.get('filename', ''),
                'format': kv.get('format', ''),
                'stride': int(kv.get('stride', 0)),
                'type': kv.get('type', '')
            }
            data_dict[sec_name] = buf_info

    # 读取组件分段 [TextureOverrideComponentX]
    components = []
    for sec_name, content in sections.items():
        if sec_name.startswith('TextureOverrideComponent'):
            kv = content['kv_map']
            drawcalls = content['drawindexed_list']
            comp_info = {
                'name': sec_name,
                'hash': kv.get('hash', ''),  # 新增此行
                'match_first_index': int(kv.get('match_first_index', 0)),
                'match_index_count': int(kv.get('match_index_count', 0)),
                'draw_calls': drawcalls
            }
            components.append(comp_info)
    components.sort(key=lambda c: c['name'])
    data_dict['components'] = components

    data_dict['textures'] = []
    for sec_name, content in sections.items():
        if sec_name.startswith('ResourceTexture'):
            texture_info = {
                'name': sec_name,
                'filename': content['kv_map'].get('filename', ''),
                'hash': content['kv_map'].get('hash', '')
            }
            data_dict['textures'].append(texture_info)
    # 新增：解析 TextureOverrideTextureX 段
    data_dict['texture_overrides'] = []
    for sec_name, content in sections.items():
        if sec_name.startswith('TextureOverrideTexture'):
            override_info = {
                'hash': content['kv_map'].get('hash', ''),
                'texture_name': content['kv_map'].get('this', '')
            }
            data_dict['texture_overrides'].append(override_info)
    return data_dict


#############################################
# 2) 读取二进制数据
#############################################

def load_positions(filepath, format_str, stride, vertex_count):
    # """
    # 读取顶点坐标 (x,y,z)。
    # 假设: DXGI_FORMAT_R32G32B32_FLOAT, stride=12
    # """
    import time
    a=time.time()
    # if not os.path.isfile(filepath):
    #     print(f"[Positions] 文件不存在: {filepath}")
    #     return []
    # if format_str != 'DXGI_FORMAT_R32G32B32_FLOAT':
    #     print(f"警告: 未处理的 Position format={format_str}, 脚本可能不正确.")
    # positions = []
    # with open(filepath, 'rb') as f:
    #     for _ in range(vertex_count):
    #         data = f.read(stride)
    #         if len(data) < stride:
    #             break
    #         x, y, z = struct.unpack('fff', data)
    #         positions.append((x, y, z))
    b=time.time()
    print(b - a)
    # return positions
    """ 加载顶点坐标（R32G32B32_FLOAT）"""
    try:
        data = np.fromfile(filepath, dtype=np.float32, count=vertex_count * 3)
        print(time.time() - b)
        return data.reshape((-1, 3)).tolist()
    except Exception as e:
        print(f"Position加载失败: {str(e)}")
        return []

def load_indices_as_single(filepath, format_str):
    """
    将 index.buf 按"4字节=1个index"全部读出来并返回一个列表 [i0, i1, i2, ...]。
    例如 format=DXGI_FORMAT_R32_UINT => 4字节/索引
    """
    # if not os.path.isfile(filepath):
    #     print(f"[Index] 文件不存在: {filepath}")
    #     return []
    #
    # if format_str != 'DXGI_FORMAT_R32_UINT':
    #     print(f"警告: 未处理的 Index format={format_str}, 脚本可能不正确.")
    # index_list = []
    # file_size = os.path.getsize(filepath)
    # count = file_size // 4  # 4字节=1个index
    # with open(filepath, 'rb') as f:
    #     for _ in range(count):
    #         raw4 = f.read(4)
    #         if len(raw4) < 4:
    #             break
    #         val = struct.unpack('I', raw4)[0]
    #         index_list.append(val)
    # return index_list
    try:
        return np.fromfile(filepath, dtype=np.uint32).tolist()
    except Exception as e:
        print(f"Index加载失败: {str(e)}")
        return []

def load_uvs(filepath, format_str, stride, vertex_count):
    """
    读取UV (u,v)；假设 DXGI_FORMAT_R16G16_FLOAT, stride=4 或 stride>=4
    """
    if not os.path.isfile(filepath):
        return []
    if format_str != 'DXGI_FORMAT_R16G16_FLOAT':
        print(f"警告: UV format={format_str}, 脚本可能不正确.")
    uvs = []
    with open(filepath, 'rb') as f:
        for _ in range(vertex_count):
            raw = f.read(stride)
            if len(raw) >= 4:
                half_u, half_v = struct.unpack('HH', raw[:4])
                u = half_to_float(half_u)
                v = half_to_float(half_v)
                uvs.append((u, 1-v))
    return uvs
    # """ 加载UV（R16G16_FLOAT）"""
    # try:
    #     data = np.fromfile(filepath, dtype=np.uint16, count=vertex_count * 2)
    #     uvs = []
    #     for i in range(0, len(data), 2):
    #         u = half_to_float(data[i])
    #         v = half_to_float(data[i + 1])
    #         uvs.append((u, 1.0-v))
    #     return uvs
    # except Exception as e:
    #     print(f"UV加载失败: {str(e)}")
    #     return []

def load_blend_data(filepath, format_str, stride, vertex_count):
    """
    读取骨骼权重，示例: DXGI_FORMAT_R8_UINT, stride=8 => (b0,b1,b2,b3, w0,w1,w2,w3)
    返回: [{'bone_indices':[b0,b1,b2,b3], 'weights':[w0,w1,w2,w3]}, ...]
    """
    if not os.path.isfile(filepath):
        return []
    if format_str != 'DXGI_FORMAT_R8_UINT':
        print(f"警告: Blend format={format_str}, 脚本可能不正确.")
    result = []
    with open(filepath, 'rb') as f:
        for _ in range(vertex_count):
            raw = f.read(stride)
            if len(raw) < stride:
                break
            b0,b1,b2,b3, w0,w1,w2,w3 = struct.unpack('BBBBBBBB', raw)
            fw0 = w0 / 255.0
            fw1 = w1 / 255.0
            fw2 = w2 / 255.0
            fw3 = w3 / 255.0
            # 可选：再次做 sum=1 归一化
            s = fw0+fw1+fw2+fw3
            if s>1e-8:
                fw0/=s; fw1/=s; fw2/=s; fw3/=s
            result.append({
                'bone_indices':[b0,b1,b2,b3],
                'weights':[fw0,fw1,fw2,fw3]
            })
    return result


#############################################
# 3) 创建骨骼和网格
#############################################
def load_skeleton_matrices(filepath, bone_count):
    """ 加载骨骼变换矩阵（假设格式为R32G32B32A32_FLOAT的4x4矩阵）"""
    try:
        data = np.fromfile(filepath, dtype=np.float32, count=bone_count*16)
        return data.reshape((bone_count, 4, 4))  # [bone_count, 4行, 4列]
    except Exception as e:
        print(f"骨骼矩阵加载失败: {str(e)}")
        return None


def create_armature_hierarchical(matrices, arm_name="WWMI_Armature"):
    """ 根据矩阵创建层级骨骼 """
    arm_data = bpy.data.armatures.new(arm_name)
    arm_obj = bpy.data.objects.new(arm_name, arm_data)
    bpy.context.collection.objects.link(arm_obj)
    bpy.context.view_layer.objects.active = arm_obj
    arm_data.display_type = 'STICK'

    bpy.ops.object.mode_set(mode='EDIT')
    bones = []

    # 第一步：创建所有骨骼并设置位置
    for i, matrix in enumerate(matrices):
        bone = arm_data.edit_bones.new(f"Bone_{i}")

        # 从矩阵提取位置（假设第4行为平移）
        pos = matrix[3][:3]
        # 转换为Blender坐标系（Y-up转Z-up）
        bone.head = (pos[0], -pos[2], pos[1])
        bone.tail = bone.head + (0, 0.1, 0)  # 初始尾部
        bones.append(bone)

    # 第二步：推断父子关系（示例：根据z坐标层级）
    # 实际项目需根据骨骼名称或矩阵中的层级信息调整
    for i, bone in enumerate(bones):
        if i == 0:
            continue  # 根骨骼无父级
        # 示例逻辑：找z坐标更小的骨骼作为父级
        possible_parents = [b for b in bones if b.head.z < bone.head.z]
        if possible_parents:
            parent = min(possible_parents, key=lambda b: b.head.z)
            bone.parent = parent
            bone.tail = parent.head  # 尾部指向父级头部

    bpy.ops.object.mode_set(mode='OBJECT')
    return arm_obj
# def create_armature_in_blender(bone_count, arm_name="WWMI_Armature"):
#     """
#     创建一个 armature，让 bone_count 个骨骼平铺在 X轴。
#     如果你有骨骼的真正父子层级 + 变换矩阵，需要自己改写这里。
#     """
#     import mathutils
#     arm_data = bpy.data.armatures.new(arm_name)
#     arm_obj = bpy.data.objects.new(arm_name, arm_data)
#     bpy.context.scene.collection.objects.link(arm_obj)
#
#     bpy.context.view_layer.objects.active = arm_obj
#     bpy.ops.object.mode_set(mode='EDIT')
#     for i in range(bone_count):
#         bone = arm_data.edit_bones.new(f"Bone_{i}")
#         # 简单平铺: head=(i*0.5,0,0), tail=(i*0.5,0,0.2)
#         bone.head = (i*0.5, 0.0, 0.0)
#         bone.tail = (i*0.5, 0.0, 0.2)
#     bpy.ops.object.mode_set(mode='OBJECT')
#     return arm_obj, arm_data


def create_component_mesh_object(data,comp_info, all_indices, positions, uvs, blend_data, arm_obj=None, texture_map=None, prefix="WWMI"):
    """
    为单个组件(可含多个 drawindexed)创建一个网格对象。
    - all_indices: 整份 index (按1个index=4字节读取)
    - comp_info['draw_calls']: [{index_count, start_index, base_vertex}, ...]
    - positions/uvs/blend_data: 全部顶点的列表
    - arm_obj: 如果要绑定骨骼，需要在这里添加 Armature Modifier + 顶点组
    """
    print('创建mesh中')
    name = comp_info['name']
    draws = comp_info['draw_calls']
    if not draws:
        print(f"组件 {name} 无 drawindexed 指令，跳过。")
        return None

    # 收集所有三角 (i1,i2,i3) => new_faces
    # 注意: indexCount 是索引的数量，不是三角数量
    #       => (indexCount//3) 才是三角面数量
    used_tris = []
    for d in draws:
        icount = d['index_count']
        start_i = d['start_index']
        base_v = d['base_vertex']

        # 在 all_indices 里取 [start_i, start_i+icount) 的索引
        sub_idxs = all_indices[start_i : start_i + icount]
        # 每3个 index 组成1个三角
        for t in range(0, len(sub_idxs), 3):
            if t+2 < len(sub_idxs):
                i1 = sub_idxs[t] + base_v
                i2 = sub_idxs[t+1] + base_v
                i3 = sub_idxs[t+2] + base_v
                used_tris.append((i1, i2, i3))

    if not used_tris:
        print(f"组件 {name} 未产生有效三角数据, 跳过。")
        return None
    print('mesh0', len(used_tris))
    # 收集面中用到的顶点
    used_vertex_ids = set()
    for tri in used_tris:
        used_vertex_ids.update(tri)
    used_vertex_ids = sorted(list(used_vertex_ids))
    print('mesh1', len(used_tris), len(used_vertex_ids))
    remap = {}
    for new_i, old_i in enumerate(used_vertex_ids):
        remap[old_i] = new_i
    print('mesh2', len(used_tris), len(used_vertex_ids))
    new_positions = [positions[old_i] for old_i in used_vertex_ids]
    new_uvs = [uvs[old_i] for old_i in used_vertex_ids] if uvs else None
    new_blends = [blend_data[old_i] for old_i in used_vertex_ids] if blend_data else None
    new_tris = []
    for tri in used_tris:
        new_tris.append((remap[tri[0]], remap[tri[1]], remap[tri[2]]))
    print('mesh3',len(used_tris),len(used_vertex_ids))
    # 在 Blender 中创建 Mesh
    mesh_name = f"{prefix}_{name}"
    mesh_data = bpy.data.meshes.new(mesh_name)
    mesh_obj = bpy.data.objects.new(mesh_name, mesh_data)
    bpy.context.scene.collection.objects.link(mesh_obj)

    # from_pydata
    mesh_data.from_pydata(new_positions, [], new_tris)
    # mesh_data.update()

    # 处理UV
    if new_uvs:
        mesh_data.uv_layers.new(name="UVMap")
        uv_layer = mesh_data.uv_layers.active.data
        loop_i = 0
        for poly in mesh_data.polygons:
            for vi in poly.vertices:
                uv_layer[loop_i].uv = new_uvs[vi]
                loop_i += 1

    # 处理骨骼权重
    if arm_obj and new_blends:
        # 给网格加一个 Armature Modifier
        mesh_obj.parent = arm_obj
        arm_mod = mesh_obj.modifiers.new("Armature", 'ARMATURE')
        arm_mod.object = arm_obj

        # 创建并分配顶点组
        for v_i, bd in enumerate(new_blends):
            bone_ids = bd['bone_indices']
            weights = bd['weights']
            for b_idx, w in zip(bone_ids, weights):
                # 假设 255 表示无效索引
                if b_idx == 255 or w < 1e-5:
                    continue
                bone_name = f"Bone_{b_idx}"
                # 确保有对应的顶点组
                if bone_name not in mesh_obj.vertex_groups:
                    mesh_obj.vertex_groups.new(name=bone_name)
                vg = mesh_obj.vertex_groups[bone_name]
                vg.add([v_i], w, 'ADD')
    # 在create_component_mesh_object函数中添加以下代码
    if texture_map:
        # 提取组件编号（例如"TextureOverrideComponent5" -> "5"）
        comp_number = ''.join(filter(str.isdigit, comp_info['name']))
        if comp_number:
            # 查找对应的TextureOverrideTextureX段（例如ResourceTexture5）
            target_tex_name = f"ResourceTexture{comp_number}"
            for override_info in data.get('texture_overrides', []):
                if override_info['texture_name'] == target_tex_name:
                    component_hash = override_info['hash']
                    material = texture_map.get(component_hash, None)
                    if material:
                        if material.name not in mesh_obj.data.materials:
                            mesh_obj.data.materials.append(material)
                    break
    if texture_map and 'texture' in comp_info:
        material = texture_map.get(comp_info['texture'], None)
        if material:
            if material.name not in mesh_obj.data.materials:
                mesh_obj.data.materials.append(material)
    mesh_data.update()
    return mesh_obj


#############################################
# 4) 最终导入流程
#############################################
def import_wwmi_model_extended(mod_ini_path):
    data = parse_mod_ini(mod_ini_path)
    if not data:
        print("解析 mod.ini 失败，退出。")
        return

    base_dir = os.path.dirname(mod_ini_path)

    mesh_vertex_count = data.get('mesh_vertex_count', 0)
    if mesh_vertex_count <= 0:
        print("mesh_vertex_count 无效, 退出.")
        return

    # 加载 Positions
    pos_buf = data.get('ResourcePositionBuffer', None)
    if not pos_buf:
        print("缺少 ResourcePositionBuffer, 退出.")
        return
    pos_file = os.path.join(base_dir, pos_buf['filename'])
    positions = load_positions(pos_file, pos_buf['format'], pos_buf['stride'], mesh_vertex_count)
    if not positions:
        print("Positions 数据为空, 退出.")
        return
    print(f"Positions 读取完成, 顶点数={len(positions)}")

    # 加载 Index => 按单index读取
    idx_buf = data.get('ResourceIndexBuffer', None)
    if not idx_buf:
        print("缺少 ResourceIndexBuffer, 退出.")
        return
    idx_file = os.path.join(base_dir, idx_buf['filename'])
    all_indices = load_indices_as_single(idx_file, idx_buf['format'])
    print(f"Index 读取完成, 索引总数={len(all_indices)}")

    # 可选: 加载UV
    uv_buf = data.get('ResourceTexCoordBuffer', None)
    if uv_buf:
        uv_file = os.path.join(base_dir, uv_buf['filename'])
        uvs = load_uvs(uv_file, uv_buf['format'], uv_buf['stride'], mesh_vertex_count)
        if uvs:
            print(f"UV 读取完成, 数量={len(uvs)}")
        else:
            uvs = None
            print("UV 数据为空.")
    else:
        uvs = None

    # 可选: 加载骨骼权重
    blend_buf = data.get('ResourceBlendBuffer', None)
    if blend_buf:
        blend_file = os.path.join(base_dir, blend_buf['filename'])
        blend_data = load_blend_data(blend_file, blend_buf['format'], blend_buf['stride'], mesh_vertex_count)
        if blend_data:
            print(f"Blend(骨骼权重) 读取完成, 数量={len(blend_data)}")
        else:
            blend_data = None
            print("Blend 数据为空.")
    else:
        blend_data = None

    # 若有骨骼数据，找出最高骨骼ID
    max_bone_idx = -1
    if blend_data:
        for bd in blend_data:
            for b_i in bd['bone_indices']:
                if b_i != 255 and b_i > max_bone_idx:
                    max_bone_idx = b_i
    arm_obj = None
    if max_bone_idx >= 0:
        # 检查 ResourceMergedSkeleton 是否存在
        if 'ResourceMergedSkeleton' not in data:
            print("警告: mod.ini 中缺少 ResourceMergedSkeleton 定义，使用平铺骨骼")
            # arm_obj, _ = create_armature_in_blender(max_bone_idx + 1, "WWMI_Armature")
        else:
            skeleton_path = os.path.join(base_dir, data['ResourceMergedSkeleton']['filename'])
            matrices = load_skeleton_matrices(skeleton_path, max_bone_idx + 1)
            if matrices is not None:
                arm_obj = create_armature_hierarchical(matrices, "WWMI_Armature")
            # else:
                # arm_obj, _ = create_armature_in_blender(max_bone_idx + 1, "WWMI_Armature")
    # 加载所有贴图并创建材质
    texture_map = {}
    for override_info in data.get('texture_overrides', []):
        tex_hash = override_info['hash']
        tex_name = override_info['texture_name']
        # 查找对应的ResourceTextureX段
        resource_tex = next((t for t in data.get('textures', []) if t['name'] == tex_name), None)
        if not resource_tex:
            print(f"警告: TextureOverrideTexture {tex_hash} 对应的 {tex_name} 不存在")
            continue
        tex_path = os.path.join(base_dir, resource_tex['filename'])
        if not os.path.exists(tex_path):
            print(f"警告: 贴图文件不存在 {tex_path}")
            continue

        # 创建材质
        mat_name = f"Mat_{tex_hash}"
        material = bpy.data.materials.new(name=mat_name)
        material.use_nodes = True
        bsdf = material.node_tree.nodes.get('Principled BSDF')

        # 加载贴图
        tex_image = material.node_tree.nodes.new('ShaderNodeTexImage')
        tex_image.image = bpy.data.images.load(tex_path)

        # 连接节点：贴图 → BSDF基础色
        material.node_tree.links.new(
            bsdf.inputs['Base Color'],
            tex_image.outputs['Color']
        )

        texture_map[tex_hash] = material
    # 读取组件分段
    components = data.get('components', [])
    if not components:
        print("没有发现 [TextureOverrideComponentX], 整合为一个对象也可.")
        # 如果确实需要把所有索引都做成一个对象，可以把 all_indices 全部当作三角面处理
        # 这里就不写了，你可自行参考 create_component_mesh_object 的做法
        return

    # 逐组件创建
    print('fenduan',len(components))
    for comp_info in components:
        obj = create_component_mesh_object(
            data,
            comp_info,
            all_indices,
            positions,
            uvs,
            blend_data,
            arm_obj,
            texture_map=texture_map,  # 新增参数
            prefix="WWMI"
        )
        if obj:
            print(f"已创建组件对象: {obj.name}")
        else:
            print(f"组件 {comp_info['name']} 创建失败或无数据.")


#############################################
# 如何使用:
# 在 Blender 脚本编辑器中粘贴整个脚本，修改下面这几行路径并运行:
#############################################

mod_ini_file = r"C:\Users\Administrator\Downloads\散华-海上私语v1.0-by 狩野樱\Sanhua v1.0\Sanhua\mod.ini"
import_wwmi_model_extended(mod_ini_file)
