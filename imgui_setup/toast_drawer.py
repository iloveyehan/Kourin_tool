# toast_drawer.py
# 用 Blender 5.0+ 的 gpu & blf API 在屏幕坐标上绘制“toast”提示（在鼠标位置出现，x 秒后渐变消失）。
# 扩展：支持每条 toast 指定文字大小（font_size）和文字颜色（text_color）。
#       颜色格式支持：
#         - 浮点 0..1 的序列或 numpy array (r,g,b) 或 (r,g,b,a)
#         - 整数 0..255 的序列 (r,g,b) 或 (r,g,b,a) —— 会自动除以 255
#         - numpy 数组（自动识别并归一化）
#
# 用法示例：
#   open_tip("完成", seconds=2.0, position=(mx,my), font_size=16, text_color=(78,200,170,255))
#   open_tip("完成", seconds=2.0, position=(mx,my), text_color=np.array((78,200,170,255))/255.0)
#
# 如果系统没有 numpy，整数 0..255 的序列仍然会被自动转换（除以 255）。

import time
import threading
from typing import Optional, Tuple, Iterable

import bpy
import gpu
from gpu_extras.batch import batch_for_shader
import blf

# 尝试导入 numpy（可选）
try:
    import numpy as np
except Exception:
    np = None

# 全局状态
_TOASTS = []  # list of dict: {"id": int, "text": str, "start": float, "end": float, "pos": (x,y), "duration": float, "font_size": int, "text_color": (r,g,b,a)}
_TOASTS_LOCK = threading.Lock()
_HANDLER = None  # draw handler reference

# 默认值（可按需修改）
_FONT_ID = 0
_FONT_SIZE = 14  # 默认文字大小（像素）
_PADDING_X = 10
_PADDING_Y = 6
_MAX_WIDTH = 420  # 最大宽度（像素）
_BG_COLOR = (0.05, 0.05, 0.05)  # 背景基础色 (r,g,b)
_TEXT_COLOR = (1.0, 1.0, 1.0, 1.0)  # 默认文本色 (r,g,b,a)

_next_toast_id = 1

# 重绘定时器状态
_REDRAW_TIMER_RUNNING = False


def _now():
    return time.time()


def _is_sequence(obj):
    return isinstance(obj, (list, tuple)) or (np is not None and isinstance(obj, np.ndarray))


def _normalize_color(c):
    """
    将用户传入的颜色规范化为 (r,g,b,a) 且每分量为 0..1 的 float。
    支持的输入形式：
      - None -> 返回默认 _TEXT_COLOR
      - (r,g,b) / (r,g,b,a) 的 tuple/list，分量可为 0..1 float 或 0..255 int
      - numpy array（会根据最大值判断是否需要除以255）
    规则：
      - 若检测到任一分量 > 1.0（例如 78 或 255），认为输入为 0..255 整数色值，统一除以 255。
      - 若是 numpy 数组且 dtype 是整数或最大值 > 1，则按 numpy 自动归一化。
    """
    if c is None:
        return _TEXT_COLOR
    # numpy array 直接处理（若 numpy 可用）
    try:
        if np is not None and isinstance(c, np.ndarray):
            arr = c.astype(float)
            if arr.size >= 3:
                maxv = float(arr.max())
                if maxv > 1.0:
                    arr = arr / 255.0
                # ensure length >=4
                if arr.size == 3:
                    r, g, b = arr.tolist()
                    a = 1.0
                else:
                    r, g, b, a = arr[:4].tolist()
                return (float(r), float(g), float(b), float(a))
    except Exception:
        pass

    # 可迭代序列（list/tuple）
    if _is_sequence(c):
        try:
            seq = [float(x) for x in c]
        except Exception:
            return _TEXT_COLOR
        if len(seq) < 3:
            return _TEXT_COLOR
        # 如果任一分量大于 1.0，则视为 0..255，则除以 255
        if any(x > 1.0 for x in seq):
            seq = [x / 255.0 for x in seq]
        # 填充 alpha
        if len(seq) == 3:
            r, g, b = seq
            a = 1.0
        else:
            r, g, b, a = seq[0], seq[1], seq[2], seq[3]
        # clamp到0..1
        def clamp(v):
            if v < 0.0:
                return 0.0
            if v > 1.0:
                return 1.0
            return v
        return (clamp(r), clamp(g), clamp(b), clamp(a))

    # 非序列（可能是单个数），不支持，回退
    return _TEXT_COLOR


