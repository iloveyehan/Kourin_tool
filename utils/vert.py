import bpy
import bmesh
import mathutils

import math
from mathutils import Vector, Quaternion
def get_selected_vert_order(bm):
    '''返回顶点历史 没有就返回none'''
    # 获取选择历史
    selected_verts = [ele for ele in bm.select_history if isinstance(ele, bmesh.types.BMVert)]
    if selected_verts:
        return selected_verts
    else:
        return None
def space_calculate_verts(bm_mod, interpolation, tknots, tpoints, points,
splines):
    move = []
    for p in points:
        m = tpoints[points.index(p)]
        if m in tknots:
            n = tknots.index(m)
        else:
            t = tknots[:]
            t.append(m)
            t.sort()
            n = t.index(m) - 1
        if n > len(splines) - 1:
            n = len(splines) - 1
        elif n < 0:
            n = 0

        if interpolation == 'cubic':
            ax, bx, cx, dx, tx = splines[n][0]
            x = ax + bx * (m - tx) + cx * (m - tx) ** 2 + dx * (m - tx) ** 3
            ay, by, cy, dy, ty = splines[n][1]
            y = ay + by * (m - ty) + cy * (m - ty) ** 2 + dy * (m - ty) ** 3
            az, bz, cz, dz, tz = splines[n][2]
            z = az + bz * (m - tz) + cz * (m - tz) ** 2 + dz * (m - tz) ** 3
            move.append([p, mathutils.Vector([x, y, z])])
        else:  # interpolation == 'linear'
            a, d, t, u = splines[n]
            move.append([p, ((m - t) / u) * d + a])

    return(move)
def get_connected_selections(edge_keys):
    # create connection data
    vert_verts = dict_vert_verts(edge_keys)
    print('vert_verts',vert_verts)
    # find loops consisting of connected selected edges
    loops = []
    while len(vert_verts) > 0:
        loop = [iter(vert_verts.keys()).__next__()]
        growing = True
        flipped = False

        # extend loop
        while growing:
            # no more connection data for current vertex
            if loop[-1] not in vert_verts:
                if not flipped:
                    loop.reverse()
                    flipped = True
                else:
                    growing = False
            else:
                extended = False
                for i, next_vert in enumerate(vert_verts[loop[-1]]):
                    if next_vert not in loop:
                        vert_verts[loop[-1]].pop(i)
                        if len(vert_verts[loop[-1]]) == 0:
                            del vert_verts[loop[-1]]
                        # remove connection both ways
                        if next_vert in vert_verts:
                            if len(vert_verts[next_vert]) == 1:
                                del vert_verts[next_vert]
                            else:
                                vert_verts[next_vert].remove(loop[-1])
                        loop.append(next_vert)
                        extended = True
                        break
                if not extended:
                    # found one end of the loop, continue with next
                    if not flipped:
                        loop.reverse()
                        flipped = True
                    # found both ends of the loop, stop growing
                    else:
                        growing = False

        # check if loop is circular
        if loop[0] in vert_verts:
            if loop[-1] in vert_verts[loop[0]]:
                # is circular
                if len(vert_verts[loop[0]]) == 1:
                    del vert_verts[loop[0]]
                else:
                    vert_verts[loop[0]].remove(loop[-1])
                if len(vert_verts[loop[-1]]) == 1:
                    del vert_verts[loop[-1]]
                else:
                    vert_verts[loop[-1]].remove(loop[0])
                loop = [loop, True]
            else:
                # not circular
                loop = [loop, False]
        else:
            # not circular
            loop = [loop, False]

        loops.append(loop)
        print('loops222',loop)
        print('loops222',loops)
    print('loops333', loops)
    return(loops)

def move_verts(object, bm, mapping, move, lock, influence):
    if lock:
        lock_x, lock_y, lock_z = lock
        orient_slot = bpy.context.scene.transform_orientation_slots[0]
        custom = orient_slot.custom_orientation
        if custom:
            mat = custom.matrix.to_4x4().inverted() @ object.matrix_world.copy()
        elif orient_slot.type == 'LOCAL':
            mat = mathutils.Matrix.Identity(4)
        elif orient_slot.type == 'VIEW':
            mat = bpy.context.region_data.view_matrix.copy() @ \
                object.matrix_world.copy()
        else:  # orientation == 'GLOBAL'
            mat = object.matrix_world.copy()
        mat_inv = mat.inverted()

    # get all mirror vectors
    mirror_Vectors = []
    if object.data.use_mirror_x:
        mirror_Vectors.append(mathutils.Vector((-1, 1, 1)))
    if object.data.use_mirror_y:
        mirror_Vectors.append(mathutils.Vector((1, -1, 1)))
    if object.data.use_mirror_x and object.data.use_mirror_y:
        mirror_Vectors.append(mathutils.Vector((-1, -1, 1)))
    z_mirror_Vectors = []
    if object.data.use_mirror_z:
        for v in mirror_Vectors:
            z_mirror_Vectors.append(mathutils.Vector((1, 1, -1)) * v)
        mirror_Vectors.extend(z_mirror_Vectors)
        mirror_Vectors.append(mathutils.Vector((1, 1, -1)))

    for loop in move:
        for index, loc in loop:
            if mapping:
                if mapping[index] == -1:
                    continue
                else:
                    index = mapping[index]
            if lock:
                delta = (loc - bm.verts[index].co) @ mat_inv
                if lock_x:
                    delta[0] = 0
                if lock_y:
                    delta[1] = 0
                if lock_z:
                    delta[2] = 0
                delta = delta @ mat
                loc = bm.verts[index].co + delta
            if influence < 0:
                new_loc = loc
            else:
                new_loc = loc * (influence / 100) + \
                                 bm.verts[index].co * ((100 - influence) / 100)

            for mirror_Vector in mirror_Vectors:
                for vert in bm.verts:
                    if vert.co == mirror_Vector * bm.verts[index].co:
                        vert.co = mirror_Vector * new_loc

            bm.verts[index].co = new_loc

    bm.normal_update()
    object.data.update()

    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

