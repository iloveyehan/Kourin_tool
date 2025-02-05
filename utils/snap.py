import bmesh
import bpy
from bpy_extras.view3d_utils import region_2d_to_origin_3d, region_2d_to_vector_3d
from mathutils import Vector
class SnapCache:
    def log(self, *args, **kwargs):
        if self.debug:
            print(*args, **kwargs)

    debug = False

    objects = {}
    meshes = {}

    bmeshes = {}

    loop_triangles = {}
    tri_coords = {}

    def __init__(self, debug=False):
        self.debug = debug
        self.log(" Initialize SnappingCache")

    def clear(self):
        for name, mesh in self.meshes.items():
            self.log(f" Removing {name}'s temporary snapping mesh {mesh.name} with {len(mesh.polygons)} faces and {len(mesh.vertices)} verts")
            bpy.data.meshes.remove(mesh, do_unlink=True)

        for name, bm in self.bmeshes.items():
            self.log(f" Freeing {name}'s temporary snapping bmesh")
            bm.free()

        self.objects.clear()
        self.meshes.clear()

        self.bmeshes.clear()

        self.loop_triangles.clear()
        self.tri_coords.clear()
class Snap:
    def __init__(self, context, include=None, exclude=None, exclude_wire=False, temp_replacement=None, debug=False):
        """
        初始化 Snap 类实例，用于在 Blender 场景中进行射线投射并处理吸附逻辑。

        :param context: Blender 上下文对象。
        :param include: 包含的对象列表。
        :param exclude: 排除的对象列表。
        :param exclude_wire: 是否排除线框对象。
        :param temp_replacement: 替代对象列表。
        :param debug: 是否启用调试信息。
        """
        self.debug = debug
        self._init_edit_mode(context)
        self.deps_graph = context.evaluated_depsgraph_get()
        self._init_exclude(context, include, exclude, exclude_wire)
        self._init_temp_replacements(context, temp_replacement)
        self.cache = SnapCache(debug=debug)
        self.hit_face = None
    def log(self, *args):
        """在调试模式下打印日志信息。"""
        if self.debug:
            print(*args)

    def finish(self):
        """结束吸附操作，清理替代对象和缓存。"""
        self._remove_temp_replacements()
        self.cache.clear()
        if self._modifiers:
            self._enable_modifiers()
        self.log("Snapping finished.")

    def get_hit(self, mousepos):
        def generate_tri_coords(loop_triangles, hitface):
            return [self.hitmx @ l.vert.co for tri in loop_triangles if tri[0].face == hitface for l in tri]

        def cache_hit_object(self, name, hitobj):
            if name not in self.cache.objects:
                # 添加对象到缓存
                self.cache.objects[name] = hitobj

                # 创建网格并添加到缓存
                evaluated_obj = hitobj.evaluated_get(self.deps_graph)
                mesh = bpy.data.meshes.new_from_object(evaluated_obj, depsgraph=self.deps_graph)
                self.cache.meshes[name] = mesh

                # 创建 bmesh 并添加到缓存
                bm = bmesh.new()
                bm.from_mesh(mesh)
                bm.verts.ensure_lookup_table()
                bm.faces.ensure_lookup_table()
                self.cache.bmeshes[name] = bm

                # 计算三角形并添加到缓存
                self.cache.loop_triangles[name] = bm.calc_loop_triangles()
                self.cache.tri_coords[name] = {}

        # 投射射线
        self.hit, self.hitobj, self.hitindex, self.hitlocation, self.hitnormal, self.hitmx = cast_scene_ray_from_mouse(
            mousepos, self.deps_graph, exclude=self.exclude, exclude_wire=self.exclude_wire, unhide=self.temp_replacements,
            debug=self.debug
        )

        if not self.hit:
            return

        name = self.hitobj.name
        cache_hit_object(self, name, self.hitobj)

        if not self.hit_face or (self.hit_face and self.hit_face.index != self.hitindex):
            self.log("Hitface changed to", self.hitindex)
            self.hit_face = self.cache.bmeshes[name].faces[self.hitindex]

        if self.hitindex not in self.cache.tri_coords[name]:
            self.log("Adding tri coords for face index", self.hitindex)
            loop_triangles = self.cache.loop_triangles[name]
            tri_coords = generate_tri_coords(loop_triangles, self.hit_face)
            self.cache.tri_coords[name][self.hitindex] = tri_coords


    # def cache_hit(self, hit_obj, hit_index, hit_matrix):
    #     """
    #     缓存击中的对象和相关信息以优化性能。
    #
    #     :param hit_obj: 击中的对象。
    #     :param hit_index: 击中的面索引。
    #     :param hit_matrix: 击中的对象的变换矩阵。
    #     """
    #     obj_name = hit_obj.name
    #     if obj_name not in self.cache:
    #         self.cache[obj_name] = {
    #             'object': hit_obj,
    #             'mesh': bpy.data.meshes.new_from_object(hit_obj.evaluated_get(self.deps_graph), deps_graph=self.deps_graph),
    #             'bmesh': bmesh.new()
    #         }
    #         self.cache[obj_name]['bmesh'].from_mesh(self.cache[obj_name]['mesh'])
    #     if hit_index not in self.cache[obj_name]:
    #         self.cache[obj_name][hit_index] = [hit_matrix @ v.co for v in self.cache[obj_name]['bmesh'].faces[hit_index].verts]
    #     self.log(f"Cached hit on {hit_obj.name} at face {hit_index}")

    def _init_exclude(self, context, include, exclude, exclude_wire):
        if include:
            self.exclude = [obj for obj in context.visible_objects if obj not in include]

        elif exclude:
            self.exclude = exclude

        else:
            self.exclude = []

        view = context.space_data

        if view.local_view:
            hidden = [obj for obj in context.view_layer.objects if not obj.visible_get()]
            self.exclude += hidden

        self.exclude_wire = exclude_wire

    def _init_temp_replacements(self, context, temp_replacement):
        """
        初始化替代对象。创建副本并隐藏以供吸附。"""
        self.temp_replacements = []
        if temp_replacement:
            for obj in temp_replacement:
                if obj not in self.exclude:
                    self.exclude.append(obj)
                dup = obj.copy()
                dup.data = obj.data.copy()
                context.scene.collection.objects.link(dup)
                dup.hide_set(True)
                self.temp_replacements.append(dup)
                self.log(f"Created temp_replacement object {dup.name} for {obj.name}")


    def _remove_temp_replacements(self):
        """
        删除替代对象，释放内存。"""
        for obj in self.temp_replacements:
            self.log(f"Removing temp_replacement object {obj.name}")
            bpy.data.meshes.remove(obj.data, do_unlink=True)
    def _init_edit_mode(self, context):
        if context.mode == 'EDIT_MESH':
            self._update_meshes(context)
            self._disable_modifiers()
    def _update_meshes(self, context):
        # 过滤可见对象中的编辑模式网格对象
        self._edit_mesh_objs = [obj for obj in context.visible_objects if obj.mode == 'EDIT']

        # 更新所有编辑模式下的对象
        for obj in self._edit_mesh_objs:
            obj.update_from_editmode()

    def _disable_modifiers(self):
        # 获取所有编辑模式对象中可见的修改器
        self._modifiers = [
            (obj, mod) for obj in self._edit_mesh_objs for mod in obj.modifiers if mod.show_viewport
        ]

        # 禁用可见的修改器
        for obj, mod in self._modifiers:
            self.log(f"Disabling {obj.name}'s {mod.name}")
            mod.show_viewport = False

    def _enable_modifiers(self):
        # 重新启用之前禁用的修改器
        for obj, mod in self._modifiers:
            self.log(f"Re-enabling {obj.name}'s {mod.name}")
            mod.show_viewport = True
