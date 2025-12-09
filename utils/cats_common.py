import bpy
from typing import Optional, Set, Dict, Any
def get_objects():
    return bpy.context.view_layer.objects
def is_hidden(obj):
    if hasattr(obj, 'hide_get'):
        return obj.hide_get()
    elif hasattr(obj, 'hide'):
        return obj.hide
    return False  # Return a default value if the hide state cannot be determined
def set_active(obj, skip_sel=False):
    if not skip_sel:
        select(obj)
        bpy.context.view_layer.objects.active = obj
def select(obj, sel=True):
    if obj is not None:
        hide(obj, False)
        obj.select_set(sel)
def hide(obj, val=True):
    if hasattr(obj, 'hide_set'):
        obj.hide_set(val)
    elif hasattr(obj, 'hide'):
        obj.hide = val
def switch(new_mode, check_mode=True):
    context = bpy.context
    active = context.view_layer.objects.active
    if check_mode and active and active.mode == new_mode:
        return
    
    # Validate that the active object supports the requested mode
    if active is None:
        print(f"Warning: No active object when trying to switch to {new_mode} mode")
        return
        
    # Check if the object type supports the requested mode
    supported_modes = []
    if active.type == 'MESH':
        supported_modes = ['OBJECT', 'EDIT', 'SCULPT', 'VERTEX_PAINT', 'WEIGHT_PAINT', 'TEXTURE_PAINT']
    elif active.type == 'ARMATURE':
        supported_modes = ['OBJECT', 'EDIT', 'POSE']
    elif active.type in ['CURVE', 'SURFACE', 'META', 'FONT']:
        supported_modes = ['OBJECT', 'EDIT']
    elif active.type == 'LATTICE':
        supported_modes = ['OBJECT', 'EDIT']
    else:
        supported_modes = ['OBJECT']
    
    if new_mode not in supported_modes:
        print(f"Warning: {active.type} object '{active.name}' does not support {new_mode} mode. Supported modes: {supported_modes}")
        return
    
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode=new_mode, toggle=False)
def get_enum_property_value(property_holder, property_name, items_func=None):
    """Safely get an enum property value, handling integer indices from Blender 5.0.
    
    Args:
        property_holder: The object holding the property (e.g., context.scene)
        property_name: Name of the enum property
        items_func: Optional function to get valid items. If provided, integer indices
                   will be converted to their corresponding identifier strings.
    
    Returns:
        The string identifier value of the enum, or empty string if invalid.
    """
    try:
        value = getattr(property_holder, property_name, None)
        if value is None:
            return ''
        
        # If it's already a valid string, return it
        if isinstance(value, str):
            return value
        
        # Handle integer index (Blender 5.0 compatibility)
        if isinstance(value, int) and items_func is not None:
            try:
                # Get the items to convert index to identifier
                items = items_func(property_holder, bpy.context)
                if items and 0 <= value < len(items):
                    return items[value][0]  # Return the identifier
            except:
                pass
        
        return str(value) if value is not None else ''
    except:
        return ''
def get_armature_list(self, context):
    choices = []

    for armature in get_armature_objects():
        # Set name displayed in list
        name = armature.data.name
        if name.startswith('Armature ('):
            name = armature.name + ' (' + name.replace('Armature (', '')[:-1] + ')'

        # 1. Will be returned by context.scene
        # 2. Will be shown in lists
        # 3. will be shown in the hover description (below description)
        choices.append((armature.name, name, armature.name))
    
    return choices


def get_armature_objects():
    armatures = []
    for obj in get_objects():
        if obj.type == 'ARMATURE':
            armatures.append(obj)
    return armatures
_empty_enum_identifier = 'Cats_empty_enum_identifier'
def is_enum_empty(string):
    """Returns True only if the tested string is the string that signifies that an EnumProperty is empty.

    Returns False in all other cases."""
    return _empty_enum_identifier == string
def get_armature(armature_name=None):
    if not armature_name:
        # Use safe enum getter for Blender 5.0 compatibility
        armature_name = get_enum_property_value(bpy.context.scene, 'armature', get_armature_list)
        
    # Handle case where armature_name might still be an integer (e.g., passed directly)
    if isinstance(armature_name, int):
        armatures = get_armature_objects()
        if 0 <= armature_name < len(armatures):
            return armatures[armature_name]
        elif armatures:
            return armatures[0]
        return None
        
    # Get all objects in the scene
    objects = get_objects()
    if not objects:
        return None
        
    # First try to find exact name match
    for obj in objects:
        if obj and obj.type == 'ARMATURE':
            if obj.name == armature_name:
                return obj
                
    # If no exact match, return first armature if name is empty
    if is_enum_empty(armature_name):
        for obj in objects:
            if obj and obj.type == 'ARMATURE':
                return obj
    
    # Fallback: if the selected armature doesn't exist, return the first available armature
    for obj in objects:
        if obj and obj.type == 'ARMATURE':
            return obj
                
    return None
