
import ctypes
import ctypes.wintypes as wintypes
import win32con, win32gui
from imgui_bundle import imgui

WNDPROC = ctypes.WINFUNCTYPE(
    ctypes.c_long, ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p
)
def message_to_string(msg_type):
    # 遍历 win32con 中的所有常量，查找与 msg_type 匹配的常量名
    for name, value in vars(win32con).items():
        if value == msg_type and name.startswith("WM_"):
            if name in ['WM_GETICON','WM_USER','WM_MOUSEWHEEL','WM_LBUTTONDOWN','WM_MOUSEHOVER','WM_CAPTURECHANGED','WM_LBUTTONUP','WM_NCHITTEST','WM_IME_NOTIFY','WM_ACTIVATEAPP','WM_IME_SETCONTEXT','WM_NCACTIVATE','WM_KILLFOCUS','WM_ACTIVATE','WM_SETCURSOR','WM_GETOBJECT','WM_MOUSEFIRST','WM_NCMOUSEMOVE','WM_MOUSELEAVE']:
                return
            return name
    return f"Unknown message: {msg_type}"
def _wndproc(hwnd, msg, wParam, lParam):
    # 有些时候 lParam 或 wParam 可能是 None，需要安全转换
    try:
        hwnd = ctypes.cast(hwnd, ctypes.c_void_p).value if hwnd else 0
        msg = int(msg) if msg is not None else 0
        wParam = int(wParam) if wParam is not None else 0
        lParam = int(lParam) if lParam is not None else 0
    except Exception as e:
        print("参数转换异常:", e)
        return 0
    # if msg == win32con.WM_IME_COMPOSITION:
    if imgui.get_io().want_text_input:
        if msg == win32con.WM_IME_COMPOSITION:
            GCS_RESULTSTR = 0x0800
            hImc = ctypes.windll.imm32.ImmGetContext(hwnd)
            size = ctypes.windll.imm32.ImmGetCompositionStringW(hImc, GCS_RESULTSTR, None, 0)
            if size > 0:
                buf = ctypes.create_unicode_buffer(size // 2)
                ctypes.windll.imm32.ImmGetCompositionStringW(hImc, GCS_RESULTSTR, buf, size)
                text = buf.value
                print("IME 最终文本：", text)
                # if imgui.get_io().want_text_input:
                for ch in text:
                    imgui.get_io().add_input_character(ord(ch))
            ctypes.windll.imm32.ImmReleaseContext(hwnd, hImc)
    # return 0
    # print(f"hwnd: {hwnd}, msg: {msg}, wParam: {wParam}, lParam: {lParam}")
    if message_to_string(msg) is not None:
        print(message_to_string(msg))
    # if msg == win32con.WM_MOUSEMOVE:
    #     x = lParam & 0xFFFF
    #     y = (lParam >> 16) & 0xFFFF
        # print(f"Mouse moved to: ({x}, {y})")
    # print(f"WM_IME_CHAR: {win32con.WM_IME_CHAR}")
    if msg == win32con.WM_IME_CHAR:
        print('sent to imgui')
        imgui.get_io().add_input_character(wParam)
        return 0

    return _old_wndproc(hwnd, msg, wParam, lParam)


_wndproc_func = WNDPROC(_wndproc)

SetWindowLongPtr = (
    ctypes.windll.user32.SetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p) == 8
    else ctypes.windll.user32.SetWindowLongW
)
SetWindowLongPtr.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
SetWindowLongPtr.restype = ctypes.c_void_p

hwnd1 = win32gui.FindWindow("GHOST_WindowClass", None)
if not hwnd1:
    raise RuntimeError("Cannot find target window")

_old_wndproc_ptr = SetWindowLongPtr(hwnd1, win32con.GWL_WNDPROC, _wndproc_func)
if not _old_wndproc_ptr:
    raise RuntimeError("Failed to set window procedure")

# 转成可调用的旧回调函数
OldWndProcType = ctypes.WINFUNCTYPE(
    ctypes.c_long, ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p
)
_old_wndproc = OldWndProcType(_old_wndproc_ptr)





import ctypes
from ctypes import wintypes
import win32con, win32gui, win32api
from imgui_bundle import imgui

class BlenderImeHook:
    def __init__(self):
        # 1）找到 Blender 的主窗口
        self.hwnd = win32gui.FindWindow("GHOST_WindowClass", None)
        if not self.hwnd:
            raise RuntimeError("找不到 Blender 主窗口 HWND")

        # 2）准备 WNDPROC 类型
        WNDPROC = ctypes.WINFUNCTYPE(
            ctypes.c_long,
            ctypes.c_void_p,  # hwnd
            ctypes.c_uint,    # msg
            ctypes.c_void_p,  # wParam
            ctypes.c_void_p   # lParam
        )
        self._wndproc_func = WNDPROC(self._wndproc)

        # 3）替换窗口过程
        SetWindowLongPtr = (
            ctypes.windll.user32.SetWindowLongPtrW
            if ctypes.sizeof(ctypes.c_void_p) == 8
            else ctypes.windll.user32.SetWindowLongW
        )
        SetWindowLongPtr.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
        SetWindowLongPtr.restype = ctypes.c_void_p

        # 保存旧的 WNDPROC pointer 值
        self._old_wndproc_ptr = SetWindowLongPtr(
            self.hwnd, win32con.GWL_WNDPROC, self._wndproc_func
        )
        if not self._old_wndproc_ptr:
            raise RuntimeError("Hook WNDPROC 失败")

        # 把旧指针转换为可调用
        self._old_wndproc = WNDPROC(self._old_wndproc_ptr)

    def shutdown(self):
        # 卸载时还原
        SetWindowLongPtr = (
            ctypes.windll.user32.SetWindowLongPtrW
            if ctypes.sizeof(ctypes.c_void_p) == 8
            else ctypes.windll.user32.SetWindowLongW
        )
        SetWindowLongPtr(self.hwnd, win32con.GWL_WNDPROC, self._old_wndproc_ptr)

    def _wndproc(self, hwnd, msg, wParam, lParam):
        # 先做安全转换
        hwnd = ctypes.cast(hwnd, ctypes.c_void_p).value or 0
        msg = int(msg) if msg is not None else 0

        # 只拦截合成结束消息
        if imgui.get_io().want_text_input:
            if msg == win32con.WM_IME_COMPOSITION:
                # GCS_RESULTSTR = 0x0800 拿到“已敲定”文字
                GCS_RESULTSTR = 0x0800
                hImc = ctypes.windll.imm32.ImmGetContext(hwnd)
                size = ctypes.windll.imm32.ImmGetCompositionStringW(
                    hImc, GCS_RESULTSTR, None, 0
                )
                if size > 0:
                    buf = ctypes.create_unicode_buffer(size // 2)
                    ctypes.windll.imm32.ImmGetCompositionStringW(
                        hImc, GCS_RESULTSTR, buf, size
                    )
                    text = buf.value
                    # 把每个字符推给 ImGui
                
                    for ch in text:
                        imgui.get_io().add_input_character(ord(ch))
                ctypes.windll.imm32.ImmReleaseContext(hwnd, hImc)
                # return 0  # 拦截

        # 其它消息原样转发
        return self._old_wndproc(hwnd, msg, wParam, lParam)
BlenderImeHook()