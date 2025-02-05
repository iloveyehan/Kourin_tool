import heapq

from mathutils import Vector, Matrix
from mathutils.geometry import intersect_line_plane


def dijkstra(start_vert, end_vert, adjacency):
    """Dijkstra算法寻找最短路径"""
    distances = {v: float('inf') for v in adjacency}
    predecessors = {}
    distances[start_vert] = 0
    heap = [(0, start_vert)]

    while heap:
        current_dist, u = heapq.heappop(heap)
        if u == end_vert:
            break
        if current_dist > distances[u]:
            continue
        for v, weight in adjacency[u]:
            if distances[v] > current_dist + weight:
                distances[v] = current_dist + weight
                predecessors[v] = u
                heapq.heappush(heap, (distances[v], v))

    path = []
    current = end_vert
    while current in predecessors:
        path.insert(0, current)
        current = predecessors[current]
    if path:
        path.insert(0, start_vert)
    return path
# 根据给定的位置创建平移矩阵
def create_translation_matrix(location):
    """
    创建一个平移矩阵，用于将对象移动到指定的位置。
    参数:
    location -- 一个三维向量，表示平移的位置 (x, y, z)
    返回:
    一个表示平移的 4x4 矩阵
    """
    return Matrix.Translation(location)


# 根据给定的旋转创建旋转矩阵
def create_rotation_matrix(rotation):
    """
    创建一个旋转矩阵，用于将对象旋转到指定的方向。
    参数:
    rotation -- 一个四元数或欧拉角对象，表示旋转的方向
    返回:
    一个表示旋转的 4x4 矩阵
    """
    return rotation.to_matrix().to_4x4()


# 根据给定的缩放值创建缩放矩阵
def create_scale_matrix(scale):
    """
    创建一个缩放矩阵，用于将对象缩放到指定的大小。
    参数:
    scale -- 一个三维向量，表示每个轴的缩放因子 (x, y, z)
    返回:
    一个表示缩放的 4x4 矩阵
    """
    # 创建一个单位矩阵
    scale_matrix = Matrix.Identity(4)
    # 设置每个轴的缩放因子
    for i in range(3):
        scale_matrix[i][i] = scale[i]
    return scale_matrix


def get_world_space_normal(normal, matrix):
    """
    将法线向量转换到世界坐标系。
    """
    return (matrix.to_3x3() @ normal).normalized()


def average_normals(normals):
    """
    计算一组法线向量的平均法线。
    """
    return sum(normals, Vector()) / len(normals)


def average_locations(locations):
    """计算一组坐标的平均值"""
    avg = sum(locations, Vector()) / len(locations)
    return avg


def get_center_between_verts(vert1, vert2):
    """获取两顶点之间的中心点"""
    return (vert1.co + vert2.co) / 2


def create_rotation_matrix_from_vertex(obj, vert):
    """从顶点创建旋转矩阵"""
    # 获取顶点关联的面来计算法线
    linked_faces = vert.link_faces
    if linked_faces:
        normal = sum((face.normal for face in linked_faces), Vector()) / len(linked_faces)
        normal.normalize()
    else:
        # 如果没有关联的面，使用对象的Z轴
        normal = Vector((0, 0, 1))

    # 构建旋转矩阵，使Z轴与法线对齐
    rotation_matrix = normal.to_track_quat('Z', 'Y').to_matrix().to_4x4()
    return rotation_matrix


def get_world_space_normal(normal, matrix):
    """ 将法线向量转换到世界坐标系 """
    return (matrix.to_3x3() @ normal).normalized()


def create_rotation_matrix_from_edge(context, obj_matrix, edge):
    """
    从边创建旋转矩阵。
    :param context: Blender上下文，用于访问视图参数。
    :param obj_matrix: 对象的世界矩阵。
    :param edge: 边对象，包含两个顶点。
    :return: 一个旋转矩阵，将边的方向对齐到Y轴，并考虑视图方向和连接面法线。
    """
    # 计算边向量并归一化，得到副法线向量
    edge_vector = (obj_matrix.to_3x3() @ (edge.verts[1].co - edge.verts[0].co)).normalized()

    # 获取视图的向上方向
    view_up = context.space_data.region_3d.view_rotation @ Vector((0, 1, 0))

    # 如果副法线与视图向上方向的点积为负，则反向副法线
    if edge_vector.dot(view_up) < 0:
        edge_vector.negate()

    # 如果边连接有面，则平均这些面的法线，并转换到世界空间
    if edge.link_faces:
        normals = [get_world_space_normal(face.normal, obj_matrix) for face in edge.link_faces]
        normal = average_normals(normals).normalized()

        # 计算切线，为副法线与法线的叉积
        tangent = edge_vector.cross(normal).normalized()

        # 重新计算法线，确保正交
        normal = tangent.cross(edge_vector).normalized()
    else:
        # 如果边没有连接面，使用全局向上方向
        global_up = (obj_matrix.to_3x3() @ Vector((0, 0, 1))).normalized()

        # 如果副法线与全局向上方向共线，使用全局向右方向
        if abs(round(edge_vector.dot(global_up), 6)) == 1:
            global_up = (obj_matrix.to_3x3() @ Vector((1, 0, 0))).normalized()

        # 计算切线和法线
        tangent = edge_vector.cross(global_up).normalized()
        normal = tangent.cross(edge_vector)

    # 构造旋转矩阵
    rotation_matrix = Matrix.Identity(4)
    rotation_matrix.col[0].xyz = tangent
    rotation_matrix.col[1].xyz = edge_vector

    rotation_matrix.col[2].xyz = normal

    return rotation_matrix


