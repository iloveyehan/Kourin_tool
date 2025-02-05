import bpy
def popup_message(message, title="Info", icon="INFO", terminal=True):
    def draw_message(self, context):
        if isinstance(message, list):
            for m in message:
                self.layout.label(text=m)
        else:
            self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw_message, title=title, icon=icon)

    if terminal:
        if icon == "FILE_TICK":
            icon = "ENABLE"
        elif icon == "CANCEL":
            icon = "DISABLE"
        print(icon, title)

        if isinstance(message, list):
            print(" »", ", ".join(message))
        else:
            print(" »", message)


import bmesh
from mathutils.geometry import intersect_line_line, intersect_line_plane, intersect_point_line


def slide_snap(self, context):
    # 第一步：获取击中矩阵和坐标
    hit_matrix = self.S.hitmx
    hit_coords = hit_matrix.inverted_safe() @ self.S.hitlocation

    # 第二步：获取击中的面和三角形坐标
    hit_face = self.S.hitface
    triangle_coords = self.S.cache.tri_coords[self.S.hitobj.name][self.S.hitindex]

    # 定义面和边的权重
    FACE_WEIGHT = 25
    EDGE_WEIGHT = 1

    # 计算到面的距离（加权）
    face_center = hit_face.calc_center_median_weighted()
    face_distance = (hit_face, (hit_coords - face_center).length / FACE_WEIGHT)

    # 找到最近的边并计算其距离（加权）
    closest_edge = min(
        [
            (
                edge,
                (hit_coords - intersect_point_line(hit_coords, edge.verts[0].co, edge.verts[1].co)[0]).length,
                (hit_coords - ((edge.verts[0].co + edge.verts[1].co) / 2)).length
            )
            for edge in hit_face.edges if edge.calc_length() > 0
        ],
        key=lambda x: (x[1] * x[2]) / x[0].calc_length()
    )
    edge_distance = (
    closest_edge[0], ((closest_edge[1] * closest_edge[2]) / closest_edge[0].calc_length()) / EDGE_WEIGHT)

    # 选择最近的元素（面或边）
    closest_element = min([face_distance, edge_distance], key=lambda x: x[1])

    # 初始化捕捉坐标
    self.snap_coords = []
    self.snap_tri_coords = []
    self.snap_proximity_coords = []
    self.snap_ortho_coords = []

    # 处理捕捉逻辑
    if isinstance(closest_element[0], bmesh.types.BMEdge):
        # 捕捉到边
        self.snap_element = 'EDGE'

        # 获取捕捉的边的坐标
        self.snap_coords = [hit_matrix @ v.co for v in closest_element[0].verts]
        snap_coords_local = [self.mx.inverted_safe() @ co for co in self.snap_coords]

        for v, data in self.verts.items():
            init_co = data['co']
            target = data['target']

            snap_dir = (snap_coords_local[0] - snap_coords_local[1]).normalized()
            slide_dir = (init_co - target.co).normalized()

            if abs(slide_dir.dot(snap_dir)) > 0.999:
                v.co = init_co
            else:
                intersection = intersect_line_line(init_co, target.co, *snap_coords_local)
                if intersection:
                    v.co = intersection[1 if self.is_diverging else 0]
                else:
                    v.co = init_co

                if v.co != target.co:
                    self.coords.extend([v.co, target.co])

                if intersection and intersection[1] != snap_coords_local[0]:
                    self.snap_proximity_coords.extend([intersection[1], snap_coords_local[0]])

                if v.co != intersection[1]:
                    self.snap_ortho_coords.extend([v.co, intersection[1]])

    elif isinstance(closest_element[0], bmesh.types.BMFace):
        # 捕捉到面
        self.snap_element = 'FACE'

        found_intersection = False
        face_center_world = self.mx.inverted_safe() @ hit_matrix @ get_face_center(closest_element[0])
        face_normal_world = self.mx.inverted_safe().to_3x3() @ hit_matrix.to_3x3() @ closest_element[0].normal

        for v, data in self.verts.items():
            init_co = data['co']
            target = data['target']

            intersection = intersect_line_plane(init_co, target.co, face_center_world, face_normal_world)
            if intersection:
                found_intersection = True
                v.co = intersection
                self.snap_ortho_coords.extend([intersection, face_center_world])

        if found_intersection:
            self.snap_tri_coords = triangle_coords

    # 处理平面化逻辑
    if self.can_flatten:
        if self.flatten:
            self.flatten_verts()
        else:
            for v, vdict in self.flatten_dict['other_verts'].items():
                v.co = vdict['co']

    # 更新法线
    self.bm.normal_update()

    # 更新网格数据
    if context.mode == 'EDIT_MESH':
        bmesh.update_edit_mesh(self.active.data)
    else:
        self.bm.to_mesh(self.active.data)