def calculate_splines(interpolation, bm_mod, tknots, knots):
    if interpolation == 'cubic':
        splines = calculate_cubic_splines(bm_mod, tknots, knots[:])
    else:  # interpolations == 'linear'
        splines = calculate_linear_splines(bm_mod, tknots, knots[:])

    return(splines)
def calculate_cubic_splines(bm_mod, tknots, knots):
    # hack for circular loops
    if knots[0] == knots[-1] and len(knots) > 1:
        circular = True
        k_new1 = []
        for k in range(-1, -5, -1):
            if k - 1 < -len(knots):
                k += len(knots)
            k_new1.append(knots[k - 1])
        k_new2 = []
        for k in range(4):
            if k + 1 > len(knots) - 1:
                k -= len(knots)
            k_new2.append(knots[k + 1])
        for k in k_new1:
            knots.insert(0, k)
        for k in k_new2:
            knots.append(k)
        t_new1 = []
        total1 = 0
        for t in range(-1, -5, -1):
            if t - 1 < -len(tknots):
                t += len(tknots)
            total1 += tknots[t] - tknots[t - 1]
            t_new1.append(tknots[0] - total1)
        t_new2 = []
        total2 = 0
        for t in range(4):
            if t + 1 > len(tknots) - 1:
                t -= len(tknots)
            total2 += tknots[t + 1] - tknots[t]
            t_new2.append(tknots[-1] + total2)
        for t in t_new1:
            tknots.insert(0, t)
        for t in t_new2:
            tknots.append(t)
    else:
        circular = False
    # end of hack

    n = len(knots)
    if n < 2:
        return False
    x = tknots[:]
    locs = [bm_mod.verts[k].co[:] for k in knots]
    result = []
    for j in range(3):
        a = []
        for i in locs:
            a.append(i[j])
        h = []
        for i in range(n - 1):
            if x[i + 1] - x[i] == 0:
                h.append(1e-8)
            else:
                h.append(x[i + 1] - x[i])
        q = [False]
        for i in range(1, n - 1):
            q.append(3 / h[i] * (a[i + 1] - a[i]) - 3 / h[i - 1] * (a[i] - a[i - 1]))
        l = [1.0]
        u = [0.0]
        z = [0.0]
        for i in range(1, n - 1):
            l.append(2 * (x[i + 1] - x[i - 1]) - h[i - 1] * u[i - 1])
            if l[i] == 0:
                l[i] = 1e-8
            u.append(h[i] / l[i])
            z.append((q[i] - h[i - 1] * z[i - 1]) / l[i])
        l.append(1.0)
        z.append(0.0)
        b = [False for i in range(n - 1)]
        c = [False for i in range(n)]
        d = [False for i in range(n - 1)]
        c[n - 1] = 0.0
        for i in range(n - 2, -1, -1):
            c[i] = z[i] - u[i] * c[i + 1]
            b[i] = (a[i + 1] - a[i]) / h[i] - h[i] * (c[i + 1] + 2 * c[i]) / 3
            d[i] = (c[i + 1] - c[i]) / (3 * h[i])
        for i in range(n - 1):
            result.append([a[i], b[i], c[i], d[i], x[i]])
    splines = []
    for i in range(len(knots) - 1):
        splines.append([result[i], result[i + n - 1], result[i + (n - 1) * 2]])
    if circular:  # cleaning up after hack
        knots = knots[4:-4]
        tknots = tknots[4:-4]

    return(splines)

def calculate_linear_splines(bm_mod, tknots, knots):
    splines = []
    for i in range(len(knots) - 1):
        a = bm_mod.verts[knots[i]].co
        b = bm_mod.verts[knots[i + 1]].co
        d = b - a
        t = tknots[i]
        u = tknots[i + 1] - t
        splines.append([a, d, t, u])  # [locStart, locDif, tStart, tDif]

    return(splines)