def get_meshes_objects(armature_name=None, mode=0, check=True, visible_only=False):
    context = bpy.context
    # Modes:
    # 0 = With armatures only
    # 1 = Top level only
    # 2 = All meshes
    # 3 = Selected only

    if not armature_name:
        armature = get_armature()
        if armature:
            armature_name = armature.name

    meshes = []
    
    for ob in get_objects():
            if ob is None:
                continue
            if ob.type != 'MESH':
                continue
                
            if mode == 0 or mode == 5: 
                if ob.parent:
                    if ob.parent.type == 'ARMATURE' and ob.parent.name == armature_name:
                        meshes.append(ob)
                    elif ob.parent.parent and ob.parent.parent.type == 'ARMATURE' and ob.parent.parent.name == armature_name:
                        meshes.append(ob) 

            elif mode == 1:
                if not ob.parent:
                    meshes.append(ob)

            elif mode == 2:
                meshes.append(ob)

            elif mode == 3:
                if ob.select_get():
                    meshes.append(ob)

    if visible_only:
        for mesh in meshes:
            if is_hidden(mesh):
                meshes.remove(mesh)

    # Check for broken meshes and delete them
    if check:
        current_active = context.view_layer.objects.active
        to_remove = []
        for mesh in meshes:
            selected = mesh.select_get()
            # print(mesh.name, mesh.users)
            set_active(mesh)

            if not context.view_layer.objects.active:
                to_remove.append(mesh)

            if not selected:
                select(mesh, False)

        for mesh in to_remove:
            print('DELETED CORRUPTED MESH:', mesh.name, mesh.users)
            meshes.remove(mesh)
            delete(mesh)

        if current_active:
            set_active(current_active)

    return meshes
def delete(obj):
    if obj.parent:
        for child in obj.children:
            child.parent = obj.parent

    objs = bpy.data.objects
    objs.remove(objs[obj.name], do_unlink=True)

if bpy.app.version >= (3, 2):
    # Passing in context_override as a positional-only argument is deprecated as of Blender 3.2, replaced with
    # Context.temp_override
    def op_override(operator, context_override: dict[str, Any], context: Optional[bpy.types.Context] = None,
                    execution_context: Optional[str] = None,
                    undo: Optional[bool] = None, **operator_args) -> set[str]:
        """Call an operator with a context override"""
        args = []
        if execution_context is not None:
            args.append(execution_context)
        if undo is not None:
            args.append(undo)

        if context is None:
            context = bpy.context
        with context.temp_override(**context_override):
            return operator(*args, **operator_args)
else:
    def op_override(operator, context_override: Dict[str, Any], context: Optional[bpy.types.Context] = None,
                    execution_context: Optional[str] = None,
                    undo: Optional[bool] = None, **operator_args) -> Set[str]:
        """Call an operator with a context override"""
        if context is not None:
            context_base = context.copy()
            context_base.update(context_override)
            context_override = context_base
        args = [context_override]
        if execution_context is not None:
            args.append(execution_context)
        if undo is not None:
            args.append(undo)

        return operator(*args, **operator_args)




class SavedData:
    __object_properties = {}
    __active_object = None

    def __init__(self):
        context = bpy.context
        # initialize as instance attributes rather than class attributes
        self.__object_properties = {}
        self.__active_object = None

        for obj in get_objects():
            mode = obj.mode
            selected = obj.select_get()
            hidden = is_hidden(obj)
            pose = None
            if obj.type == 'ARMATURE':
                pose = obj.data.pose_position
            self.__object_properties[obj.name] = [mode, selected, hidden, pose]

            active = context.view_layer.objects.active
            if active:
                self.__active_object = active.name

    def load(self, ignore=None, load_mode=True, load_select=True, load_hide=True, load_active=True, hide_only=False):
        if not ignore:
            ignore = []
        if hide_only:
            load_mode = False
            load_select = False
            load_active = False

        for obj_name, values in self.__object_properties.items():
            # print(obj_name, ignore)
            if obj_name in ignore:
                continue

            obj = get_objects().get(obj_name)
            if not obj:
                continue

            mode, selected, hidden, pose = values
            # print(obj_name, mode, selected, hidden)
            print(obj_name, pose)

            if load_mode and obj.mode != mode:
                set_active(obj, skip_sel=True)
                switch(mode, check_mode=False)
                if pose:
                    obj.data.pose_position = pose

            if load_select:
                select(obj, selected)
            if load_hide:
                hide(obj, hidden)

        # Set the active object
        if load_active and self.__active_object and get_objects().get(self.__active_object):
            context = bpy.context
            if self.__active_object not in ignore and self.__active_object != context.view_layer.objects.active:
                set_active(get_objects().get(self.__active_object), skip_sel=True)
