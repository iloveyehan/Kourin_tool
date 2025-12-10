import bpy
from imgui_bundle import imgui
import ctypes

from .imgui_global import GlobalImgui

def on_text_edit(data):
    g = GlobalImgui.get()

    try:
        s = int(data.selection_start)
        e = int(data.selection_end)
    except Exception:
        s = 0; e = 0

    # ensure buf is str
    buf = data.buf
    if isinstance(buf, (bytes, bytearray)):
        try:
            buf = buf.decode('utf-8', errors='replace')
        except Exception:
            buf = str(buf)

    # selected text (safe)
    if e > s:
        sel_text = buf[s:e]
    elif s > e:
        sel_text = buf[e:s]
    else:
        sel_text = ''

    # helper: safe clipboard write/read
    def clipboard_set(text):
        try:
            bpy.context.window_manager.clipboard = text
        except Exception:
            pass

    def clipboard_get():
        try:
            return bpy.context.window_manager.clipboard
        except Exception:
            return ''

    try:
        if getattr(g, "ctrl_c", False):
            clipboard_set(sel_text)
            g.ctrl_c = False

        if getattr(g, "ctrl_x", False):
            clipboard_set(sel_text)
            # delete selected region
            if e > s:
                data.delete_chars(s, e - s)
            elif s > e:
                data.delete_chars(e, s - e)
            g.ctrl_x = False

        if getattr(g, "ctrl_v", False):
            paste_text = clipboard_get() or ''
            if e > s:
                data.delete_chars(s, e - s)
                data.insert_chars(s, paste_text)
            elif s == e:
                data.insert_chars(s, paste_text)
            else:
                data.delete_chars(e, s - e)
                data.insert_chars(e, paste_text)
            g.ctrl_v = False

        if getattr(g, "ctrl_a", False):
            data.selection_start = 0
            data.selection_end = data.buf_text_len
            data.cursor_pos = data.buf_text_len
            g.ctrl_a = False

    except Exception:
        # avoid bubbling exceptions to ImGui / Blender
        import traceback; traceback.print_exc()

    # final sync
    try:
        g.text_input_buf = data.buf
    except Exception:
        pass

    return 0