def space_calculate_t(bm_mod, knots):
    print('k',knots)
    tknots = []  # 存储每个节点到当前节点的累积长度
    loc_prev = False  # 前一个位置的标记
    len_total = 0  # 总长度初始化为0
    for k in knots:
        loc = mathutils.Vector(bm_mod.verts[k].co[:])  # 获取当前节点的位置
        if not loc_prev:
            loc_prev = loc  # 如果前一个位置未设置，则将当前节点位置赋值给它
        len_total += (loc - loc_prev).length  # 计算当前节点与前一个节点的距离并累加
        tknots.append(len_total)  # 将当前总长度添加到 tknots 列表中
        loc_prev = loc  # 更新前一个位置为当前节点位置
    amount = len(knots)  # 节点的总数量
    t_per_segment = len_total / (amount - 1)  # 计算每个段的长度
    tpoints = [i * t_per_segment for i in range(amount)]  # 生成每个节点的参数值
    print('tknots',tknots, 'tpoints',tpoints)
    return(tknots, tpoints)  # 返回累积长度和参数值列表
def check_loops(loops, bm_mod):
    valid_loops = []  # 用于存储有效的环
    for loop, circular in loops:
        # 环需要至少有3个顶点
        if len(loop) < 3:
            continue
        # 顶点不能全部位于同一位置
        stacked = True
        for i in range(len(loop) - 1):
            # 检查相邻顶点之间的距离
            if (bm_mod.verts[loop[i]].co - bm_mod.verts[loop[i + 1]].co).length > 1e-6:
                stacked = False  # 如果距离大于阈值，则不堆叠
                break
        if stacked:
            continue  # 如果所有顶点都堆叠，跳过该环
        # 通过所有测试，环是有效的
        valid_loops.append([loop, circular])  # 将有效的环添加到列表中
    return valid_loops
# 输入：边的键列表（edge_keys），输出：表示顶点-顶点连接关系的字典
def dict_vert_verts(edge_keys):
    # 创建用于存储连接关系的字典
    vert_verts = {}

    # 遍历每条边
    for ek in edge_keys:
        # 遍历边的两个顶点
        for i in range(2):
            # 如果当前顶点已经在字典中，则将另一个顶点添加到其相邻顶点列表中
            if ek[i] in vert_verts:
                vert_verts[ek[i]].append(ek[1 - i])
            # 如果当前顶点不在字典中，则创建新条目，并将另一个顶点作为初始值
            else:
                vert_verts[ek[i]] = [ek[1 - i]]

    # 返回构建好的字典
    return vert_verts
