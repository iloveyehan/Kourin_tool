# bl_info = {
#     "name": "Robust Weight Transfer",
#     "author": "sentfromspacevr",
#     "version": (1, 1, 5),
#     "blender": (2, 93, 0),
#     "doc_url": "https://jinxxy.com/SentFromSpaceVR/robust-weight-transfer",
#     "location": "View3D > Sidebar > SENT Tab",
#     "category": "Object",
# }

import sys
import os

libs_path = os.path.join(os.path.dirname(__file__), 'deps')
if libs_path not in sys.path:
    sys.path.append(libs_path)

import bpy
import bmesh
import numpy as np
import webbrowser
import math
import importlib
import subprocess
from ...ui.qt_global import GlobalProperty as G_pro

import bpy.utils.previews


DEPENDENCIES = ["robust_laplacian", "igl", "scipy"]
missing_deps = []
for module in DEPENDENCIES:
    try:
        importlib.import_module(module)
    except ImportError:
        if module == "igl":
            missing_deps.append("libigl==2.5.1")
        else:
            missing_deps.append(module)

installed_deps = False

if not missing_deps:
    import igl
    from .weighttransfer import find_matches_closest_surface, inpaint, limit_mask, smooth_weigths
    from . import util


class KourinRobustWeightTransfer(bpy.types.Operator):
    """Transfer Skin Weights Robust"""
    bl_idname = "kourin.skin_weight_transfer"
    bl_label = "Robust Weight Transfer"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        if context.mode != 'OBJECT' and context.mode != 'PAINT_WEIGHT': return False
        
        scene_settings: KourinSceneSettingsGroup = context.scene.kourin_weight_transfer_settings
        if not scene_settings.source_object: return False
        if not scene_settings.apply_to_selected and scene_settings.source_object == context.active_object: return False
        if scene_settings.group_selection == 'DEFORM_POSE_BONES':
            armature_mods = [mod for mod in scene_settings.source_object.modifiers if mod.type == "ARMATURE"]
            if len(armature_mods) != 1: return False # no armature modifier or more than one
            if not armature_mods[0].object: return False

            
        objs = lambda x: [obj for obj in x if obj != scene_settings.source_object and isinstance(obj.data, bpy.types.Mesh)]
        if scene_settings.apply_to_selected:
            target_objs = objs(context.selected_objects)
        else:
            if not context.object: return False
            target_objs = objs([context.object])
            
        if len(target_objs) == 0: return False
        if scene_settings.use_deformed_target and any(util.has_modifier(obj, *util.TOPOLOGY_MODS) for obj in target_objs): return False
        
        if not scene_settings.apply_to_selected:
            obj = target_objs[0]
            object_settings: KourinObjectSettingsGroup = obj.kourin_weight_transfer_settings
            mask = object_settings.vertex_group
            if len(mask) > 0 and mask not in obj.vertex_groups: return False
            inpaint = object_settings.inpaint_group
            if len(inpaint) > 0 and  inpaint not in obj.vertex_groups: return False
        return True


    def execute(self, context: bpy.types.Context):
        scene_settings: KourinSceneSettingsGroup = context.scene.kourin_weight_transfer_settings
        
        source_obj: bpy.types.Object = scene_settings.source_object
        if source_obj.type != 'MESH':
            self.report({'ERROR'}, f'Source object {source_obj.name} is not a mesh')
            return {'CANCELLED'}
    
        if scene_settings.apply_to_selected:
            target_objs = [obj for obj in context.selected_objects if obj != source_obj and isinstance(obj.data, bpy.types.Mesh)]
        else:
            target_objs = [context.object]
        
        depsgraph = context.evaluated_depsgraph_get()
        if scene_settings.use_deformed_source:
            source_obj = source_obj.evaluated_get(depsgraph)
        
        weights_all = [] # (num_objs, (num_vertices, num_weights))
        source_verts, source_triangles, source_normals = util.get_obj_arrs_world(source_obj)
        deform_only = scene_settings.group_selection == 'DEFORM_POSE_BONES'
        is_deform = [util.is_vertex_group_deform_bone(source_obj, g.name) for g in source_obj.vertex_groups]
        source_weights = util.get_groups_arr(source_obj, is_deform if deform_only else None) # (num_verts, )
        for obj in target_objs:
            object_settings: KourinObjectSettingsGroup = obj.kourin_weight_transfer_settings
            verts, triangles, normals = util.get_obj_arrs_world(obj.evaluated_get(depsgraph) if scene_settings.use_deformed_target else obj)
            matched_verts, weights = find_matches_closest_surface(source_verts, source_triangles, source_normals, verts, normals, source_weights, scene_settings.max_distance**2, math.degrees(scene_settings.max_normal_angle_difference), scene_settings.flip_vertex_normal)
            if not scene_settings.apply_to_selected:
                if util.is_group_valid(obj.vertex_groups, object_settings.inpaint_group):
                    inpaint_mask = util.get_group_arr(obj, object_settings.inpaint_group)
                    inpaint_mask_bin = inpaint_mask > object_settings.inpaint_threshold
                    if object_settings.inpaint_group_invert:
                        inpaint_mask_bin = ~inpaint_mask_bin
                    matched_verts = np.logical_and(matched_verts, ~inpaint_mask_bin)
            
            
            if scene_settings.draw_matched:
                res = util.draw_debug_vertex_colors(obj, matched_verts)
                if not res:
                    self.report({'ERROR'}, f'{obj.name} has too many vertex colors. Delete one or deactive Visualize Rejected Weights.')
                    return {'CANCELLED'}

                
            result, weights = inpaint(verts, triangles, weights, matched_verts, scene_settings.inpaint_mode == 'POINT')
            if not result:
                self.report({'ERROR'}, f'Failed weight inpainting on {obj.name}: This usually happens on loose parts, where vertices are not finding a match on the source mesh. Use Select Rejected Loose Parts to solve the issue.')
                return {'CANCELLED'}
            
            adj_mat = util.get_mesh_adjacency_matrix_sparse(obj.data, include_self=True)
            if scene_settings.smoothing_enable:
                adj_list = util.get_mesh_adjacency_list(obj.data)
                weights = smooth_weigths(verts, weights, matched_verts, adj_mat, adj_list, scene_settings.smoothing_repeat, scene_settings.smoothing_factor, scene_settings.max_distance)
            
            if scene_settings.enforce_four_bone_limit:
                weights[weights <= 0.0001] = 0
                mask = limit_mask(weights, adj_mat, limit_num=scene_settings.num_limit_groups)
                weights = (1 - mask) * weights
                weights[weights <= 0.0001] = 0
            
            weights_all.append(weights)
        for obj, weights in zip(target_objs, weights_all):
            source_vertex_groups = source_obj.vertex_groups
            weight_counts = np.count_nonzero(weights, axis=0)
            for group, w_count in zip(source_vertex_groups, weight_counts):
                if w_count > 0:
                    if group.name not in obj.vertex_groups:
                        obj.vertex_groups.new(name=group.name)
            
            is_deform = [util.is_vertex_group_deform_bone(source_obj, g.name) for g in source_vertex_groups]
            
            use_mask = not scene_settings.apply_to_selected and util.is_group_valid(obj.vertex_groups, object_settings.vertex_group)
            if use_mask:
                mask = util.get_group_arr(obj, object_settings.vertex_group)
                if object_settings.vertex_group_invert:
                    mask = 1 - mask
                current_weights = {group.name: w  for group, w in zip(obj.vertex_groups, util.get_groups_arr(obj).T)}
                
            for i, w in enumerate(weights.T):
                w_count = weight_counts[i]
                if w_count == 0: continue
                
                source_group = source_vertex_groups[i]
                target_group = obj.vertex_groups[source_group.name]
                
                if target_group.lock_weight:
                    continue
                if deform_only and not is_deform[i]:
                    continue
                
                if use_mask:
                    group_name = source_obj.vertex_groups[i].name
                    current_weight = current_weights[group_name]
                    w = (1 - mask) * current_weight + mask * w
                    
                for j, wv in enumerate(w):
                    if wv >= 0.00001:
                        target_group.add([j], wv, 'REPLACE')
                ind = np.where(w < 0.00001)[0].tolist()
                target_group.remove(ind)   
        
        if scene_settings.draw_matched:
            if isinstance(context.space_data, bpy.types.SpaceView3D):
                view: bpy.types.SpaceView3D = context.space_data
                view.shading.type = 'SOLID'
                view.shading.color_type = 'VERTEX'
        if scene_settings.apply_to_selected:
            self.report({'INFO'}, f'Weights transfered from {source_obj.name} to selected objects')
        else:
            self.report({'INFO'}, f'Weights transfered from {source_obj.name} to {context.object.name}')
        return {'FINISHED'}
    

