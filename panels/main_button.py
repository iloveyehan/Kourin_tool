import bpy

class CUSTOM_OT_icon_button(bpy.types.Operator):
    """自定义图标按钮"""
    bl_idname = "wm.custom_icon_button"
    bl_label = "Custom Icon Button"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # 这里可以添加点击后的操作逻辑
        self.report({'INFO'}, "你点击了自定义图标！")
        return {'FINISHED'}

def draw_menu(self, context):
    layout = self.layout
    layout.operator(
        "wm.custom_icon_button", 
        icon='INFO',  # 使用Blender内置图标
        text=""  # 空文本只显示图标
    )

def main_button_register():
    bpy.utils.register_class(CUSTOM_OT_icon_button)
    # 添加到3D视图的编辑器菜单
    bpy.types.VIEW3D_MT_editor_menus.append(draw_menu)

def main_button_unregister():
    bpy.utils.unregister_class(CUSTOM_OT_icon_button)
    bpy.types.VIEW3D_MT_editor_menus.remove(draw_menu)

