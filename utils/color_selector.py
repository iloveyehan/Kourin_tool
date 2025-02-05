def debug_print(DEBUG_MODE,*args):
    if DEBUG_MODE:
        print("[DEBUG]", *args)
import copy
import colorsys

import bpy
import os
def get_path():
    return os.path.dirname((os.path.realpath(__file__)))

def get_name():
    return os.path.basename(get_path())

def get_prefs():
    return bpy.context.preferences.addons[get_name()].preferences

def set_brush_color_based_on_mode(picker,color=None,hsv=None):
    '''根据模式设置画笔颜色'''
    # 获取当前的模式
    # print("Context:", context)
    # print("Dir(Context):", dir(context))
    # print(context.active_object)
    mode = picker.mode
    # if hsv:
    debug_print(1,hsv,'画笔颜色hsv',color)

    # color=(colorsys.hsv_to_rgb(*color))
    # debug_print(1,'画笔颜色rgb',color,mode)
    if hsv:
        # 根据不同的模式获取笔刷颜色
        if mode in ['VERTEX_PAINT','PAINT_VERTEX']:
            # 在顶点绘制模式下
            picker.tool_settings.vertex_paint.brush.color.hsv = color

        elif mode in ['TEXTURE_PAINT','PAINT_TEXTURE']:
            # 在纹理绘制模式下
            picker.tool_settings.image_paint.brush.color.hsv = color
            debug_print(1,hsv,'画笔验证hsv',picker.tool_settings.image_paint.brush.color.hsv)
        elif mode == 'PAINT_GPENCIL':
            # 在 Grease Pencil 绘制模式下
            picker.tool_settings.gpencil_paint.brush.color.hsv = color
        elif mode == 'VERTEX_GPENCIL':
            # 在 Grease Pencil 绘制模式下
            picker.tool_settings.gpencil_vertex_paint.brush.color.hsv = color
        elif mode == 'SCULPT':
            bpy.data.brushes['Paint'].color.hsv = color
        elif picker.ui_mode == 'PAINT':
            picker.tool_settings.image_paint.brush.color.hsv = color
    else:
        # 根据不同的模式获取笔刷颜色
        if mode in ['VERTEX_PAINT','PAINT_VERTEX']:
            # 在顶点绘制模式下
            picker.tool_settings.vertex_paint.brush.color=color

        elif mode in ['TEXTURE_PAINT','PAINT_TEXTURE']:
            # 在纹理绘制模式下
            picker.tool_settings.image_paint.brush.color=color

        elif mode == 'PAINT_GPENCIL':
            # 在 Grease Pencil 绘制模式下
            picker.tool_settings.gpencil_paint.brush.color=color
        elif mode == 'VERTEX_GPENCIL':
            # 在 Grease Pencil 绘制模式下
            picker.tool_settings.gpencil_vertex_paint.brush.color = color
        elif mode == 'SCULPT':
            bpy.data.brushes['Paint'].color = color
        elif picker.ui_mode == 'PAINT':
            picker.tool_settings.image_paint.brush.color = color