class KourinSelectNonMatched(bpy.types.Operator):
    """Select Rejected Loose Parts"""
    bl_idname = "object.select_non_matched"
    bl_label = "Select Rejected Loose Parts"
    bl_description = "Select vertices in Edit Mode, that make Weight Inpainting fail"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        scene_settings: KourinSceneSettingsGroup = context.scene.kourin_weight_transfer_settings
        if context.mode != 'EDIT_MESH': return False
        if not context.active_object: return False
        if not scene_settings.source_object: return False
        if scene_settings.source_object == context.active_object: return False
        if scene_settings.use_deformed_target and util.has_modifier(context.active_object, *util.TOPOLOGY_MODS): return False
        return True

    def execute(self, context):
        bpy.ops.object.mode_set(mode='OBJECT')     
        scene_settings: KourinSceneSettingsGroup = context.scene.kourin_weight_transfer_settings
        source_obj: bpy.types.Object = scene_settings.source_object
        
        depsgraph = context.evaluated_depsgraph_get()
        if scene_settings.use_deformed_source:
            source_obj = source_obj.evaluated_get(depsgraph)
        
        source_verts, source_triangles, source_normals = util.get_obj_arrs_world(source_obj)
        
        deform_only = scene_settings.group_selection == 'DEFORM_POSE_BONES'
        is_deform = [util.is_vertex_group_deform_bone(source_obj, g.name) for g in source_obj.vertex_groups]
        source_weights = util.get_groups_arr(source_obj, is_deform if deform_only else None)
        
        obj = context.active_object
        verts, triangles, normals = util.get_obj_arrs_world(obj.evaluated_get(depsgraph) if scene_settings.use_deformed_target else obj)
        matched_verts, weights = find_matches_closest_surface(source_verts, source_triangles, source_normals, verts, normals, source_weights, scene_settings.max_distance**2, math.degrees(scene_settings.max_normal_angle_difference), scene_settings.flip_vertex_normal)
        
        if not scene_settings.apply_to_selected:
            object_settings: KourinObjectSettingsGroup = obj.kourin_weight_transfer_settings
            has_inpaint = len(object_settings.inpaint_group) > 0 and object_settings.inpaint_group in obj.vertex_groups
            if has_inpaint:
                inpaint_mask = util.get_group_arr(obj, object_settings.inpaint_group)
                inpaint_mask_bin = inpaint_mask > object_settings.inpaint_threshold
                if object_settings.inpaint_group_invert:
                    inpaint_mask_bin = ~inpaint_mask_bin
                matched_verts = np.logical_and(matched_verts, ~inpaint_mask_bin)
        
        # get loose part meshes
        num_conn, conn, num_vertices = igl.connected_components(igl.adjacency_matrix(triangles))
        conns = [np.where(conn == i)[0] for i in range(num_conn)]
        matched_per_submesh = [np.count_nonzero(matched_verts[c]) for c in conns]
        zero_matched_submeshes = [i for i, m in enumerate(matched_per_submesh) if m == 0]
        
        selects = np.zeros(verts.shape[0], dtype=bool)
        for i in zero_matched_submeshes:
            selects[conns[i]] = True
        
        bpy.ops.object.mode_set(mode='EDIT')
        mesh = bmesh.from_edit_mesh(obj.data)
        mesh.verts.ensure_lookup_table()
        for i, x in enumerate(selects):
            mesh.verts[i].select_set(x)
        mesh.select_flush(True)
        mesh.select_flush(False)
        bmesh.update_edit_mesh(obj.data, destructive=False)
        self.report({'INFO'}, f'Selected {np.count_nonzero(selects)} out of {selects.shape[0]} vertices.')

        return {'FINISHED'}
        

