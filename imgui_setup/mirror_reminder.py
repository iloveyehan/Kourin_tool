import time
from imgui_bundle import imgui
from imgui_bundle import ImVec2

def open_mirror_tip(str,p_open_flag=[True]):
    from .imgui_global import GlobalImgui
    io = imgui.get_io()
    window_flags = (
        imgui.WindowFlags_.no_decoration |
        imgui.WindowFlags_.always_auto_resize |
        imgui.WindowFlags_.no_saved_settings |
        imgui.WindowFlags_.no_focus_on_appearing |
        imgui.WindowFlags_.no_nav
    )
    if GlobalImgui.get().show_mirror_reminder_window:
            # 如果已经过去 4 秒
            if time.time() - GlobalImgui.get().mirror_reminder_window_open_time >= 4.0:
                GlobalImgui.get().show_mirror_reminder_window = False
            else:
                if imgui.begin("##Example: Simple overlay", p_open_flag[0], window_flags):
                    dl = imgui.get_foreground_draw_list()
                    # dl.add_text(GlobalImgui().get().loaded_font, 30.0, (io.mouse_pos.x, io.mouse_pos.y), 0xFFFFFFFF, f"  {str}")
                    dl.add_text(io.font_default, 30.0, (io.mouse_pos.x, io.mouse_pos.y), 0xFFFFFFFF, f"  {str}")
                    imgui.end()

def open_tip(btn,str,p_open_flag=[True]):
    from .imgui_global import GlobalImgui
    io = imgui.get_io()
    window_flags = (
        imgui.WindowFlags_.no_decoration |
        imgui.WindowFlags_.always_auto_resize |
        imgui.WindowFlags_.no_saved_settings |
        imgui.WindowFlags_.no_focus_on_appearing |
        imgui.WindowFlags_.no_nav
    )
    if getattr(GlobalImgui.get(), f"{btn}", False):
    # if getattr(GlobalImgui.get(), f"{btn.split('##')[-1]}", False):
            # 如果已经过去 4 秒
            if time.time() - getattr(GlobalImgui.get(), f"{btn}_time", 0) >= 4.0:
            # if time.time() - getattr(GlobalImgui.get(), f"{btn.split('##')[-1]}_time", 0) >= 4.0:
                setattr(GlobalImgui.get(), f"{btn}", False)
            else:
                if imgui.begin(f"##{btn}1", p_open_flag[0], window_flags):
                    dl = imgui.get_foreground_draw_list()
                    dl.add_text(io.font_default, 30.0, (io.mouse_pos.x, io.mouse_pos.y-60), 0xFFFFFFFF, f"  {str}")
                    # dl.add_text(GlobalImgui().get().loaded_font, 30.0, (io.mouse_pos.x, io.mouse_pos.y-60), 0xFFFFFFFF, f"  {str}")
                    imgui.end()
