import bpy

class Weight_obj_source(bpy.types.Operator):
    """自定义图标按钮"""
    bl_idname = "kourin.weight_obj_source"
    bl_label = "设置权重来源"
    bl_options = {'REGISTER', 'UNDO'}
    @classmethod
    def poll(cls, context):
        o=context.active_object
        return o is not None and o.type=='MESH'
    def execute(self, context):
        settings = context.scene.kourin_weight_transfer_settings
        settings.source_object=context.active_object
        self.report({'INFO'}, f"权重来源物体设置为{context.active_object.name}")
        return {'FINISHED'}

def source_obj(self, context):
    layout = self.layout
    settings = context.scene.kourin_weight_transfer_settings
    layout.prop(settings, "source_object")
    layout.operator(
        "kourin.weight_obj_source", 
        icon='SNAP_VOLUME',  # 使用Blender内置图标
        text=""  # 空文本只显示图标
    )
    layout.prop(settings, "mirror_enable")