def open_tip(text: str,
             seconds: float = 2.0,
             position: Optional[Tuple[int, int]] = None,
             font_size: Optional[float] = None,
             text_color: Optional[Iterable] = None):
    """
    添加一个提示到队列并确保视图被刷新以立即显示提示。

    参数：
      - text: 要显示的文本（会自动转 str）
      - seconds: 显示时长（秒）
      - position: (x, y) 屏幕/区域像素坐标（通常使用 event.mouse_region_x, event.mouse_region_y）
      - font_size: 可选，文字大小（px），不传则使用模块默认 _FONT_SIZE
      - text_color: 可选，(r,g,b) 或 (r,g,b,a)（支持 0..1 float 或 0..255 int，或 numpy array）
    """
    global _next_toast_id
    if seconds <= 0:
        seconds = 2.0
    now = _now()
    pos = position if position is not None else _guess_position()
    fs = float(font_size) if font_size is not None else _FONT_SIZE
    tc = _normalize_color(text_color)

    with _TOASTS_LOCK:
        tid = _next_toast_id
        _next_toast_id += 1
        _TOASTS.append({
            "id": tid,
            "text": str(text),
            "start": now,
            "end": now + float(seconds),
            "duration": float(seconds),
            "pos": (float(pos[0]), float(pos[1])),
            "font_size": fs,
            "text_color": tc,
        })

    try:
        _tag_redraw_view3d_windows_once()
    except Exception:
        pass
    try:
        _ensure_redraw_timer()
    except Exception:
        pass


def _guess_position():
    try:
        region = bpy.context.region
        return (region.width / 2.0, region.height / 2.0)
    except Exception:
        pass
    try:
        ctx = bpy.context
        for a in ctx.screen.areas:
            if a.type == 'VIEW_3D':
                for r in a.regions:
                    if r.type == 'WINDOW':
                        return (r.width / 2.0, r.height / 2.0)
    except Exception:
        pass
    return (300.0, 300.0)


def _cleanup_expired(now):
    with _TOASTS_LOCK:
        _TOASTS[:] = [t for t in _TOASTS if t["end"] > now]


def _draw_rect(x, y, w, h, color):
    shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
    verts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    batch = batch_for_shader(shader, 'TRI_FAN', {"pos": verts})
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)


def _blf_size(size, dpi_hint=72):
    try:
        blf.size(_FONT_ID, int(size), int(dpi_hint))
        return
    except TypeError:
        try:
            blf.size(_FONT_ID, int(size))
            return
        except Exception:
            return
    except Exception:
        return


def _draw_text(x, y, text, color, size=_FONT_SIZE):
    try:
        _blf_size(size)
    except Exception:
        pass

    try:
        blf.position(_FONT_ID, x, y, 0)
    except Exception:
        try:
            blf.position(_FONT_ID, x, y)
        except Exception:
            pass

    try:
        blf.color(_FONT_ID, color[0], color[1], color[2], color[3])
    except TypeError:
        try:
            blf.color(_FONT_ID, color[0], color[1], color[2])
        except Exception:
            pass
    except Exception:
        pass

    try:
        blf.draw(_FONT_ID, text)
    except Exception:
        pass


def _measure_text(text, size=_FONT_SIZE):
    try:
        _blf_size(size)
    except Exception:
        pass
    try:
        dims = blf.dimensions(_FONT_ID, text)
        return float(dims[0]), float(dims[1])
    except Exception:
        return max(80.0, len(text) * (size * 0.6)), float(size)


