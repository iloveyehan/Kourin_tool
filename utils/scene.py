import bpy
def get_all_collections(collection):
    """递归获取所有集合"""
    all_collections = [collection]
    for child in collection.children:
        all_collections.extend(get_all_collections(child))
    return all_collections