class KourinObjectSettingsGroup(bpy.types.PropertyGroup):
    vertex_group: bpy.props.StringProperty(name='Mask Vertex Group')
    vertex_group_invert: bpy.props.BoolProperty(name='Invert')
    inpaint_group: bpy.props.StringProperty(name='Inpaint Vertex Group')
    inpaint_group_invert: bpy.props.BoolProperty(name='Invert Inpaint')
    inpaint_threshold: bpy.props.FloatProperty(name='Inpaint Binary Threshold', default=0.5, min=0, max=1)
    
def update_enforce_four_bone_limit(self, context):
    """Ensure the correct group selection and enforce constraints."""
    if self.enforce_four_bone_limit:
        self.group_selection = 'DEFORM_POSE_BONES'
    
class KourinSceneSettingsGroup(bpy.types.PropertyGroup):
    source_object: bpy.props.PointerProperty(name='Source', type=bpy.types.Object, poll=lambda self, obj: obj.type == 'MESH')
    shape_key_mix: bpy.props.BoolProperty(name='Use Shape Key Mix', description='Uses the Shape of the Shape Key Mix to transfer the weights', default=True)
    max_distance: bpy.props.FloatProperty(
        name='Max Distance',
        description='Maximum allowed distance between source and destination vertex',
        default=0.05,
        min=0,
        unit='LENGTH',
        subtype='DISTANCE')
    max_normal_angle_difference: bpy.props.FloatProperty(
        name='Max Normal Difference',
        description='Maximum allowed vertex normal difference between source and destination vertex',
        default=math.radians(30),
        min=0,
        max=math.pi,
        precision=3,
        step=100,
        unit='ROTATION',
        subtype='ANGLE')
    flip_vertex_normal: bpy.props.BoolProperty(
        name='Flip Vertex Normal',
        description='Allow vertex normal flipped at 180° between source and destination vertex',
        default=True)
    smoothing_factor: bpy.props.FloatProperty(
        name='Smoothing factor',
        description='Smoothing factor used in the smoothing pass.',
        default=0.2,
        min=0,
        max=1,
        step=10)
    smoothing_repeat: bpy.props.IntProperty(
        name='Smoothing repeat',
        description='Amount of iterations of smoothing used in the smoothing pass',
        default=4,
        min=0)
    apply_to_selected: bpy.props.BoolProperty(
        name='Apply to all Selected Objects',
        description='Weight transfers the from the source object to all selected objects')
    use_modifier: bpy.props.BoolProperty(name='Use Modifier', description='Uses the Shape resulting from the source objects modifier stack', default=True)
    use_deformed_source: bpy.props.BoolProperty(name='Use Deformed Source', description='Uses the Shape resulting from the source object\'s modifier stack and shape keys', default=True)
    use_deformed_target: bpy.props.BoolProperty(name='Use Deformed Target', description='Uses the Shape resulting from the target object\'s modifier stack and shape keys', default=True)
    draw_matched: bpy.props.BoolProperty(
        name='Visualize Rejected Weights',
        description='Draws rejected weights as a pink to the vertex color layer "RBT Matched". After each transfer it will set the vertex color layer to active and change the Viewport Shading to Solid, with Color set to Attribute')
    enforce_four_bone_limit: bpy.props.BoolProperty(
        name='Limit Groups per Vertex',
        description='Limit a vertex to being influenced to a specific amount of groups. This is useful when a mesh will be exported to game engines like Unity, that normally only support 4 bones per vertex',
        default=True,
        update=update_enforce_four_bone_limit)
    group_selection: bpy.props.EnumProperty(
        name='Group Type',
        description='Select what subset of Vertex Group\'s should be transferred',
        items=[
            ('ALL_GROUPS', 'All Groups', 'Transfer all groups'),
            ('DEFORM_POSE_BONES', 'Deform Pose Bones', 'Only transfer deform pose bones, used by the Armature')
        ],
        default='DEFORM_POSE_BONES')
    dilation_repeat: bpy.props.IntProperty(
        name='Dilation repeat',
        description='Amount of iterations used to smooth the weight remove mask, that is used to limit the bone influence per vertex to 4',
        default=4,
        min=0)
    inpaint_mode: bpy.props.EnumProperty(
        name='Mode',
        description='Choose the Inpaint Mode',
        items=[
            ('POINT', 'Point', 'Object is remeshed internally. Weights can "flow" outside a mesh/loose part and more robust' ),
            ('SURFACE', 'Surface', 'Mesh is used as is. Weights "flow" only inside a mesh/loose part. More likely to fail compared to "Point"')
        ],
        default='POINT')
    smoothing_enable: bpy.props.BoolProperty(
        name='Enable Smoothing',
        description='Smooths weights in the area where weights got inpainted',
        default=False)
    smooth_limit_debug: bpy.props.BoolProperty(
        name='Limited vertices to Vertex Group',
        description='Visualize the vertices that got limited by writing to the "Limited" vertex group',
        default=False)
    num_limit_groups: bpy.props.IntProperty(
        name="Max groups per vertex",
        description="Amount of groups a vertex should be limited to. For VRChat/Unity keep it at 4.",
        min=1,
        default=4
    )