def AriAlignmentSemicircle(chain, inputAngle, moveTrue, circleTrue, angleTrue, regularTrue, plantTrue):
    # 如果顶点列表的数量小于等于2，则返回0
    if len(chain) <= 2:
        return 0

    verList_pos = []

    # 获取每个顶点的位置坐标
    verList_pos = [v.co.copy() for v in chain]

    target_first_pos = verList_pos[0]  # 获取第一个顶点位置
    target_end_pos = verList_pos[-1]   # 获取最后一个顶点位置
    target_vector = target_end_pos - target_first_pos  # 计算向量

    # 计算中心点位置
    centerPos = sum(verList_pos, Vector()) / len(verList_pos)
    vectorList = []
    triangleNormal = []

    # 计算每个顶点相对于中心点的向量
    for i in range(len(verList_pos)):
        vec1 = verList_pos[i] - centerPos
        vectorList.append(vec1)

        if i + 1 < len(verList_pos):
            vec2 = verList_pos[i + 1] - centerPos
        else:
            vec2 = verList_pos[0] - centerPos

        normal = vec1.cross(vec2)
        if normal.length != 0:
            normal.normalize()
        triangleNormal.append(normal)

    # 计算中心法向量
    centerNormal = sum(triangleNormal, Vector()) / len(triangleNormal)
    if centerNormal.length != 0:
        centerNormal.normalize()
    else:
        centerNormal = Vector((0, 0, 1))

    # 如果不需要使用输入角度，则计算平均角度
    if not angleTrue:
        angleTotal_rad = 0
        for i in range(1, len(verList_pos) - 1):
            angleTotal_rad += (verList_pos[i] - target_first_pos).angle(verList_pos[i] - target_end_pos)
        angleAbe_rad = angleTotal_rad / (len(verList_pos) - 2)
        angleAbe_deg = math.degrees(angleAbe_rad)
        angleAbe_deg = 360 - (angleAbe_deg * 2)
        inputAngle = angleAbe_deg

    # 计算半径
    radAngle = math.radians((360 - inputAngle) / 2.0)
    firstEndPosDistance = (target_first_pos - target_end_pos).length
    distance = (firstEndPosDistance / 2) / math.sin(radAngle)

    # 如果不需要移动，直接返回输入角度
    if not moveTrue:
        return inputAngle

    thre = 0.1
    if -thre < inputAngle < thre:
        # 如果输入角度接近0，则执行等距离移动操作
        for ii in range(len(chain)):
            per = float(ii) / (len(chain) - 1)
            movePos = target_first_pos.lerp(target_end_pos, per)
            chain[ii].co = movePos
        return distance

    basePosList = []
    movePosList = []
    verTotal = len(chain)
    rot = inputAngle / (verTotal - 1)  # 计算旋转角度

    if regularTrue:
        # 如果需要规则排列，则计算每个顶点的新位置
        for i in range(verTotal):
            rad = math.radians(rot * i + 180 - (inputAngle / 2.0))
            x = distance * math.sin(rad)
            y = distance * math.cos(rad)
            basePosList.append(Vector((x, y, 0)))

        baseNormal = Vector((0, 0, -1))
        base_vector = Vector((-1, 0, 0))
        movePosList = basePosList.copy()

        vector_cross = base_vector.cross(target_vector)
        vector_angle = base_vector.angle(target_vector)
        if vector_cross.length != 0:
            vector_cross.normalize()
        else:
            vector_cross = Vector((0, 0, 1))

        # 旋转中心法向量
        rot_q = Quaternion(vector_cross, vector_angle)
        rotTargetVec = rot_q @ centerNormal

        rotTargetFrontVec = Vector((0, rotTargetVec.y, rotTargetVec.z))
        first_cross = baseNormal.cross(rotTargetFrontVec)
        first_angle = baseNormal.angle(rotTargetFrontVec)
        if first_cross.x < 0:
            first_angle = -first_angle

        # 旋转每个顶点的位置
        rot_matrix = mathutils.Matrix.Rotation(first_angle, 4, 'X')
        movePosList = [pos @ rot_matrix for pos in movePosList]

        # 反向旋转位置数组
        rot_q_inv = Quaternion(vector_cross, -vector_angle)
        movePosList = [rot_q_inv @ pos for pos in movePosList]

        # 平移每个顶点的位置
        translateVal = target_first_pos - movePosList[0]
        movePosList = [pos + translateVal for pos in movePosList]

    else:
        # 如果不需要规则排列，则执行自定义移动操作
        currentTool = bpy.context.workspace.tools.from_space_view3d_mode(bpy.context.mode).idname
        currentToolTrue = currentTool in {"builtin.move", "builtin.rotate", "builtin.scale"}

        if currentToolTrue:
            centerPos = bpy.context.scene.cursor.location  # 如果当前工具是移动、旋转或缩放工具，则获取操纵器位置作为中心点

        for i in range(len(chain)):
            movePosList.append(chain[i].co.copy())
            crossNormal = target_vector.cross(centerNormal)
            verticalNormal = target_vector.cross(crossNormal)
            if verticalNormal.length == 0:
                continue

            if plantTrue:
                # 计算在法向量平面上的投影点
                plane_co = target_first_pos
                plane_no = verticalNormal.normalized()
                point = movePosList[i]
                plane_point = point - plane_no.dot(point - plane_co) * plane_no
                movePosList[i] = plane_point

            if circleTrue:
                # 更新位置为圆上的点
                circleCenter = ((distance) * math.cos(math.radians(inputAngle / 2))) * (-crossNormal.normalized()) + ((target_first_pos + target_end_pos) / 2)
                planePosNormalize = (movePosList[i] - circleCenter).normalized()
                movePosList[i] = distance * planePosNormalize + circleCenter

    # 移动顶点到新位置
    for i in range(len(chain)):
        chain[i].co = movePosList[i]

    return distance
def AriTransferPosition_ArrayContainsArray(verListA, verListB):
    """
    返回 verListA 中也存在于 verListB 的元素(交集)，并保持 A 的遍历顺序。
    相当于 Maya 里的: stringArrayContains($ver, $verListB)
    """
    setB = set(verListB)
    result = []
    for ver in verListA:
        if ver in setB:
            result.append(ver)
    return result


