import bpy
import bmesh
from mathutils import Vector
from collections import deque

# =============== 1) 用户初始配对（避免中线） ===============
def get_symmetry_pairs_initial(bm, epsilon=1e-6):
    """
    从用户选中的顶点中获取初始对称对 (v_left, v_right)，
    跳过绝对值 |x| <= epsilon 的中线顶点，并用贪心法匹配。
    """
    selected_verts = [v for v in bm.verts if v.select]

    # 剔除中线附近的顶点
    left_verts  = [v for v in selected_verts if v.co.x < -epsilon]
    right_verts = [v for v in selected_verts if v.co.x >  epsilon]

    # 用 set 管理右侧可用顶点，避免重复配对
    right_avail = set(right_verts)
    pairs = []

    for lv in left_verts:
        mirror_pos = Vector((-lv.co.x, lv.co.y, lv.co.z))
        best_rv, best_dist = None, float('inf')
        for rv in right_avail:
            dist = (rv.co - mirror_pos).length
            if dist < best_dist:
                best_rv = rv
                best_dist = dist
        if best_rv is not None:
            pairs.append((lv, best_rv))
            right_avail.remove(best_rv)

    return pairs

# =============== 2) 指纹与邻居获取 ===============
def neighbors_in_bmvert(v):
    """返回顶点 v 的所有邻居顶点列表。"""
    return [e.other_vert(v) for e in v.link_edges]

def build_fingerprint(bm, v):
    """
    为顶点 v 构建一个简单的“指纹”：
      - 度数 deg
      - 面数量 face_count
      - 邻居的度分布(升序)
      - 该顶点所连面的顶点数量分布(升序)
    """
    deg = len(v.link_edges)
    face_count = len(v.link_faces)
    neighbor_degs = sorted(len(n.link_edges) for n in neighbors_in_bmvert(v))
    face_verts_count = sorted(len(f.verts) for f in v.link_faces)

    return (deg, face_count, tuple(neighbor_degs), tuple(face_verts_count))

def is_fingerprint_compatible(fpA, fpB):
    """简单判断指纹是否完全相等。"""
    return fpA == fpB

# =============== 3) 分层 BFS，避免重复扩展 ===============
def expand_symmetry_pairs(bm, initial_pairs):
    """
    利用 BFS 从 initial_pairs 扩展出更多对称匹配。
    用 pair_dict 记录最终配对：pair_dict[left_idx] = right_idx
    """
    pair_dict = {}
    for l, r in initial_pairs:
        pair_dict[l.index] = r.index

    # 预计算指纹
    fingerprints = [build_fingerprint(bm, v) for v in bm.verts]

    # 预计算所有邻居
    all_neighbors = {v.index: [n.index for n in neighbors_in_bmvert(v)]
                     for v in bm.verts}
    print('initial_pairs',initial_pairs)
    # BFS 队列，存放已配对的 (left_idx, right_idx)
    queue = deque((l.index, r.index) for l, r in initial_pairs)

    # 用 visited 避免对同一 (l_idx, r_idx) 重复处理
    visited = set(queue)
    print('visited',visited)
    print('queue', queue)
    while queue:
        l_idx, r_idx = queue.popleft()

        # 匹配前先获取邻居
        l_neighbors = all_neighbors[l_idx]
        r_neighbors = all_neighbors[r_idx]

        # 找出还未匹配的邻居
        matched_right_set = set(pair_dict.values())  # 已经作为“右侧”配对
        l_unmatched = [x for x in l_neighbors if x not in pair_dict]
        r_unmatched = [x for x in r_neighbors if x not in matched_right_set]

        # N^2 方式尝试匹配 (可根据需要再优化)
        # print(len(l_unmatched), len(r_unmatched))
        for cand_l in l_unmatched:
            # print('cand_l',cand_l)
            fp_l = fingerprints[cand_l]
            chosen_r = None
            for cand_r in r_unmatched:
                fp_r = fingerprints[cand_r]
                if is_fingerprint_compatible(fp_l, fp_r):
                    # 局部冲突检查
                    if not local_conflict(pair_dict, cand_l, cand_r, all_neighbors):
                        chosen_r = cand_r
                        break
            if chosen_r is not None:
                pair_dict[cand_l] = chosen_r
                r_unmatched.remove(chosen_r)
                # 入队前检查是否访问过
                if (cand_l, chosen_r) not in visited:
                    visited.add((cand_l, chosen_r))
                    queue.append((cand_l, chosen_r))

    return pair_dict