def brush_value_based_on_mode(set=False,get=False,size=False,strength=False,):
    '''根据不同参数get或者set画笔的大小 强度'''
    mode = bpy.context.object.mode
    if set:
        # 根据不同的模式获取笔刷颜色
        if mode == 'VERTEX_PAINT':
            # 在顶点绘制模式下
            if size:
                bpy.context.scene.tool_settings.unified_paint_settings.size=size
                # bpy.context.tool_settings.vertex_paint.brush.size = size
                # print('set size',size)
            if strength:
                bpy.context.tool_settings.vertex_paint.brush.strength = strength
        elif mode == 'TEXTURE_PAINT':
            # 在纹理绘制模式下
            if size:
                bpy.context.scene.tool_settings.unified_paint_settings.size = size
                # bpy.context.tool_settings.image_paint.brush.size = size
            if strength:
                bpy.context.tool_settings.image_paint.brush.strength = strength

        elif mode == 'PAINT_GPENCIL':
            # 在 Grease Pencil 绘制模式下
            if size:
            # bpy.context.tool_settings.gpencil_paint.brush.strength=strength
                if bpy.context.tool_settings.gpencil_paint.brush==bpy.data.brushes['Pencil']:
                    bpy.data.brushes['Pencil'].size = size
                elif bpy.context.tool_settings.gpencil_paint.brush==bpy.data.brushes['Tint']:
                    bpy.data.brushes['Tint'].size = size
                else:
                    bpy.context.tool_settings.gpencil_paint.brush.size = size
            if strength:
                if bpy.context.tool_settings.gpencil_paint.brush == bpy.data.brushes['Pencil']:
                    bpy.data.brushes['Pencil'].gpencil_settings.pen_strength = strength
                elif bpy.context.tool_settings.gpencil_paint.brush == bpy.data.brushes['Tint']:
                    bpy.data.brushes['Tint'].gpencil_settings.pen_strength = strength
                else:
                    if hasattr(bpy.context.tool_settings.gpencil_paint.brush.gpencil_settings, 'pen_strength'):
                        bpy.context.tool_settings.gpencil_paint.brush.gpencil_settings.pen_strength = strength
        elif mode == 'VERTEX_GPENCIL':
            # 在 Grease Pencil 绘制模式下
            if size:
                if bpy.context.tool_settings.gpencil_vertex_paint.brush==bpy.data.brushes['Vertex Draw']:
                    bpy.data.brushes['Vertex Draw'].size = size
                elif bpy.context.tool_settings.gpencil_vertex_paint.brush==bpy.data.brushes['Vertex Blur']:
                    bpy.data.brushes['Vertex Blur'].size = size
                elif bpy.context.tool_settings.gpencil_vertex_paint.brush==bpy.data.brushes['Vertex Average']:
                    bpy.data.brushes['Vertex Average'].size = size
                elif bpy.context.tool_settings.gpencil_vertex_paint.brush==bpy.data.brushes['Vertex Smear']:
                    bpy.data.brushes['Vertex Smear'].size = size
                elif bpy.context.tool_settings.gpencil_vertex_paint.brush==bpy.data.brushes['Vertex Replace']:
                    bpy.data.brushes['Vertex Replace'].size = size

                else:
                    bpy.context.tool_settings.gpencil_vertex_paint.brush.size = size
            if strength:
                if bpy.context.tool_settings.gpencil_vertex_paint.brush == bpy.data.brushes['Vertex Draw']:
                    if hasattr(bpy.context.tool_settings.gpencil_vertex_paint.brush.gpencil_settings, 'pen_strength'):
                        bpy.data.brushes['Vertex Draw'].gpencil_settings.pen_strength = strength
                elif bpy.context.tool_settings.gpencil_vertex_paint.brush == bpy.data.brushes['Vertex Blur']:
                    if hasattr(bpy.context.tool_settings.gpencil_vertex_paint.brush.gpencil_settings, 'pen_strength'):
                        bpy.data.brushes['Vertex Blur'].gpencil_settings.pen_strength = strength
                elif bpy.context.tool_settings.gpencil_vertex_paint.brush == bpy.data.brushes['Vertex Average']:
                    if hasattr(bpy.context.tool_settings.gpencil_vertex_paint.brush.gpencil_settings, 'pen_strength'):
                        bpy.data.brushes['Vertex Average'].gpencil_settings.pen_strength = strength
                elif bpy.context.tool_settings.gpencil_vertex_paint.brush == bpy.data.brushes['Vertex Smear']:
                    if hasattr(bpy.context.tool_settings.gpencil_vertex_paint.brush.gpencil_settings, 'pen_strength'):
                        bpy.data.brushes['Vertex Smear'].gpencil_settings.pen_strength = strength
                elif bpy.context.tool_settings.gpencil_vertex_paint.brush == bpy.data.brushes['Vertex Replace']:
                    if hasattr(bpy.context.tool_settings.gpencil_vertex_paint.brush.gpencil_settings, 'pen_strength'):
                        bpy.data.brushes['Vertex Replace'].gpencil_settings.pen_strength = strength
        elif mode == 'SCULPT':
            if size:
                bpy.data.brushes['Paint'].size = size
            if strength:
                bpy.data.brushes['Paint'].strength = strength
        elif bpy.context.area.spaces.active.ui_mode == 'PAINT':
            if size:
                bpy.context.tool_settings.image_paint.brush.size = size
            if strength:
                bpy.context.tool_settings.image_paint.brush.strength = strength

    if get:
        if mode == 'VERTEX_PAINT':
            # 在顶点绘制模式下
            brush = bpy.context.tool_settings.vertex_paint.brush
            if size:
                value = bpy.context.scene.tool_settings.unified_paint_settings.size
            if strength:
                value =  brush.strength
            # print('sizeget ',value)
        elif mode == 'TEXTURE_PAINT':
            # 在纹理绘制模式下
            brush = bpy.context.tool_settings.image_paint.brush
            if size:
                value = bpy.context.scene.tool_settings.unified_paint_settings.size
            if strength:
                value = brush.strength
        elif mode == 'PAINT_GPENCIL':
            if size:
                # bpy.context.tool_settings.gpencil_paint.brush.strength=strength
                if bpy.context.tool_settings.gpencil_paint.brush == bpy.data.brushes['Pencil']:
                    value=bpy.data.brushes['Pencil'].size
                elif bpy.context.tool_settings.gpencil_paint.brush == bpy.data.brushes['Tint']:
                    value=bpy.data.brushes['Tint'].size
                else:
                    value=bpy.context.tool_settings.gpencil_paint.brush.size
            if strength:
                if bpy.context.tool_settings.gpencil_paint.brush == bpy.data.brushes['Pencil']:
                    value=bpy.data.brushes['Pencil'].gpencil_settings.pen_strength
                elif bpy.context.tool_settings.gpencil_paint.brush == bpy.data.brushes['Tint']:
                    value=bpy.data.brushes['Tint'].gpencil_settings.pen_strength
                else:
                    if hasattr(bpy.context.tool_settings.gpencil_paint.brush.gpencil_settings, 'pen_strength'):
                        value=bpy.context.tool_settings.gpencil_paint.brush.gpencil_settings.pen_strength
        elif mode == 'VERTEX_GPENCIL':
            # 在 Grease Pencil 绘制模式下
            # brush = bpy.context.tool_settings.gpencil_vertex_paint.brush
            if size:
                if bpy.context.tool_settings.gpencil_vertex_paint.brush==bpy.data.brushes['Vertex Draw']:
                    value = bpy.data.brushes['Vertex Draw'].size
                elif bpy.context.tool_settings.gpencil_vertex_paint.brush==bpy.data.brushes['Vertex Blur']:
                    value = bpy.data.brushes['Vertex Blur'].size
                elif bpy.context.tool_settings.gpencil_vertex_paint.brush==bpy.data.brushes['Vertex Average']:
                    value = bpy.data.brushes['Vertex Average'].size
                elif bpy.context.tool_settings.gpencil_vertex_paint.brush==bpy.data.brushes['Vertex Smear']:
                    value = bpy.data.brushes['Vertex Smear'].size
                elif bpy.context.tool_settings.gpencil_vertex_paint.brush==bpy.data.brushes['Vertex Replace']:
                    value = bpy.data.brushes['Vertex Replace'].size

                else:
                    value = bpy.context.tool_settings.gpencil_paint.brush.size
            if strength:
                if bpy.context.tool_settings.gpencil_vertex_paint.brush == bpy.data.brushes['Vertex Draw']:
                    if hasattr(bpy.context.tool_settings.gpencil_vertex_paint.brush.gpencil_settings, 'pen_strength'):
                        value = bpy.data.brushes['Vertex Draw'].gpencil_settings.pen_strength
                elif bpy.context.tool_settings.gpencil_vertex_paint.brush == bpy.data.brushes['Vertex Blur']:
                    if hasattr(bpy.context.tool_settings.gpencil_vertex_paint.brush.gpencil_settings, 'pen_strength'):
                        value = bpy.data.brushes['Vertex Blur'].gpencil_settings.pen_strength
                elif bpy.context.tool_settings.gpencil_vertex_paint.brush == bpy.data.brushes['Vertex Average']:
                    if hasattr(bpy.context.tool_settings.gpencil_vertex_paint.brush.gpencil_settings, 'pen_strength'):
                        value = bpy.data.brushes['Vertex Average'].gpencil_settings.pen_strength
                elif bpy.context.tool_settings.gpencil_vertex_paint.brush == bpy.data.brushes['Vertex Smear']:
                    if hasattr(bpy.context.tool_settings.gpencil_vertex_paint.brush.gpencil_settings, 'pen_strength'):
                        value = bpy.data.brushes['Vertex Smear'].gpencil_settings.pen_strength
                elif bpy.context.tool_settings.gpencil_vertex_paint.brush == bpy.data.brushes['Vertex Replace']:
                    if hasattr(bpy.context.tool_settings.gpencil_vertex_paint.brush.gpencil_settings, 'pen_strength'):
                        value = bpy.data.brushes['Vertex Replace'].gpencil_settings.pen_strength
            # strength = bpy.data.brushes['Vertex Draw'].gpencil_settings.pen_strength
        elif mode == 'SCULPT':
            brush = bpy.data.brushes['Paint']
            if size:
                value =  brush.size
            if strength:
                value =  brush.strength
        elif bpy.context.area.spaces.active.ui_mode == 'PAINT':
            brush = bpy.context.tool_settings.image_paint.brush
            if size:
                value =  brush.size
            if strength:
                value =  brush.strength
        return value