def AriTransferPosition_CircumferenceUV(obj, vertex_index_list, mode):
    """
    在Blender中模仿 Maya 的 vtx->(edge/face)->tuv 逻辑，返回新的“UV组件”集合。
    这里会返回"loop indices"或"map indices"之类的概念，用以区分 UV。
    实际中你可能需要存储成字符串 "obj.map[x]" 形式，或直接存成 loop index。
    """
    mesh = obj.data
    mesh.update()

    if not mesh.uv_layers.active:
        # 没有UV层
        return []

    # 收集所有和 vertex_index_list 相关的 “目标UV”
    # step1: 根据 mode (0=edge, 1=face) 收集相邻 loops
    new_loops = set()

    if mode == 0:
        # vtx->edges->所有关联的loops
        for v_idx in vertex_index_list:
            for e in mesh.vertices[v_idx].link_edges:
                # e 关联的两端顶点 => 找这些顶点所在的 loop
                for edge_v in e.vertices:
                    # 查找 mesh.loops 中所有 vertex_index = edge_v
                    for loop_i, loop in enumerate(mesh.loops):
                        if loop.vertex_index == edge_v:
                            new_loops.add(loop_i)

    else:
        # vtx->faces->所有关联的loops
        for v_idx in vertex_index_list:
            for poly in mesh.polygons:
                if v_idx in poly.vertices:
                    # 把这个 polygon 的所有 loop 都收集
                    for loop_i in poly.loop_indices:
                        new_loops.add(loop_i)

    # step2: “转为 UV 组件”
    # 在 Blender 里, 每个 loop_i 对应一个 UV 坐标 (uv_layers.active.data[loop_i].uv)
    # 如果你想返回“loop index”就可以直接使用
    new_uvs = list(new_loops)

    # step3: 根据 Maya 脚本做法，还要"去掉原先的 verList"。
    # 但注意：Maya 中的 verList 是 “UV 组件字符串”，这里却是顶点索引/loop index，不一样。
    # 这里我们只能做一个简单演示：假设 vertex_index_list 也是 loop index（或者 map index）。
    # 如果你真想精确模拟，需要把 “verList[]” 当成 “已经是UV”的集合，然后再去除即可。
    # 在此就不做严格的移除动作了:

    # 直接返回 new_uvs
    return new_uvs


def AriTransferPosition_valMuch(valA, valB, gosa):
    """
    检查 valA, valB (长度=3) 在每个分量上是否满足:
      abs(valA[i] - valB[i]) <= gosa
    如果全部分量都满足，返回 1；否则返回 0。
    """
    # 假设 valA, valB 是 [x, y, z] 的 list 或 tuple
    for i in range(3):
        if not (valB[i] - gosa <= valA[i] <= valB[i] + gosa):
            return 0
    return 1

def AriTransferPosition_CircumferenceVer(obj, vertex_index_list, mode):
    """
    在Blender中模拟:
      - 若mode=0:  vtx -> edges -> vtx
      - 若mode=1:  vtx -> faces -> vtx
    并把原来的顶点从结果中去掉, 得到类似 Maya 里的 “外圈” 顶点集合。
    参数:
      obj: bpy.types.Object，目标网格对象
      vertex_index_list: 要扩展的顶点索引列表 (如 [0,1,2,...])
      mode: 0或1，控制不同的拓扑扩展方式
    返回:
      list[int]，新的顶点索引 (不包含原来的 vertex_index_list)
    """
    mesh = obj.data
    mesh.update()

    new_vertices = set()

    if mode == 0:
        # vtx -> edges -> vtx
        for v_idx in vertex_index_list:
            # 找到 v_idx 顶点关联的所有边
            for e in mesh.vertices[v_idx].link_edges:
                # e.vertices 是一对端点
                new_vertices.update(e.vertices)
    else:
        # vtx -> faces -> vtx
        # Blender里无法直接从 "vertex.link_faces" 拿到面，需要自己遍历 polygons
        for v_idx in vertex_index_list:
            for poly in mesh.polygons:
                if v_idx in poly.vertices:
                    # 把这个 polygon 里的所有顶点都加入
                    for fv in poly.vertices:
                        new_vertices.add(fv)

    # 去除原先传入的顶点
    original_set = set(vertex_index_list)
    result = list(new_vertices - original_set)
    return result
def get_vertex_uv(obj, v_idx):
    """
    在Blender中，根据顶点索引取UV。
    注意Blender是loop->UV->vertex的关系，这里仅简单拿第一个匹配的loop UV。
    真实需求中你可能想找所有loop再做平均值。
    """
    mesh = obj.data
    uv_layer = mesh.uv_layers.active
    if not uv_layer:
        return (0.0, 0.0)
    # 遍历所有loop，找到 vertex_index = v_idx 的那个，然后取 uv
    for poly in mesh.polygons:
        for loop_idx in poly.loop_indices:
            if mesh.loops[loop_idx].vertex_index == v_idx:
                return uv_layer.data[loop_idx].uv
    return (0.0, 0.0)

def set_vertex_uv(obj, v_idx, uv_val):
    """
    为顶点v_idx写入UV(只写一个loop)。
    如果一个顶点在多个loop出现，这里只写第一个找到的loop。
    """
    mesh = obj.data
    uv_layer = mesh.uv_layers.active
    if not uv_layer:
        return
    for poly in mesh.polygons:
        for loop_idx in poly.loop_indices:
            if mesh.loops[loop_idx].vertex_index == v_idx:
                uv_layer.data[loop_idx].uv = (uv_val[0], uv_val[1])
                return