def cast_scene_ray_from_mouse(mousepos, depsgraph, exclude=None, exclude_wire=False, unhide=None, debug=False):
    import bpy
    from bpy_extras.view3d_utils import region_2d_to_origin_3d, region_2d_to_vector_3d

    if exclude is None:
        exclude = []
    if unhide is None:
        unhide = []

    region = bpy.context.region
    region_data = bpy.context.region_data

    # 获取视图的起始点和方向
    view_origin = region_2d_to_origin_3d(region, region_data, mousepos)
    view_dir = region_2d_to_vector_3d(region, region_data, mousepos)

    scene = bpy.context.scene

    # 显示指定的对象
    for ob in unhide:
        ob.hide_set(False)

    # 执行射线投射
    hit, location, normal, index, obj, mx = scene.ray_cast(depsgraph=depsgraph, origin=view_origin, direction=view_dir)
    hidden = []

    # 如果命中的对象需要忽略，则继续射线投射
    while hit and (obj in exclude or (exclude_wire and obj.display_type == 'WIRE')):
        if debug:
            print("忽略对象", obj.name)
        obj.hide_set(True)
        hidden.append(obj)
        hit, location, normal, index, obj, mx = scene.ray_cast(depsgraph=depsgraph, origin=view_origin, direction=view_dir)

    # 恢复之前隐藏的对象的可见性
    for ob in unhide:
        ob.hide_set(True)
    for ob in hidden:
        ob.hide_set(False)

    # 调试输出
    if debug:
        if hit:
            print(obj.name, index, location, normal)
        else:
            print(None)

    # 返回结果
    return (hit, obj, index, location, normal, mx) if hit else (None, None, None, None, None, None)