def is_circle(face, face_center, threshold):
    """ 判断面是否为圆形 """
    edge_lengths = [e.calc_length() for e in face.edges]
    center_distances = [(v.co - face_center).length for v in face.verts]
    avg_edge_length = sum(edge_lengths) / len(edge_lengths)
    avg_center_distance = sum(center_distances) / len(center_distances)
    return all(abs(l - avg_edge_length) < avg_edge_length * threshold for l in edge_lengths) and \
        all(abs(d - avg_center_distance) < avg_center_distance * threshold for d in center_distances)


def calculate_binormal_for_circle(face, face_center, normal, matrix):
    """ 计算圆形面的副法线 """
    for axis in [Vector((0, 1, 0)), Vector((1, 0, 0)), Vector((0, 0, 1))]:
        intersection = intersect_line_plane(face_center + axis, face_center - axis, face_center, normal)
        if intersection:
            projected = intersection - face_center
            if projected.length_squared > 0:
                return (matrix.to_3x3() @ projected).normalized()
    return None


def calculate_binormal_from_edges(face, matrix, edge_pair):
    """ 从边或边对计算副法线 """
    if edge_pair:
        return (matrix.to_3x3() @ face.calc_tangent_edge_pair()).normalized()
    else:
        return (matrix.to_3x3() @ face.calc_tangent_edge()).normalized()


def align_with_view(context, tangent, binormal):
    """ 将副法线和切线根据视图向上方向调整 """
    view_up = context.space_data.region_3d.view_rotation @ Vector((0, 1, 0))
    tangent_dot = tangent.dot(view_up)
    binormal_dot = binormal.dot(view_up)

    if abs(tangent_dot) >= abs(binormal_dot):
        if binormal_dot < 0:
            binormal, tangent = tangent, -binormal
        else:
            binormal, tangent = tangent, binormal
    elif binormal_dot < 0:
        binormal, tangent = -binormal, -tangent

    return tangent, binormal


def create_rotation_matrix_from_face(context, mx, face, edge_pair=True, cylinder_threshold=0.01,
                                     align_binormal_with_view=True):
    """
    根据面创建旋转矩阵，能够识别圆形面，并可根据视图调整副法线方向。
    :param context: Blender上下文，用于访问视图参数。
    :param mx: 对象的世界矩阵。
    :param face: 面对象。
    :param edge_pair: 是否使用边对来计算切线，默认为True。
    :param cylinder_threshold: 判断圆形面的阈值，默认为0.01。
    :param align_binormal_with_view: 是否将副法线与视图向上方向对齐，默认为True。
    :return: 旋转矩阵。
    """
    # 获取面法线的世界坐标
    normal = get_world_space_normal(face.normal, mx)
    binormal = None
    face_center = face.calc_center_median()

    # 判断是否为圆形面
    if is_circle(face, face_center, cylinder_threshold):
        binormal = calculate_binormal_for_circle(face, face_center, normal, mx)

    # 如果未成功计算圆形面的副法线，使用边或边对来计算副法线
    if not binormal:
        binormal = calculate_binormal_from_edges(face, mx, edge_pair)

    # 计算切线
    tangent = binormal.cross(normal).normalized()

    # 根据视图对齐副法线和切线
    if align_binormal_with_view:
        tangent, binormal = align_with_view(context, tangent, binormal)

    # 构建旋转矩阵
    rotation_matrix = Matrix.Identity(4)
    rotation_matrix.col[0].xyz = tangent
    rotation_matrix.col[1].xyz = binormal
    rotation_matrix.col[2].xyz = normal

    return rotation_matrix