def AriTransferPosition_GoSymmetryTP(obj,UnSymmetry_plus: list[int],UnSymmetry_minus: list[int],plus_pivPos: Vector,minus_pivPos: Vector,UVMode: int,gosa: float,loop_count: int,use_world: bool) -> list[int]:
    """
    在Blender中大致复刻Maya版AriTransferPosition_GoSymmetryTP的逻辑。
    返回处理后剩余的UnSymmetry_minus(或你想要的其它数据)。
    """
    # 注意: Maya脚本里有很多UI进度条/label操作等，这里简化为print
    print("==== Start AriTransferPosition_GoSymmetryTP ====")
    print(f"  UVMode = {UVMode}, gosa = {gosa}, loop_count = {loop_count}")

    mesh = obj.data
    mesh.update()

    # Maya脚本里把不对称顶点数量作为进度总量
    UnSymmeBeforeTotal = len(UnSymmetry_plus)
    moveCounter = 0
    breakTrue = False

    prop=bpy.context.scene.ari_transfer_position_settings
    loop=prop.iterations
    # 记录上两次循环里“不对称列表”的大小，以判断是否“本轮循环没新发现”
    loopVerTotal = [0, 0]

    # 实际上循环次数是 loop_count*2, 这里按你的原脚本写法
    loop = loop * 2
    worldTrue=prop.world_space
    for ii in range(loop):
        if breakTrue:
            break

        if len(UnSymmetry_plus) == 0:
            break

        # 检测是否出现“连续两次循环无新匹配”的情况
        circMode = ii % 2
        if (loopVerTotal[circMode] == len(UnSymmetry_plus) and
            loopVerTotal[circMode] == loopVerTotal[1 - circMode]):
            break
        loopVerTotal[circMode] = len(UnSymmetry_plus)

        # 1) 取得外圈顶点(根据UVMode选择几何还是UV)
        if UVMode == 0:
            extendVers_plus_num  = AriTransferPosition_CircumferenceVer(obj, UnSymmetry_plus, circMode)
            extendVers_minus_num = AriTransferPosition_CircumferenceVer(obj, UnSymmetry_minus, circMode)
        else:
            extendVers_plus_num  = AriTransferPosition_CircumferenceUV(obj, UnSymmetry_plus, circMode)
            extendVers_minus_num = AriTransferPosition_CircumferenceUV(obj, UnSymmetry_minus, circMode)

        # 2) 获取坐标(或UV)并做对称匹配
        extendVers_plus_pos = []
        for vidx in extendVers_plus_num:
            if UVMode == 0:
                if use_world:
                    world_co = obj.matrix_world @ mesh.vertices[vidx].co
                    extendVers_plus_pos.append(world_co)
                else:
                    extendVers_plus_pos.append(mesh.vertices[vidx].co)
            else:
                # UV 模式，需要拿该顶点对应的UV。
                # 这里简单地从第一个loop里获取; 真实使用时要找所有loop做平均等处理
                uv = get_vertex_uv(obj, vidx)
                extendVers_plus_pos.append(Vector((uv[0], uv[1], 0.0)))

        extendVers_minus_pos = []
        for vidx in extendVers_minus_num:
            if UVMode == 0:
                if use_world:
                    world_co = obj.matrix_world @ mesh.vertices[vidx].co
                    extendVers_minus_pos.append(world_co)
                else:
                    extendVers_minus_pos.append(mesh.vertices[vidx].co)
            else:
                uv = get_vertex_uv(obj, vidx)
                extendVers_minus_pos.append(Vector((uv[0], uv[1], 0.0)))

        # 匹配
        extendVers_plus_sym = []
        extendVers_minus_sym = []

        for i, p_pos in enumerate(extendVers_plus_pos):
            p_local = p_pos - plus_pivPos  # Maya脚本中的减pivot
            for j, m_pos in enumerate(extendVers_minus_pos):
                m_local = m_pos - minus_pivPos
                if AriTransferPosition_valMuch(p_local, m_local, gosa):
                    # 找到匹配
                    extendVers_plus_sym.append(extendVers_plus_num[i])
                    extendVers_minus_sym.append(extendVers_minus_num[j])
                    break

        # 3) 把匹配到的点，从不对称队列中剔除
        newSym_main = []
        newSym_sub  = []

        for i, minus_v in enumerate(extendVers_minus_sym):
            # 查找是否可移动
            # 这里参考Maya脚本的做法：先找该 minus_v 的周边，再对照 plus 匹配
            subOne_extendVers = []
            if UVMode == 0:
                subOne_extendVers = AriTransferPosition_CircumferenceVer(obj, [minus_v], circMode)
            else:
                subOne_extendVers = AriTransferPosition_CircumferenceUV(obj, [minus_v], circMode)

            exUnSymList = AriTransferPosition_ArrayContainsArray(subOne_extendVers, UnSymmetry_minus)
            if len(exUnSymList) == 1:
                # 有一个可以移动
                moveCounter += 1

                # 找对应的 plus 顶点
                plus_v = extendVers_plus_sym[i]
                mainOne_ExtendVers = []
                if UVMode == 0:
                    mainOne_ExtendVers = AriTransferPosition_CircumferenceVer(obj, [plus_v], circMode)
                else:
                    mainOne_ExtendVers = AriTransferPosition_CircumferenceUV(obj, [plus_v], circMode)

                exUnSymList2 = AriTransferPosition_ArrayContainsArray(mainOne_ExtendVers, UnSymmetry_plus)
                if len(exUnSymList2) == 0:
                    # 防御式判断，可能找不到对应
                    continue
                mainVer = exUnSymList2[0]

                # 拿 mainVer 的坐标
                if UVMode == 0:
                    if use_world:
                        pos = obj.matrix_world @ mesh.vertices[mainVer].co
                    else:
                        pos = mesh.vertices[mainVer].co
                else:
                    uv = get_vertex_uv(obj, mainVer)
                    pos = Vector((uv[0], uv[1], 0.0))

                # 执行“移动 minus 侧点”
                if UVMode == 0:
                    # 计算出跟 pivot 对应的差值
                    delta = (pos + minus_pivPos - plus_pivPos)
                    # 直接改 minus_v
                    if use_world:
                        # 需要先把pos转回局部空间才能赋值
                        local_goal = obj.matrix_world.inverted() @ delta
                        mesh.vertices[minus_v].co = local_goal
                    else:
                        mesh.vertices[minus_v].co = delta
                else:
                    # UV模式下，直接改UV
                    set_vertex_uv(obj, minus_v, (pos.x, pos.y))

                newSym_main.append(mainVer)
                newSym_sub.append(minus_v)

        # 把 newSym_main / newSym_sub 从不对称队列里去掉
        UnSymmetry_plus  = list(set(UnSymmetry_plus)  - set(newSym_main))
        UnSymmetry_minus = list(set(UnSymmetry_minus) - set(newSym_sub))

        # 如果你想看中断条件之类可以再加，这里就不详细演示

    print(f"Total moved: {moveCounter} of {UnSymmeBeforeTotal}")
    return UnSymmetry_minus
