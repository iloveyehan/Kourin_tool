import bpy
from .registration import get_prefs, get_addon
import blf
def draw_label(context, title='', coords=None, offset=0, center=True, size=12, color=(1, 1, 1), alpha=1):
    if not coords:
        region = context.region
        width = region.width / 2
        height = region.height / 2
    else:
        width, height = coords

    scale = context.preferences.system.ui_scale * get_prefs().modal_hud_scale

    font = 1
    fontsize = int(size * scale)

    blf.size(font, fontsize)
    blf.color(font, *color, alpha)

    if center:
        dims = blf.dimensions(font, title)
        blf.position(font, width - (dims[0] / 2), height - (offset * scale), 1)

    else:
        blf.position(font, width, height - (offset * scale), 1)

    blf.draw(font, title)

    return blf.dimensions(font, title)

def draw_fading_label(context, text='', x=100, y=100, gap=18, center=True, size=12, color=(1, 1, 1), alpha=1, move_y=0, time=5, delay=1, cancel=''):
    scale = context.preferences.system.ui_scale * get_prefs().modal_hud_scale

    # if x is None:
        # x = (context.region.width / 2)

    if isinstance(text, list):

        coords = (x, y + gap * (len(text) - 1) * scale)

        for idx, t in enumerate(text):
            line_coords = (coords[0], coords[1] - (idx * gap * scale))
            line_color = color if isinstance(color, tuple) else color[idx if idx < len(color) else len(color) - 1]
            line_alpha = alpha if (isinstance(alpha, int) or isinstance(alpha, float)) else alpha[idx if idx < len(alpha) else len(alpha) - 1]
            line_move = int(move_y + (idx * gap)) if move_y > 0 else 0
            line_time = time + idx * delay
            
            bpy.ops.ops_info.draw_label(text=t, coords=line_coords, center=center, size=size, color=line_color, alpha=line_alpha, move_y=line_move, time=line_time, cancel=cancel)

    else:
        coords = (x, y)

        bpy.ops.ops_info.draw_label(text=text, coords=coords, center=center, size=size, color=color, alpha=alpha, move_y=move_y, time=time, cancel=cancel)
