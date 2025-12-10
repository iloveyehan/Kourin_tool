import ctypes
import ctypes.wintypes as wintypes
# import win32con, win32gui
import win32con
from imgui_bundle import imgui
import atexit # 用于在程序退出时进行清理

# 全局变量，用于确保回调函数和原始窗口过程的持久性
# 这样可以防止它们被Python垃圾回收器过早回收
_global_wndproc_func = None
_global_old_wndproc = None
_global_hwnd = None
_global_old_wndproc=None
_global_old_wndproc_ptr=None
# 定义窗口过程的函数签名
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
    """新的窗口过程函数，用于处理Windows消息"""
    try:
        # 安全地将参数转换为整数，以防None值
        hwnd_val = ctypes.cast(hwnd, ctypes.c_void_p).value if hwnd else 0
        msg_val = int(msg) if msg is not None else 0
        wParam_val = int(wParam) if wParam is not None else 0
        lParam_val = int(lParam) if lParam is not None else 0
    except Exception as e:
        print("参数转换异常:", e)
        # 如果参数转换失败，直接调用原始过程或返回0
        if _global_old_wndproc:
            return _global_old_wndproc(hwnd, msg, wParam, lParam)
        return 0

    # 仅当imgui需要文本输入时才处理IME消息
    if imgui.get_io().want_text_input:
        # imgui.set_keyboard_focus_here()
        if msg_val == win32con.WM_IME_COMPOSITION:
            # print('句柄',win32gui.FindWindow("GHOST_WindowClass", None))
            GCS_RESULTSTR = 0x0800
            
            hImc = ctypes.windll.imm32.ImmGetContext(hwnd_val)
            ctypes.windll.imm32.ImmSetOpenStatus(hImc, True)
            ctypes.windll.imm32.ImmAssociateContext(hwnd, hImc)
            if hImc: # 确保获取到有效的IME上下文
                # 获取最终的组合字符串
                size = ctypes.windll.imm32.ImmGetCompositionStringW(hImc, GCS_RESULTSTR, None, 0)
                if size > 0:
                    # 创建Unicode缓冲区，注意为null终止符预留空间
                    buf = ctypes.create_unicode_buffer(size // 2 + 1)
                    ctypes.windll.imm32.ImmGetCompositionStringW(hImc, GCS_RESULTSTR, buf, size)
                    text = buf.value
                    # print("IME 最终文本：", text)
                    # 将字符添加到imgui的输入队列
                    for ch in text:
                        imgui.get_io().add_input_character(ord(ch))
                ctypes.windll.imm32.ImmReleaseContext(hwnd_val, hImc) # 释放IME上下文
            return 0 # 表示已处理此消息

        # if msg_val == win32con.WM_IME_CHAR:
        #     print('sent to imgui')
        #     imgui.get_io().add_input_character(wParam_val)
        #     return 0 # 表示已处理此消息

    # 打印消息名称（用于调试）
    # if message_to_string(msg_val) is not None:
    #     print(message_to_string(msg_val))

    # 调用原始的窗口过程，将消息传递下去
    # 必须使用全局变量 _global_old_wndproc
    if _global_old_wndproc:
        return _global_old_wndproc(hwnd, msg, wParam, lParam)
    return 0 # 如果原始过程未设置，则返回0

def restore_wndproc():
    """在程序退出时恢复原始的窗口过程，进行清理"""
    global _global_wndproc_func, _global_old_wndproc, _global_hwnd
    if _global_hwnd and _global_old_wndproc:
        # 根据系统位数选择正确的SetWindowLongPtr函数
        SetWindowLongPtr = (
            ctypes.windll.user32.SetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p) == 8
            else ctypes.windll.user32.SetWindowLongW
        )
        # 恢复原始的窗口过程
        SetWindowLongPtr(_global_hwnd, win32con.GWL_WNDPROC, _global_old_wndproc)
        print("原始 WNDPROC 已恢复。")
        # 清除全局引用，允许Python垃圾回收这些对象
        _global_wndproc_func = None
        _global_old_wndproc = None
        _global_hwnd = None
        _global_old_wndproc=None
        _global_old_wndproc_ptr=None

# 注册清理函数，确保在Python解释器关闭时调用
# 这对于防止Blender退出时崩溃至关重要 [4, 5]
atexit.register(restore_wndproc)

# --- 主执行部分 ---
# 根据系统位数选择正确的SetWindowLongPtr函数
def hook_ime():
    global _global_wndproc_func, _global_old_wndproc, _global_hwnd,_global_old_wndproc_ptr
    SetWindowLongPtr = (
        ctypes.windll.user32.SetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p) == 8
        else ctypes.windll.user32.SetWindowLongW
    )
    SetWindowLongPtr.argtypes =[wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
    SetWindowLongPtr.restype = ctypes.c_void_p

    # 查找Blender的主窗口句柄
    # hwnd1 = win32gui.FindWindow("GHOST_WindowClass", None)
    hwnd1 = ctypes.windll.user32.FindWindowW("GHOST_WindowClass", None)
    if not hwnd1:
        raise RuntimeError("无法找到目标窗口")

    # 将窗口句柄存储为全局变量，以便在清理时使用
    _global_hwnd = hwnd1

    # 创建C可调用的函数指针，并将其存储在全局变量中，防止被垃圾回收 [2, 3]
    _global_wndproc_func = WNDPROC(_wndproc)

    # 设置新的窗口过程，并获取原始的窗口过程指针
    _global_old_wndproc_ptr = SetWindowLongPtr(hwnd1, win32con.GWL_WNDPROC, _global_wndproc_func)
    if not _global_old_wndproc_ptr:
        raise RuntimeError("设置窗口过程失败")

    # 将原始的窗口过程指针转换为可调用的Python函数，并存储在全局变量中
    OldWndProcType = ctypes.WINFUNCTYPE(
        ctypes.c_long, ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p
    )
    _global_old_wndproc = OldWndProcType(_global_old_wndproc_ptr)

    print("窗口过程已成功挂钩。")
