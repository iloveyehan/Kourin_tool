import math

import bpy
import bmesh
import mathutils
# 函数：VectorAve
# 计算向量数组的平均值
# 参数：
#   $vectorList - 向量数组
# 返回值：
#   返回向量数组的平均值
def vector_max_min_avg(vertex_list):
    # Initialize values with the first vertex
    first_vert = vertex_list[0]
    max_x, max_y, max_z = first_vert.co.x, first_vert.co.y, first_vert.co.z
    min_x, min_y, min_z = first_vert.co.x, first_vert.co.y, first_vert.co.z

    # Iterate through the vertex list
    for vert in vertex_list:
        max_x = max(max_x, vert.co.x)
        max_y = max(max_y, vert.co.y)
        max_z = max(max_z, vert.co.z)
        min_x = min(min_x, vert.co.x)
        min_y = min(min_y, vert.co.y)
        min_z = min(min_z, vert.co.z)

    # Calculate the average vector
    avg_vec = mathutils.Vector((
        (min_x + max_x) / 2.0,
        (min_y + max_y) / 2.0,
        (min_z + max_z) / 2.0
    ))
    return avg_vec

# # Example usage in Blender
# import bpy
#
# # Get the active object's mesh data
# obj = bpy.context.active_object
# if obj and obj.type == 'MESH':
#     mesh = obj.data
#     vertex_list = mesh.vertices  # Get all vertices
#     average_vector = vector_max_min_avg(vertex_list)
#     print("Average Vector:", average_vector)
# else:
#     print("Please select a mesh object.")

# 如果需要更新网格
# bmesh.update_edit_mesh(mesh)
def vector_max_min_ave(vec_list):
    if len(vec_list)==0:
        return Vector((0,0,0))
    xs = [v.x for v in vec_list]
    ys = [v.y for v in vec_list]
    zs = [v.z for v in vec_list]
    maxX, minX = max(xs), min(xs)
    maxY, minY = max(ys), min(ys)
    maxZ, minZ = max(zs), min(zs)
    return Vector(((minX+maxX)*0.5, (minY+maxY)*0.5, (minZ+maxZ)*0.5))

from mathutils import Vector, Quaternion
def get_selected_chain(bm):
    '''返回排序好的顶点列表顶点列表'''
    # 1. 确保处于编辑模式
    if bpy.context.object.mode != 'EDIT':
        bpy.ops.object.mode_set(mode='EDIT')

    # 2. 获取网格和 bmesh 对象
    # mesh = bpy.context.object.data

    # 3. 获取选中的边
    selected_edges = [edge for edge in bm.edges if edge.select]

    # 4. 构建顶点的邻接关系（只考虑选中的边）
    vertex_dict = {}
    for edge in selected_edges:
        v1, v2 = edge.verts
        for v, neighbor in ((v1, v2), (v2, v1)):
            if v not in vertex_dict:
                vertex_dict[v] = set()
            vertex_dict[v].add(neighbor)

    # 5. 标记所有顶点为未访问
    visited_vertices = set()

    # 6. 初始化边链列表
    edge_chains = []

    # 7. 遍历所有顶点，找到所有连接组件
    for vertex in vertex_dict.keys():
        if vertex not in visited_vertices:
            # 开始新的边链
            chain_vertices = []
            chain_vertices_set = set()
            stack = [vertex]

            while stack:
                current_vertex = stack.pop()
                if current_vertex in visited_vertices:
                    continue
                visited_vertices.add(current_vertex)
                chain_vertices.append(current_vertex)
                chain_vertices_set.add(current_vertex)
                # 将未访问的相邻顶点加入栈
                neighbors = vertex_dict[current_vertex]
                for neighbor in neighbors:
                    if neighbor not in visited_vertices:
                        stack.append(neighbor)

            # 识别当前边链的端点
            chain_vertex_dict = {v: vertex_dict[v] for v in chain_vertices}
            endpoints = [v for v in chain_vertices if len(chain_vertex_dict[v]) == 1]

            # 如果有端点，从端点开始排序
            if endpoints:
                start_vertex = endpoints[0]
            else:
                # 如果没有端点（闭合环），从任意顶点开始
                start_vertex = chain_vertices[0]

            # 8. 按照连接顺序遍历当前边链，收集顶点
            ordered_vertices = []
            ordered_visited = set()
            current_vertex = start_vertex
            previous_vertex = None

            while True:
                ordered_vertices.append(current_vertex)
                ordered_visited.add(current_vertex)

                neighbors = vertex_dict[current_vertex]
                unvisited_neighbors = [v for v in neighbors if v not in ordered_visited]

                if unvisited_neighbors:
                    # 在相邻顶点中排除前一个顶点，防止往回走
                    if previous_vertex and previous_vertex in unvisited_neighbors:
                        unvisited_neighbors.remove(previous_vertex)
                    if unvisited_neighbors:
                        previous_vertex = current_vertex
                        current_vertex = unvisited_neighbors[0]
                    else:
                        break
                else:
                    break

            # 将当前边链的有序顶点列表添加到边链列表中
            edge_chains.append(ordered_vertices)
    print(edge_chains)
    return edge_chains