class KourinRobustWeightTransferPanel(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "Robust Weight Transfer"
    bl_idname = "OBJECT_PT_robust_weight_transfer_panel"
    bl_space_type = 'VIEW_3D'   # Defines the space type where the panel is located
    bl_region_type = 'UI'       # Specifies that the panel is drawn in the UI region
    bl_category = 'SENT'      # The name of the tab the panel will be in
    bl_options = set()

    def draw(self, context): 
        layout = self.layout

        if missing_deps:
            box = layout.box()
            col = box.column()
            global installed_deps
            if installed_deps:
                col.label(text="Dependencies installed!", icon='INFO')
                col.label(text="Restart Blender!", icon='ERROR')
                installed_deps = True
                return
            
            col.label(text="Blender will be unreactive while installing")
            col.operator("kourin.install_rwt_dependencies", icon='IMPORT')
            col.label(text="This might take a few minutes", icon='INFO')
            return

        active_obj = context.object
        if not context.object:
            layout.label(text='No active object selected.')
            return
        
        props = active_obj.kourin_weight_transfer_settings
        settings = context.scene.kourin_weight_transfer_settings
        
        # Object field for source
        row = layout.row(align=True)
        row.prop(settings, "source_object")
        row.prop(settings, "use_deformed_source",toggle=True, text="", icon='SHAPEKEY_DATA')
        row.prop(settings, "use_deformed_source",toggle=True, text="", icon='MODIFIER')
        
        # Vertex group field
        row = layout.row()
        row.label(text='Transfer Mask')
        row = row.row(align=True)
        row.prop_search(props, "vertex_group", active_obj, "vertex_groups", text='')
        row.prop (props , "vertex_group_invert",text="", toggle=True, icon='ARROW_LEFTRIGHT')
        row.enabled = not settings.apply_to_selected
        
        objs = lambda x: [obj for obj in x if obj != settings.source_object and isinstance(obj.data, bpy.types.Mesh)]
        if settings.apply_to_selected:
            target_objs = objs(context.selected_objects)
        else:
            target_objs = objs([context.object])
        if (len(target_objs) > 0
                and settings.use_deformed_target
                and any(util.has_modifier(obj, *util.TOPOLOGY_MODS) for obj in target_objs)):
            objs_str = ', '.join(obj.name for obj in target_objs)
            col = layout.column(align=True)
            col.label(text=f'Error: {objs_str}', icon='ERROR')
            col.label(text='  Topology altering Modifier!', icon='SHAPEKEY_DATA')
            col.label(text='  Deactivate Use Deformed Target or apply/delete modifier.', icon='MODIFIER')
            
        source_obj = settings.source_object
        if source_obj:
            armature_mods = [mod for mod in source_obj.modifiers if mod.type == "ARMATURE"]
            if len(armature_mods) == 0:
                col = layout.column(align=True)
                col.label(text=f'Subset is set to Deform Pose Bones,', icon='ERROR')
                col.label(text=f'but {source_obj.name} has no Armature Modifier')
            elif len(armature_mods) == 1:
                if not armature_mods[0].object:
                    col = layout.column(align=True)
                    col.label(text=f'Subset is set to Deform Pose Bones,', icon='ERROR')
                    col.label(text=f'but {source_obj.name} has an empty Armature Modifier object')
            else:
                col = layout.column(align=True)
                col.label(text=f'Subset is set to Deform Pose Bones,', icon='ERROR')
                col.label(text=f'but {source_obj.name} has multiple Armature Modifiers')
            
        row = layout.row(align=True)
        row.prop(settings, 'apply_to_selected', text='', icon='RESTRICT_SELECT_OFF')
        row.operator("kourin.skin_weight_transfer", text="Transfer Weights")
        row.prop(settings, "use_deformed_target",toggle=True, text="", icon='SHAPEKEY_DATA')
        row.prop(settings, "use_deformed_target",toggle=True, text="", icon='MODIFIER')
        
        layout.separator(factor=1)
        
        col = layout.column()
        col.label(text='Inpaint Mask')
        row = col.row(align=True)
        row.prop_search(props, "inpaint_group", active_obj, 'vertex_groups', text='')
        row.prop(props , "inpaint_group_invert",text="", toggle=True, icon='ARROW_LEFTRIGHT')
        row.prop(props, 'inpaint_threshold', text="")
        row.enabled = not settings.apply_to_selected

        
class KourinSettingsPanel(bpy.types.Panel):
    bl_idname = 'OBJECT_PT_kourin_weight_transfer_settings_panel'
    bl_label = 'Settings'
    bl_space_type = 'VIEW_3D'   # Defines the space type where the panel is located
    bl_region_type = 'UI'       # Specifies that the panel is drawn in the UI region
    bl_category = 'SENT'      # The name of the tab the panel will be in
    bl_parent_id = 'OBJECT_PT_robust_weight_transfer_panel'
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        settings = context.scene.kourin_weight_transfer_settings
        layout.operator('object.rbt_reset_scene_settings', icon='LOOP_BACK', text='Reset to Defaults')
        layout.prop(settings, 'inpaint_mode')
        layout.prop(settings, 'draw_matched')
        row = layout.row()
        row.enabled = not settings.enforce_four_bone_limit
        row.prop(settings, 'group_selection', text='Subset')


class KourinVertexMappingPanel(bpy.types.Panel):
    bl_label = "Vertex Mapping"
    bl_idname = "OBJECT_PT_vertex_mapping"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'SENT'
    bl_parent_id = 'OBJECT_PT_kourin_weight_transfer_settings_panel'

    def draw(self, context):
        layout = self.layout
        settings = context.scene.kourin_weight_transfer_settings
        layout.prop(settings, "max_distance")
        layout.prop(settings, "max_normal_angle_difference")
        layout.prop(settings, "flip_vertex_normal", text='Allow Flipped Vertex Normals')


class KourinSmoothingPanel(bpy.types.Panel):
    bl_label = "Smoothing"
    bl_idname = "OBJECT_PT_smoothing"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'SENT'
    bl_parent_id = 'OBJECT_PT_kourin_weight_transfer_settings_panel'

    def draw(self, context):
        layout = self.layout
        settings = context.scene.kourin_weight_transfer_settings
        layout.enabled = settings.smoothing_enable
        layout.prop(settings, 'smoothing_repeat')
        layout.prop(settings, 'smoothing_factor')
        
    def draw_header(self, context: bpy.types.Context):
        settings = context.scene.kourin_weight_transfer_settings
        col = self.layout.column(align=True)
        col.prop(settings, 'smoothing_enable', text='')

class KourinLimitGroupsPanel(bpy.types.Panel):
    bl_label = "Limit Vertex Groups"
    bl_idname = "OBJECT_PT_limit_groups"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'SENT'
    bl_parent_id = 'OBJECT_PT_kourin_weight_transfer_settings_panel'

    def draw(self, context):
        layout = self.layout
        settings = context.scene.kourin_weight_transfer_settings
        layout.enabled = settings.enforce_four_bone_limit
        layout.prop(settings, 'num_limit_groups')
        
    def draw_header(self, context: bpy.types.Context):
        settings = context.scene.kourin_weight_transfer_settings
        col = self.layout.column(align=True)
        col.prop(settings, 'enforce_four_bone_limit', text='')


class KourinResetSceneSettings(bpy.types.Operator):
    """Reset all settings to their default values"""
    bl_idname = "object.rbt_reset_scene_settings"
    bl_label = "Reset Robust Weight Transfer to Default Settings"

    def execute(self, context):
        settings = context.scene.kourin_weight_transfer_settings
        for prop_name, prop in settings.bl_rna.properties.items():
            if prop.is_readonly or prop_name in {'rna_type', 'name'}:
                continue
            if hasattr(prop, 'default'):
                setattr(settings, prop_name, prop.default)
            else:
                setattr(settings, prop_name, None)
        return {'FINISHED'}


class KourinUtilitiesPanel(bpy.types.Panel):
    bl_idname = 'OBJECT_PT_robust_weight_utilities_settings_panel'
    bl_label = 'Utilities'
    bl_space_type = 'VIEW_3D'   # Defines the space type where the panel is located
    bl_region_type = 'UI'       # Specifies that the panel is drawn in the UI region
    bl_category = 'SENT_'      # The name of the tab the panel will be in
    bl_parent_id = 'OBJECT_PT_robust_weight_transfer_panel'
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        settings = context.scene.kourin_weight_transfer_settings
        layout.operator('object.select_non_matched')
        row = layout.row(align=True)
        row.operator('object.smooth_limit_weights')
        row.prop(settings, 'smooth_limit_debug', text='', icon='GROUP_VERTEX')
    

class KourinSmoothLimit(bpy.types.Operator):
    """Limit weights of to a specific amount"""
    bl_idname = "object.smooth_limit_weights"
    bl_label = "Smoothed Limit Vertex Groups"
    bl_description = "Limits the amount weights per vertex of the active object"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        if not context.active_object: return False
        if context.mode != 'OBJECT' and context.mode != 'PAINT_WEIGHT': return False
        if context.active_object.type != 'MESH': return False
        
        return True
    
    def execute(self, context):
        scene_settings = context.scene.kourin_weight_transfer_settings
        obj = context.active_object
        is_deform = [util.is_vertex_group_deform_bone(obj, g.name) for g in obj.vertex_groups]
        W = util.get_groups_arr(obj, is_deform)
        adj_mat = util.get_mesh_adjacency_matrix_sparse(obj.data, True)
        mask = limit_mask(W, adj_mat, limit_num=scene_settings.num_limit_groups)
        W = (1 - mask) * W
        util.write_weights(obj, W[:, is_deform], [group.name for i, group in enumerate(obj.vertex_groups) if is_deform[i]], 0.0001)
        if scene_settings.smooth_limit_debug:
            limited = np.max(mask, axis=1)
            util.write_weights(obj, limited[:, np.newaxis], ['Limited'])
        return {'FINISHED'}

class KourinInstallDependencies(bpy.types.Operator):
    """Install missing Python dependencies"""
    bl_idname = "kourin.install_rwt_dependencies"
    bl_label = "Install Dependencies"
    
    def execute(self, context):
        python_exe = sys.executable
        print(python_exe)
        
        global libs_path
        if not os.path.exists(libs_path):
            os.makedirs(libs_path)
        try:
            subprocess.check_call([python_exe, "-m", "ensurepip"])
            subprocess.check_call([
                python_exe, "-m", "pip", "install", 
                *missing_deps, "--target", libs_path
            ])
            self.report({'INFO'}, "Installation successful! Please restart Blender.")
            global installed_deps
            installed_deps = True
            return {'FINISHED'}
        except subprocess.CalledProcessError as e:
            self.report({'ERROR'}, f"Installation failed: {str(e)}")
            return {'CANCELLED'}


def Robust_register():
    # bpy.types.VIEW3D_MT_make_links.append(menu_func)
    bpy.utils.register_class(KourinRobustWeightTransfer)
    bpy.utils.register_class(KourinRobustWeightTransferPanel)
    if missing_deps:
        bpy.utils.register_class(KourinInstallDependencies)
    else:
        bpy.utils.register_class(KourinInstallDependencies)
        bpy.utils.register_class(KourinSettingsPanel)
        bpy.utils.register_class(KourinVertexMappingPanel)
        bpy.utils.register_class(KourinLimitGroupsPanel)
        bpy.utils.register_class(KourinSmoothingPanel)
        bpy.utils.register_class(KourinObjectSettingsGroup)
        bpy.utils.register_class(KourinSceneSettingsGroup)
        bpy.utils.register_class(KourinSelectNonMatched)
        bpy.utils.register_class(KourinResetSceneSettings)
        bpy.utils.register_class(KourinUtilitiesPanel)
        bpy.utils.register_class(KourinSmoothLimit)
        bpy.types.Object.kourin_weight_transfer_settings = bpy.props.PointerProperty(type=KourinObjectSettingsGroup)
        bpy.types.Scene.kourin_weight_transfer_settings = bpy.props.PointerProperty(type=KourinSceneSettingsGroup)
        

    
def Robust_unregister():
    # bpy.types.VIEW3D_MT_make_links.remove(menu_func)
    bpy.utils.unregister_class(KourinRobustWeightTransfer)
    bpy.utils.unregister_class(KourinRobustWeightTransferPanel)
    if missing_deps:
        bpy.utils.unregister_class(KourinInstallDependencies)
    else:
        bpy.utils.register_class(KourinInstallDependencies)
        bpy.utils.unregister_class(KourinSettingsPanel)
        bpy.utils.unregister_class(KourinVertexMappingPanel)
        bpy.utils.unregister_class(KourinLimitGroupsPanel)
        bpy.utils.unregister_class(KourinSmoothingPanel)
        bpy.utils.unregister_class(KourinObjectSettingsGroup)
        bpy.utils.unregister_class(KourinSceneSettingsGroup)
        bpy.utils.unregister_class(KourinSelectNonMatched)
        bpy.utils.unregister_class(KourinResetSceneSettings)
        bpy.utils.unregister_class(KourinUtilitiesPanel)
        bpy.utils.unregister_class(KourinSmoothLimit)
        del bpy.types.Object.kourin_weight_transfer_settings
        del bpy.types.Scene.kourin_weight_transfer_settings


# if __name__ == "__main__":
#     register()