import bpy
import bmesh
from mathutils import Vector
import bpy
import bmesh
from mathutils import Vector

def AriTransferPosition_MoveVerPos(obj,
                                   comp_list,
                                   pos_list,
                                   pivotPos=Vector((0,0,0)),
                                   UVMode=0,
                                   worldTrue=False):
    """
    在Blender中模拟 '移动顶点或UV到指定位置' 的逻辑（仿 Maya 的 AriTransferPosition_MoveVerPos）。

    参数：
      obj       : bpy.types.Object，需要操作的网格对象 (Mesh)。
      comp_list : 要移动的组件列表，可以是类似 ["Cube.vtx[0]", ...] / ["Cube.map[5]", ...]，
                  或者干脆就是[0,1,2,...] (索引列表)。具体取决于你的使用场景。
      pos_list  : 新位置坐标（或相对移动值）。
                  - 如果是单个 Vector，则对所有组件都用同一个位置/偏移；
                  - 如果是与 comp_list 等长的列表，则逐一对应移动。
      pivotPos  : Pivot 点坐标，用于在局部或世界空间移动时的坐标修正。
      UVMode    : 0 => 移动顶点；1 => 移动 UV。
      worldTrue : 是否使用世界坐标（仅对 UVMode=0 生效）。
    """

    if obj.type != 'MESH':
        print(f"Object {obj.name} is not a Mesh. Abort.")
        return

    # 将 pos_list 统一转成 list[Vector]
    # 如果只给了一个 Vector，就让它套到所有组件
    if isinstance(pos_list, Vector):
        pos_list = [pos_list] * len(comp_list)
    if len(pos_list) != len(comp_list):
        print("pos_list 与 comp_list 数量不一致。请检查输入。")
        return

    # 如果要在Edit Mode下修改，需要拿到 bmesh
    was_in_edit_mode = (bpy.context.mode == 'EDIT_MESH')
    if not was_in_edit_mode:
        # 如果脚本需要自动切换
        bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(obj.data)

    # 若UVMode=1，需要 uv_layer
    uv_layer = None
    if UVMode == 1:
        uv_layer = bm.loops.layers.uv.active
        if not uv_layer:
            print("当前网格无UV层，或未激活UV层。")
            return

    # 构建： 顶点Index -> bmesh.verts[v_idx]   或   loopIndex -> bmesh.loops[loop_idx]
    # 1) 如果你 comp_list 里是 "Cube.vtx[10]"，就需要解析出 index=10
    # 2) 如果你 comp_list 里是 "Cube.map[5]"，就需要解析出 loopIndex=5
    # 这里示例一个简易的 parser
    # 如果你已经有纯数字的索引列表，就可跳过这一步。
    def parse_index(s):
        # 假设 s 类似 "Cube.vtx[10]" 或 "Cube.map[5]"
        # 我们只取中括号里的数
        if "[" in s and "]" in s:
            return int(s[s.index("[")+1 : s.index("]")])
        else:
            return int(s)  # 如果就是纯数字也行

    # 根据 worldTrue 决定如何转换坐标
    inv_mat = obj.matrix_world.inverted()

    # 遍历 comp_list，并执行移动
    for i, comp_str in enumerate(comp_list):
        new_pos = pos_list[i]

        if UVMode == 0:
            # 移动 mesh 顶点
            v_idx = parse_index(comp_str) if isinstance(comp_str, str) else comp_str
            v = bm.verts[v_idx]

            # Maya 脚本里 typical:
            #    if(worldTrue) move -ws to (pos + pivotPos) ...
            #    else          move -ls ...
            # 这里 “pos” 可能是绝对坐标，也可能是相对位移 -- 视你的需求而定。
            # 假设是绝对位置：
            if worldTrue:
                # 先把 new_pos 转为局部坐标 => local_goal
                # 同时如果你想减 pivotPos.x,y,z，也要先转到世界，然后再 subtract pivot
                # 具体看你 pivotPos 在世界还是局部
                local_goal = inv_mat @ new_pos
                if pivotPos.length > 1e-6:
                    local_goal -= inv_mat @ pivotPos
                v.co = local_goal
            else:
                # 局部坐标下，直接 - pivotPos
                # pivotPos 假设也是局部
                v.co = (v.co * 0.0) + (new_pos - pivotPos)

        else:
            # UVMode == 1，移动 UV
            loop_idx = parse_index(comp_str) if isinstance(comp_str, str) else comp_str
            # 需要找到 bmesh 中的 loop. Blender 里 bmesh.loops 并不保证 loop_idx == loops[i].index
            # loop.index 可能与 i 不一致。需要手动查找:
            target_loop = None
            for l in bm.loops:
                if l.index == loop_idx:
                    target_loop = l
                    break

            if not target_loop:
                continue

            # 在 Maya 中 polyEditUV -u x -v y 是绝对还是相对？ 这里示例直接设为绝对
            # new_pos.x, new_pos.y => uv
            # pivotPos 对 UV 通常没意义，如有需求，可自行减/加
            uv_data = target_loop[uv_layer]
            uv_data.uv.x = new_pos.x
            uv_data.uv.y = new_pos.y

    # 提交 bmesh 变更到 mesh
    bmesh.update_edit_mesh(obj.data)

    # 如果原先不是Edit Mode，可以切回去
    if not was_in_edit_mode:
        bpy.ops.object.mode_set(mode='OBJECT')

    print("AriTransferPosition_MoveVerPos done.")


