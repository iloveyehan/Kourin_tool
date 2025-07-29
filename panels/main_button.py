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

def draw_menu(self, context):
    layout = self.layout
    settings = context.scene.kourin_weight_transfer_settings
    layout.prop(settings, "source_object")
    layout.operator(
        "kourin.weight_obj_source", 
        icon='SNAP_VOLUME',  # 使用Blender内置图标
        text=""  # 空文本只显示图标
    )

def main_button_register():
    bpy.utils.register_class(Weight_obj_source)
    # 添加到3D视图的编辑器菜单
    bpy.types.VIEW3D_MT_editor_menus.append(draw_menu)

def main_button_unregister():
    bpy.utils.unregister_class(Weight_obj_source)
    bpy.types.VIEW3D_MT_editor_menus.remove(draw_menu)