def draw_callback_px():
    now = _now()
    _cleanup_expired(now)
    with _TOASTS_LOCK:
        to_draw = list(_TOASTS)

    if not to_draw:
        return

    for t in to_draw:
        text = t["text"]
        end = t["end"]
        duration = max(0.0001, t["duration"])
        pos_x, pos_y = t["pos"]
        font_size = t.get("font_size", _FONT_SIZE)
        base_text_color = t.get("text_color", _TEXT_COLOR)

        remaining = max(0.0, end - now)
        alpha = min(1.0, remaining / duration)

        txt_w, txt_h = _measure_text(text, size=font_size)
        box_w = min(_MAX_WIDTH, txt_w + _PADDING_X * 2)
        box_h = txt_h + _PADDING_Y * 2

        x = pos_x
        y = pos_y

        try:
            area = bpy.context.area
            region = bpy.context.region
            region_w = region.width
            region_h = region.height
            if x + box_w > region_w:
                x = max(4, region_w - box_w - 4)
            if y + box_h > region_h:
                y = max(4, region_h - box_h - 4)
        except Exception:
            pass

        bg_color = (_BG_COLOR[0], _BG_COLOR[1], _BG_COLOR[2], 0.85 * alpha)
        btc = _normalize_color(base_text_color)
        txt_color = (btc[0], btc[1], btc[2], btc[3] * alpha)

        try:
            _draw_rect(x, y, box_w, box_h, bg_color)
        except Exception:
            pass

        tx = x + _PADDING_X
        ty = y + _PADDING_Y

        try:
            outline_color = (0.0, 0.0, 0.0, min(0.9, txt_color[3] * 1.0))
            _draw_text(tx + 1, ty + 1, text, outline_color, size=font_size)
        except Exception:
            pass
        try:
            _draw_text(tx, ty, text, txt_color, size=font_size)
        except Exception:
            pass


def _tag_redraw_view3d_windows_once():
    try:
        wm = bpy.context.window_manager
        for win in wm.windows:
            screen = win.screen
            if not screen:
                continue
            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    try:
                        area.tag_redraw()
                    except Exception:
                        pass
    except Exception:
        pass


def _redraw_timer():
    global _REDRAW_TIMER_RUNNING
    now = _now()
    with _TOASTS_LOCK:
        has = len(_TOASTS) > 0

    if has:
        try:
            wm = bpy.context.window_manager
            for win in wm.windows:
                screen = win.screen
                if not screen:
                    continue
                for area in screen.areas:
                    if area.type == 'VIEW_3D':
                        try:
                            area.tag_redraw()
                        except Exception:
                            pass
        except Exception:
            pass
        _REDRAW_TIMER_RUNNING = True
        return 0.05
    else:
        _REDRAW_TIMER_RUNNING = False
        return None


def _ensure_redraw_timer():
    global _REDRAW_TIMER_RUNNING
    if _REDRAW_TIMER_RUNNING:
        return
    try:
        bpy.app.timers.register(_redraw_timer, first_interval=0.01)
        _REDRAW_TIMER_RUNNING = True
    except Exception:
        _REDRAW_TIMER_RUNNING = False


def register_draw_handler():
    global _HANDLER
    if _HANDLER is not None:
        return
    try:
        _HANDLER = bpy.types.SpaceView3D.draw_handler_add(draw_callback_px, (), 'WINDOW', 'POST_PIXEL')
    except Exception:
        try:
            _HANDLER = bpy.types.SpaceView3D.draw_handler_add(draw_callback_px, (), 'WINDOW', 'POST_PIXEL')
        except Exception:
            _HANDLER = None


def unregister_draw_handler():
    global _HANDLER
    if _HANDLER is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_HANDLER, 'WINDOW')
        except Exception:
            try:
                bpy.types.SpaceView3D.draw_handler_remove(_HANDLER, 'WINDOW')
            except Exception:
                pass
        _HANDLER = None