def AriTransferPosition_GetVer(UVMode: int):
    """
    在Blender中模拟“获取选中顶点/UV”的逻辑。
    - UVMode=0:  获取选中的几何顶点
    - UVMode=1:  获取选中的UV坐标(对应loop)
    返回一个字符串列表，格式类似: ["MyMesh.vtx[0]", "MyMesh.vtx[15]", ...] 或 ["MyMesh.map[7]", ...]
    """

    # 1) 确保我们有一个激活对象
    obj = bpy.context.active_object
    if not obj or obj.type != 'MESH':
        print("No active mesh object found or object is not a mesh.")
        return []

    # 2) 确保处于Edit Mode，才能获取编辑状态下的顶点/UV选择
    if bpy.context.mode != 'EDIT_MESH':
        print("Please switch to Edit Mode.")
        return []

    mesh = obj.data
    # 3) 从Edit Mesh读取bmesh
    bm = bmesh.from_edit_mesh(mesh)

    # 用于存储结果的字符串列表
    results = []

    if UVMode == 0:
        # ---- 获取选中的顶点 ----
        # 在Blender中，bmesh的顶点有 v.select 来表示是否被选中
        for v in bm.verts:
            if v.select:
                # 模拟 Maya 的 "transform.vtx[index]" 字符串
                # 可以自定义成你想要的格式
                results.append(f"{obj.name}.vtx[{v.index}]")

    elif UVMode == 1:
        # ---- 获取选中的UV ----
        # 首先获取当前活动的 uv_layer
        uv_layer = bm.loops.layers.uv.active
        if not uv_layer:
            print("No active UV layer found.")
            return []

        # 遍历所有面，在face.loops中查看loop对应的UV选择
        for face in bm.faces:
            for loop in face.loops:
                # loop[uv_layer].select_uv 表示是否选中了该UV
                if loop[uv_layer].select_uv:
                    # Blender里每个loop有一个index，但并不直接对应 Maya 的 map[index]
                    # 这里我们简单地把 loop.index 当作“map”索引。
                    # 你也可以记录 face.index+loop.index 或其他方式来区分
                    results.append(f"{obj.name}.map[{loop.index}]")

    # 4) 返回最终的字符串列表
    return results
