import bpy
class Kourin_uv_unify_uv_name(bpy.types.Operator):
    """统一uv名称"""

    bl_idname = "kourin.unify_uv_name"
    bl_label = "uv_规范当前激活uv名称为UVMap"
    bl_options = {'UNDO'}


    @classmethod
    def poll(cls, context):
        return 1

    def execute(self, context):
        for i in bpy.context.scene.objects:
            if i.type=='MESH':
                if not len(i.data.uv_layers):
                    i.data.uv_layers.new(name='UVMap')
                    continue
                for uv in bpy.context.object.data.uv_layers:
                    if not uv.active and uv.name=='UVMap':
                        uv.name='UVMap_temp'
                i.data.uv_layers.active.name='UVMap'

        return {'FINISHED'}