def local_conflict(pair_dict, cand_l, cand_r, all_neighbors):
    """
    若 cand_l 的某已匹配邻居 lN -> rN，但 rN 不在 cand_r 的邻居里，则冲突。
    """
    # cand_l 的已匹配邻居
    lN_list = [ln for ln in all_neighbors[cand_l] if ln in pair_dict]
    r_neighbors = set(all_neighbors[cand_r])

    for lN in lN_list:
        rN = pair_dict[lN]
        if rN not in r_neighbors:
            return True
    return False

# =============== 4) 三色标记与镜像 ===============
def check_symmetry_position(left_co, right_co, threshold=1e-6):
    """判断 two points 是否关于 X=0 成镜像。"""
    mirrored = Vector((-left_co.x, left_co.y, left_co.z))
    return (right_co - mirrored).length < threshold

def color_vertices_three_way(bm, pair_dict):
    """
    - 绿色(Green): 有对称配对，且坐标也对称
    - 蓝色(Blue):   有对称配对，但坐标尚未对称
    - 红色(Red):    未匹配
    """
    color_layer = bm.loops.layers.color.get("SymmetryColor")
    if not color_layer:
        color_layer = bm.loops.layers.color.new("SymmetryColor")

    reverse_dict = {r: l for l, r in pair_dict.items()}

    def get_color(v):
        idx = v.index
        if idx in pair_dict:
            # left 顶点
            r_idx = pair_dict[idx]
            v_r = bm.verts[r_idx]
            return (0.0, 1.0, 0.0, 1.0) if check_symmetry_position(v.co, v_r.co) else (0.0, 0.0, 1.0, 1.0)
        elif idx in reverse_dict:
            # right 顶点
            l_idx = reverse_dict[idx]
            v_l = bm.verts[l_idx]
            return (0.0, 1.0, 0.0, 1.0) if check_symmetry_position(v_l.co, v.co) else (0.0, 0.0, 1.0, 1.0)
        else:
            return (1.0, 0.0, 0.0, 1.0)

    for face in bm.faces:
        for loop in face.loops:
            loop[color_layer] = get_color(loop.vert)

def mirror_left_to_right(bm, pair_dict):
    """
    将 -X 侧顶点镜像到 +X 侧:
    仅对坐标不对称的配对进行坐标修正。
    """
    for l_idx, r_idx in pair_dict.items():
        v_left = bm.verts[l_idx]
        v_right = bm.verts[r_idx]
        # 保证 v_left 在 -X 侧，若相反则交换
        if v_left.co.x > v_right.co.x:
            v_left, v_right = v_right, v_left

        # 如果它们不对称，就把右侧镜像回左侧
        if not check_symmetry_position(v_left.co, v_right.co):
            # 将右侧顶点 v_right 坐标镜像到左侧
            mirror_pos = Vector((-v_right.co.x, v_right.co.y, v_right.co.z))
            v_left.co = mirror_pos

# =============== 5) 主函数入口 ===============
def main():
    obj = bpy.context.active_object
    if not obj or obj.type != 'MESH':
        print("请先选择一个网格对象并进入 Edit 模式。")
        return
    if bpy.context.mode != 'EDIT_MESH':
        print("脚本需要在 Edit 模式下运行。")
        return

    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.ensure_lookup_table()

    # 1) 获取初始配对（忽略中线顶点）
    init_pairs = get_symmetry_pairs_initial(bm, epsilon=1e-5)
    if not init_pairs:
        print("请先选中至少一对 -X/+X 对称顶点，才能建立初始配对。")
        return

    # 2) BFS 扩展
    pair_dict = expand_symmetry_pairs(bm, init_pairs)
    print(f"共匹配到 {len(pair_dict)} 对顶点。")

    # 3) 三色标记
    color_vertices_three_way(bm, pair_dict)

    # 4) 镜像 (可选)
    mirror_left_to_right(bm, pair_dict)

    # 5) 更新
    bmesh.update_edit_mesh(obj.data, loop_triangles=False, destructive=False)
    print("脚本执行完毕！")

# 若要粘贴后自动执行可取消注释
main()
