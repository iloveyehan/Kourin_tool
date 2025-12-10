import bpy
import numpy as np

def get_obj_arrs_world(object: bpy.types.Object):
    """
    提取Blender物体的顶点、三角面索引、法向量，并转换到世界坐标系
    
    核心功能：
    1. 从Blender物体的Mesh数据中提取本地坐标系的顶点、三角面索引、顶点法向量
    2. 将顶点坐标从物体本地空间转换到世界空间（支持透视变换，处理齐次坐标）
    3. 将顶点法向量从物体本地空间转换到世界空间（法向量需用模型矩阵的逆转置变换）
    4. 输出连续内存的NumPy数组，适配后续GPU/数值计算场景
    
    参数：
        object: bpy.types.Object
            Blender场景中的物体对象（需包含Mesh数据，如网格、曲面等）
    
    返回值：
        tuple (world_vertices, indices, world_normals)
            - world_vertices: np.ndarray (N, 3), dtype=np.float32
              世界坐标系下的顶点坐标，N为顶点数量，每行对应(x, y, z)
            - indices: np.ndarray (M, 3), dtype=np.int64
              三角面索引数组，M为三角面数量，每行对应一个三角面的3个顶点索引
            - world_normals: np.ndarray (N, 3), dtype=np.float32
              世界坐标系下的顶点法向量，已归一化处理（继承Blender原生法向量）
    
    注意事项：
        1. 函数会自动计算物体的三角面（mesh.calc_loop_triangles()），无需提前处理
        2. 法向量转换使用模型矩阵的逆转置，保证法向量方向在世界空间的正确性
        3. 输出数组均为C连续内存（np.ascontiguousarray），适配OpenGL/CUDA等场景
    """
    # 获取物体的Mesh数据（本地坐标系）
    mesh: bpy.types.Mesh = object.data
    # 计算三角面（将多边形转换为三角面，确保loop_triangles数据可用）
    mesh.calc_loop_triangles()

    # 初始化数组：顶点坐标（N×3）、三角面索引（M×3）、顶点法向量（N×3）
    vertices = np.empty((len(mesh.vertices), 3), dtype=np.float32)
    indices = np.empty((len(mesh.loop_triangles), 3), dtype=np.int64)
    normals = np.empty((len(mesh.vertices), 3), dtype=np.float32)

    # 批量提取本地坐标系的顶点坐标（foreach_get效率远高于逐顶点遍历）
    mesh.vertices.foreach_get("co", vertices.reshape(-1))
    # 批量提取三角面的顶点索引（每个三角面对应3个顶点索引）
    mesh.loop_triangles.foreach_get("vertices", indices.reshape(-1))
    # 批量提取顶点法向量（优先用vertices.normal，而非vertex_normals，兼容性更好）
    # mesh.vertex_normals.foreach_get('vector', normals.reshape(-1))  # 备选：面插值后的法向量
    mesh.vertices.foreach_get('normal', normals.reshape(-1))
    
    # 获取物体的世界变换矩阵（4×4齐次矩阵）
    world_matrix = np.array(object.matrix_world)
    # 构造齐次坐标的w分量（全1），用于4×4矩阵变换
    ones = np.ones((vertices.shape[0], 1))
    
    # 将顶点转换为4D齐次坐标（N×4）：(x,y,z) → (x,y,z,1)
    vertices_4d = np.hstack((vertices, ones))
    # 应用世界矩阵变换：M @ V^T → 结果转置回N×4（保证矩阵乘法维度匹配）
    world_vertices_4d = (world_matrix @ vertices_4d.T).T
    # 转换为C连续内存数组，提升后续计算效率
    world_vertices_4d = np.ascontiguousarray(world_vertices_4d, dtype=np.float32)
    # 齐次坐标转回3D坐标：(x/w, y/w, z/w)（处理透视变换，若矩阵含透视分量）
    world_vertices = world_vertices_4d[:,:3] / world_vertices_4d[:, 3][:, np.newaxis]
    
    # 法向量世界空间转换：使用模型矩阵前3×3的逆转置（保证法向量垂直性）
    # 原理：法向量变换需抵消缩放/旋转的影响，逆转置是标准做法
    world_normals = (np.linalg.inv(world_matrix[:3, :3]).T @ normals.T).T
    # 转换为C连续内存数组
    world_normals = np.ascontiguousarray(world_normals, dtype=np.float32)
    
    # 返回世界坐标系下的顶点、索引、法向量
    return world_vertices, indices, world_normals