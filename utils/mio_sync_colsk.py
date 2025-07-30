
import bpy

from .utils import has_shapekey, is_sync_collection
from ..ui.qt_global import GlobalProperty as GP

def sync_shapekey_value():
    object = bpy.context.object
    if object is None:
        return
    prop_o = GP.get().obj_sync_col
    if is_sync_collection(object):
        key_blocks = object.data.shape_keys.key_blocks
        for item in [v for v in prop_o[object.as_pointer()].objects if has_shapekey(v) and v != object]:
            for item_key in item.data.shape_keys.key_blocks:
                if item_key.name in key_blocks:
                    if item_key.mute != key_blocks[item_key.name].mute:
                        item_key.mute = key_blocks[item_key.name].mute
                    if item_key.value != key_blocks[item_key.name].value:
                        item_key.value = key_blocks[item_key.name].value


def sync_show_only_shape_key():

    object = bpy.context.object
    if object is None:
        return
    prop_o = GP.get().obj_sync_col
    if is_sync_collection(object):
        for item in [v for v in prop_o[object.as_pointer()].objects if has_shapekey(v) and v != object]:
            if item.show_only_shape_key != object.show_only_shape_key:
                item.show_only_shape_key = object.show_only_shape_key


def sync_active_shape_key():

    object = bpy.context.object
    if object is None:
        return
    prop_o = GP.get().obj_sync_col

    if is_sync_collection(object):
        for elem in [o for o in prop_o[object.as_pointer()].objects if has_shapekey(o) and o != object]:
            index = elem.data.shape_keys.key_blocks.find(object.active_shape_key.name)
            elem.active_shape_key_index = index if index >= 0 else 0


def callback_update_shapekey():
    sync_shapekey_value()


def callback_show_only_shape_key():
    sync_show_only_shape_key()


def callback_rename_shapekey():
    pass


def callback_active_shapekey():

    sync_active_shape_key()