def get_brush_color_based_on_mode():
        '''根据模式获得画笔颜色'''
        # 获取当前的模式
        mode = bpy.context.object.mode

        # 根据不同的模式获取笔刷颜色
        if mode == 'VERTEX_PAINT':
            # 在顶点绘制模式下
            brush = bpy.context.tool_settings.vertex_paint.brush
            color = brush.color
        elif mode == 'TEXTURE_PAINT':
            # 在纹理绘制模式下
            brush = bpy.context.tool_settings.image_paint.brush
            color = brush.color
        elif mode == 'PAINT_GPENCIL':
            # 在 Grease Pencil 绘制模式下
            brush = bpy.context.tool_settings.gpencil_paint.brush
            color = brush.color
        elif mode == 'VERTEX_GPENCIL':
            # 在 Grease Pencil 绘制模式下
            brush = bpy.context.tool_settings.gpencil_vertex_paint.brush
            color = brush.color
        elif mode=='SCULPT':
            brush = bpy.data.brushes['Paint']
            color = brush.color
        elif bpy.context.area.spaces.active.ui_mode=='PAINT':
            brush = bpy.context.tool_settings.image_paint.brush
            color = brush.color
        return color



def exchange_brush_color_based_on_mode(exchange=None):
    '''根据模式切换前景色后景色'''
    mode = bpy.context.object.mode
    if exchange:
        # 根据不同的模式获取笔刷颜色
        if mode == 'VERTEX_PAINT':
            # 在顶点绘制模式下
            tmp=copy.deepcopy(bpy.context.tool_settings.vertex_paint.brush.color)
            bpy.context.tool_settings.vertex_paint.brush.color= bpy.context.tool_settings.vertex_paint.brush.secondary_color
            bpy.context.tool_settings.vertex_paint.brush.secondary_color=tmp

        elif mode == 'TEXTURE_PAINT':
            # 在纹理绘制模式下
            tmp = copy.deepcopy(bpy.context.tool_settings.image_paint.brush.color)
            bpy.context.tool_settings.image_paint.brush.color = bpy.context.tool_settings.image_paint.brush.secondary_color
            bpy.context.tool_settings.image_paint.brush.secondary_color=tmp

        elif mode == 'PAINT_GPENCIL':
            # 在 Grease Pencil 绘制模式下
            tmp = copy.deepcopy(bpy.context.tool_settings.gpencil_paint.brush.color)
            bpy.context.tool_settings.gpencil_paint.brush.color = bpy.context.tool_settings.gpencil_paint.brush.secondary_color
            bpy.context.tool_settings.gpencil_paint.brush.secondary_color=tmp
        elif mode == 'SCULPT':
            tmp = copy.deepcopy(bpy.data.brushes['Paint'].color)
            bpy.data.brushes['Paint'].color = bpy.data.brushes['Paint'].secondary_color
            bpy.data.brushes['Paint'].secondary_color=tmp


def register_keymaps(keylist):
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon

    keymaps = []

    if kc:

        for item in keylist:
            keymap = item.get("keymap")
            space_type = item.get("space_type", "EMPTY")

            if keymap:
                km = kc.keymaps.new(name=keymap, space_type=space_type)

                if km:
                    idname = item.get("idname")
                    type = item.get("type")
                    value = item.get("value")

                    shift = item.get("shift", False)
                    ctrl = item.get("ctrl", False)
                    alt = item.get("alt", False)

                    kmi = km.keymap_items.new(idname, type, value, shift=shift, ctrl=ctrl, alt=alt)

                    if kmi:
                        properties = item.get("properties")

                        if properties:
                            for name, value in properties:
                                setattr(kmi.properties, name, value)

                        active = item.get("active", True)
                        kmi.active = active

                        keymaps.append((km, kmi))
    else:
        print("WARNING: Keyconfig not availabe, skipping color picker keymaps")

    return keymaps
def unregister_keymaps(keymaps):
    for km, kmi in keymaps:
        km.keymap_items.remove(kmi)
def im_pow(list,gamma):
    return (pow(list[0],gamma),pow(list[1],gamma),pow(list[2],gamma))