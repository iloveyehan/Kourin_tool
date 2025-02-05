import queue
from collections import deque

import bmesh
import bpy
# from ..utils.vert import get_selected_vert_order
obj=bpy.context.active_object
bm=bmesh.from_edit_mesh(obj.data)
bm.edges.ensure_lookup_table()

# for edge in bm.edges:
#     if edge.select:
#         if edge.select:
#             bound.append(edge)

bpy.ops.mesh.loop_to_region()
bm.faces.ensure_lookup_table()
bound=[]
selected_faces= {}
for f in bm.faces:
    if f.select:
        selected_faces[f]=len(f.verts)
        for edge in f.edges:
            for ef in edge.link_faces:
                if not ef.select:
                    bound.append(edge)
bound=set(bound)
# print('selected_faces',selected_faces)
#获取边界面
f_bound = deque()
e_delete=[]
for e in bound:
    for f in e.link_faces:
        if f in selected_faces:
            f_bound.append(f)
while len(f_bound)>0:
    face_bound=f_bound.popleft()
    if len(face_bound.verts)==3:
        count=0
        diagonal=0
        #遍历边界面的边 如果有两条边都在边界边里 那么就是拐角面
        for e in face_bound.edges:
            if e in bound:
                count+=1
            else:
                diagonal=e
        for face2 in diagonal.link_faces:
            if face2!=face_bound and len(face2.verts)==3:
                #找到了矩形的另一个三角面
                print(face2.index)
                for edge in face2.edges:
                    if edge!=diagonal:
                        for f in edge.link_faces:
                            if f!=face2 and f not in f_bound and f in selected_faces:
                                #添加新的边界面
                                f_bound.appendleft(f)
                # del selected_faces[face_bound]
                # del selected_faces[face2]
        #拐角面 标记斜边
        if count>1:
            e_delete.append(diagonal)
        else:
            #如果只有一条边在边界上
            #计算顶点到边上两点的距离 小的就比较方正
            for e in face_bound.edges:
                if e in bound:
                    continue
                distance=float('inf')
                for face2 in e.link_faces:
                    if face2!=face_bound and len(face2.verts)==3:

            f_bound.append(face_bound)
# for i in e_delete:
#     print(i.index)
bmesh.ops.dissolve_edges(bm, edges=list(set(e_delete)))
bmesh.update_edit_mesh(obj.data)