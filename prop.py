import bpy
import math
def update_enforce_four_bone_limit(self, context):
    """Ensure the correct group selection and enforce constraints."""
    if self.enforce_four_bone_limit:
        self.group_selection = 'DEFORM_POSE_BONES'
class ImguiObjectSettingsGroup(bpy.types.PropertyGroup):
    vertex_group: bpy.props.StringProperty(name='Mask Vertex Group')
    vertex_group_invert: bpy.props.BoolProperty(name='Invert')
    inpaint_group: bpy.props.StringProperty(name='Inpaint Vertex Group')
    inpaint_group_invert: bpy.props.BoolProperty(name='Invert Inpaint')
    inpaint_threshold: bpy.props.FloatProperty(name='Inpaint Binary Threshold', default=0.5, min=0, max=1)
class ImguiSceneSettingsGroup(bpy.types.PropertyGroup):
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
        default=True)
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
    mirror_enable: bpy.props.BoolProperty(
        name='自动镜像',
        description='自动开启物体x镜像',
        default=True)

