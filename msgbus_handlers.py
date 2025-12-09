from pathlib import Path
import time
import bpy

from .utils.mio_sync_colsk import callback_show_only_shape_key, callback_update_shapekey
from .imgui_setup.imgui_global import GlobalImgui,_globalimgui_load_pre,_globalimgui_load_post
# from .common.class_loader.auto_load import ClassAutoloader
# msgbus_handler=ClassAutoloader(Path(__file__))
from bpy.app.handlers import persistent
@persistent
def load_post_handler(dummy):
    # register_sculpt_warning_handler()
    # 每次新文件加载完成后，重新执行消息总线订阅
    register_msgbus()
    GlobalImgui.get().obj_sync_col.clear()
def unregister_msgbus():
    bpy.msgbus.clear_by_owner(__name__)
    print("[IMGUI DEBUG]消息总线订阅已移除。")
def reg_msgbus_handler():
    # msgbus_handler.init()
    # msgbus_handler.register()
    # bpy.types.TOPBAR_MT_editor_menus.append(menu_func)
    bpy.app.handlers.load_post.append(load_post_handler)
    if _globalimgui_load_pre not in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.append(_globalimgui_load_pre)
    if _globalimgui_load_post not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_globalimgui_load_post)
    # register_sculpt_warning_handler()
    register_msgbus()
def unreg_msgbus_handler():
    unregister_msgbus()
    # msgbus_handler.unregister()
    # bpy.types.TOPBAR_MT_editor_menus.remove(menu_func)
    # unregister_sculpt_warning_handler()
    if load_post_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_post_handler)
    try:
        bpy.app.handlers.load_pre.remove(_globalimgui_load_pre)
    except Exception:
        pass
    try:
        bpy.app.handlers.load_post.remove(_globalimgui_load_post)
    except Exception:
        pass
def mirror_x_changed(*args):
    # print('mirorx')
    g = GlobalImgui.get()

    # 兼容旧调用：如果没有任何 draw handler 或 _regions，直接返回
    has_handlers = False
    try:
        # 优先检查新的内部结构
        has_handlers = bool(getattr(g, "_regions", {}))
    except Exception:
        has_handlers = bool(getattr(g, "draw_handlers", {}))

    if not has_handlers:
        # print('ret  ')
        return

    # 安全读取当前物体

    obj = bpy.context.view_layer.objects.active


    if obj is None:
        return

    try:
        if obj.mode in ['SCULPT', 'EDIT']:
            if not getattr(obj, 'use_mesh_mirror_x', True):
                g.show_mirror_reminder_window = True
                g.mirror_reminder_window_open_time = time.time()
    except Exception:
        # 避免任何异常打断 Blender msgbus 的调用
        pass
def on_mode_changed(*args):
    # print('mode')
    g = GlobalImgui.get()


    obj = bpy.context.view_layer.objects.active


    if obj is None:
        return
    settings = bpy.context.scene.kourin_weight_transfer_settings
    if settings.mirror_enable:
        obj.use_mesh_mirror_x = True
    try:
        if obj.mode in ['SCULPT', 'EDIT']:
            if not getattr(obj, 'use_mesh_mirror_x', True):
                g.show_mirror_reminder_window = True
                g.mirror_reminder_window_open_time = time.time()
    except Exception:
        # 避免任何异常打断 Blender msgbus 的调用
        pass

    # on_active_or_mode_change()
def on_active_change():
    from .imgui_setup.imgui_global import GlobalImgui as GP
    # print('qt_window',qt_window,'物体切换')
    new_obj=bpy.context.view_layer.objects.active
    gp =GP.get()
    # self.obj=new_obj
    # 如果是 mesh 类型的对象并且发生了变化
    if new_obj and new_obj.type == 'MESH':
        if new_obj != gp.last_mesh_obj and new_obj and new_obj.type == 'MESH':

            gp.last_mesh_obj = new_obj # 保存旧的 mesh 对象
            gp.obj_change_sk=True
            # self.last_mesh_obj_ptr=self.obj.as_pointer()
        settings = bpy.context.scene.kourin_weight_transfer_settings
        if settings.mirror_enable:
            new_obj.use_mesh_mirror_x = True

def register_msgbus():
    # 监听所有 Object 实例的 mode 属性变化 :contentReference[oaicite:1]{index=1}
    bpy.msgbus.subscribe_rna(
        key=(bpy.types.LayerObjects, "active"),
        owner=__name__,
        args=(),
        notify=on_active_change,
        options={'PERSISTENT'}
    )
    bpy.msgbus.subscribe_rna(
        key=(bpy.types.Object, "mode"),
        owner=__name__,
        args=(),
        notify=on_mode_changed,
        options={'PERSISTENT'}
    )
    bpy.msgbus.subscribe_rna(
        key=(bpy.types.Object, "use_mesh_mirror_x"),
        owner=__name__,
        args=(),
        notify=mirror_x_changed,
        options={'PERSISTENT'},
    )
    bpy.msgbus.subscribe_rna(
        key=(bpy.types.ShapeKey, "value"),
        owner=__name__,
        args=(),
        notify=callback_update_shapekey,
    )
    bpy.msgbus.subscribe_rna(
        key=(bpy.types.ShapeKey, "mute"),
        owner=__name__,
        args=(),
        notify=callback_update_shapekey,
    )
    bpy.msgbus.subscribe_rna(
        key=(bpy.types.Object, "show_only_shape_key"),
        owner=__name__,
        args=(),
        notify=callback_show_only_shape_key,
    )