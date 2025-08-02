import bpy

def get_blender_language():
    lang = bpy.context.preferences.view.language
    if lang == 'en_US':
        return 'en'
    elif lang == 'vi_VN':
        return 'vi'
    elif lang == 'zh_CN':
        return 'zh'        # 简体中文
    else:
        return 'zh'