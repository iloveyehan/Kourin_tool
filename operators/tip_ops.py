import bpy
from ..imgui_setup import toast_drawer


class WM_OT_toast_at_mouse(bpy.types.Operator):
    """在鼠标位置显示一个短暂提示（方便测试/快捷使用）"""
    bl_idname = "wm.toast_at_mouse"
    bl_label = "Toast at Mouse"

    message: bpy.props.StringProperty(name="Message", default="操作完成")
    seconds: bpy.props.FloatProperty(name="Seconds", default=2.0, min=0.1, max=10.0)

    def invoke(self, context, event):
        # 获取 region 内鼠标坐标（适用于在区域内 invoke）
        mx = getattr(event, "mouse_region_x", None)
        my = getattr(event, "mouse_region_y", None)
        print(mx,my,mx is None,my is None)
        print(context.region.y)
        if mx is None or my is None:
            
            # 回退：尝试用 context.region 的中心
            try:
                region = context.region
                mx = region.width / 2
                my = region.height / 2
            except Exception:
                mx, my = 300, 300
        toast_drawer.open_tip(self.message, seconds=self.seconds, position=(mx, my))
        return {'FINISHED'}