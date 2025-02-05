import bpy
import sys
import ctypes
import platform
import weakref  # [!] 新增关键模块
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PySide6.QtGui import QWindow, QGuiApplication
from PySide6.QtCore import Qt, QTimer,QPoint,Signal
from ctypes import wintypes  # [!] 关键修复

# 调试模式开关
DEBUG_MODE = True


def debug_print(*args):
    if DEBUG_MODE:
        print("[DEBUG]", *args)


def get_blender_hwnd():
    system = platform.system()
    if system == "Windows":
        user32 = ctypes.windll.user32
        hwnd = user32.FindWindowW("GHOST_WindowClass", None)
        return hwnd if hwnd else None

    elif system == "Linux":
        app = QGuiApplication.instance()
        if not app:
            debug_print("未找到QGuiApplication实例")
            return None

        windows = app.allWindows()
        debug_print("找到的窗口数量:", len(windows))

        for window in windows:
            title = window.title()
            debug_print("窗口标题:", title)
            if title.startswith("Blender"):
                win_id = int(window.winId())
                debug_print("匹配到Blender窗口ID:", win_id)
                return win_id
        return None

    else:
        debug_print("暂不支持的系统:", system)
        return None


class EmbeddedQtWidget(QWidget):
    frame_changed_signal = Signal(int)  # 新增信号
    def __init__(self, parent_hwnd):
        super().__init__()
        # 连接信号到槽
        self.frame_changed_signal.connect(self.update_frame_label)
        # Windows DPI处理
        if platform.system() == "Windows":
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
            self.setAttribute(Qt.WA_NativeWindow, True)

        # 强制创建窗口句柄
        self.setAttribute(Qt.WA_DontShowOnScreen, True)
        self.show()
        self.hide()
        self.setAttribute(Qt.WA_DontShowOnScreen, False)

        # 设置父窗口
        blender_window = QWindow.fromWinId(parent_hwnd)
        if blender_window.screen() is None:
            raise RuntimeError("无效的父窗口")
        self.windowHandle().setParent(blender_window)

        # [!] 关键视觉设置
        self.setStyleSheet("""
            QWidget {
                background: #FF0000;
                border: 5px solid #00FF00;
            }
            QLabel {
                color: #FFFFFF;
                font-size: 24px;
                font-weight: bold;
            }
        """)
        self.setWindowOpacity(0.9)
        self.setGeometry(50, 50, 300, 200)

        # 创建帧号标签（修改后的版本）
        self.frame_label = QLabel(f'current frame {bpy.context.scene.frame_current}', self)
        self.frame_label.setAlignment(Qt.AlignCenter)
        layout = QVBoxLayout()
        layout.addWidget(self.frame_label)
        self.setLayout(layout)

        # 新增帧号更新定时器
        self.frame_timer = QTimer(self)
        self.frame_timer.timeout.connect(self.update_frame_label)
        self.frame_timer.start(100)  # 每100毫秒检查一次

        # 注册Blender回调
        self._register_blender_handlers()

        # [!] Windows强制显示操作
        if platform.system() == "Windows":
            hwnd = int(self.winId())
            debug_print(f"Windows窗口句柄: {hwnd}")

            # 设置窗口层级
            ctypes.windll.user32.SetWindowPos(
                hwnd, -1,  # HWND_TOPMOST
                50, 50, 300, 200,
                0x40 | 0x10  # SWP_SHOWWINDOW|SWP_NOACTIVATE
            )

            # 强制刷新
            ctypes.windll.user32.UpdateWindow(hwnd)
            ctypes.windll.user32.FlashWindow(hwnd, True)

        self.show()
        debug_print("窗口显示命令执行完毕")
        # 新增拖动相关变量
        self.dragging = False
        self.drag_start_position = self.pos()
        self.drag_mouse_start_pos = QPoint()

        # [!] 允许窗口接收鼠标事件
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setMouseTracking(True)

    # ========== 新增鼠标事件处理 ==========
    def mousePressEvent(self, event):
        """鼠标按下时开始拖动"""
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_mouse_start_pos = event.globalPosition().toPoint()
            self.drag_start_position = self.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()

    def mouseMoveEvent(self, event):
        """鼠标移动时更新窗口位置"""
        if self.dragging and event.buttons() & Qt.LeftButton:
            # 计算位移差值
            delta = event.globalPosition().toPoint() - self.drag_mouse_start_pos
            new_pos = self.drag_start_position + delta
            self.move(new_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        """鼠标释放时结束拖动"""
        if event.button() == Qt.LeftButton:
            self.dragging = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()

    def _register_blender_handlers(self):
        """注册Blender帧变化回调"""
        # 先移除旧回调避免重复
        if hasattr(bpy.app.handlers, 'frame_change_pre'):
            try:
                bpy.app.handlers.frame_change_pre.remove(self._on_frame_changed)
            except ValueError:
                pass

        # 添加新回调
        bpy.app.handlers.frame_change_pre.append(self._on_frame_changed)

    def _on_frame_changed(self, scene):
        """Blender帧变化回调函数"""
        # 通过Qt信号机制安全更新UI
        self.frame_changed_signal.emit(scene.frame_current)

    def update_frame_label(self, frame=None):
        """更新帧号标签的通用方法"""
        current_frame = bpy.context.scene.frame_current
        if frame is not None:
            current_frame = frame
        if str(current_frame) != self.frame_label.text():
            self.frame_label.setText(f'current frame {current_frame}')

    def __del__(self):
        """析构时清理资源"""
        if hasattr(bpy.app.handlers, 'frame_change_pre'):
            try:
                bpy.app.handlers.frame_change_pre.remove(self._on_frame_changed)
            except ValueError:
                pass
        if self.frame_timer.isActive():
            self.frame_timer.stop()
class QtEmbedPanel(bpy.types.Panel):
    bl_label = "嵌入式Qt面板"
    bl_idname = "OBJECT_PT_qt_embed"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = '工具'

    def draw(self, context):
        layout = self.layout
        layout.operator("qt.color_selector", text="显示Qt窗口")


class EmbedQtOperator(bpy.types.Operator):
    bl_idname = "qt.color_selector"
    bl_label = "嵌入Qt窗口"
    _instance = None  # [!] 类级实例引用

    def __init__(self):
        super().__init__()
        self._widget_ref = None  # [!] 使用弱引用

    def execute(self, context):
        EmbedQtOperator._instance = weakref.ref(self)
        # [!] Windows DPI感知
        if platform.system() == "Windows":
            ctypes.windll.shcore.SetProcessDpiAwareness(2)

        parent_hwnd = get_blender_hwnd()
        if not parent_hwnd:
            self.report({'ERROR'}, "无法获取窗口句柄")
            return {'CANCELLED'}

        # 初始化Qt应用
        if not QApplication.instance():
            debug_print("创建新的QApplication实例")
            bpy._qt_app = QApplication(sys.argv)
        else:
            debug_print("使用现有QApplication实例")
            bpy._qt_app = QApplication.instance()

        # 创建嵌入式窗口
        try:
            bpy._embedded_qt = EmbeddedQtWidget(parent_hwnd)
            # [!] 修改回调机制
            QTimer.singleShot(500, self._safe_force_redraw)
        except Exception as e:
            self.report({'ERROR'}, str(e))

        return {'FINISHED'}

    def _safe_force_redraw(self):
        """安全的延迟重绘方法"""
        # [!] 通过类级引用获取有效实例
        instance = EmbedQtOperator._instance() if EmbedQtOperator._instance else None

        if instance and hasattr(bpy, '_embedded_qt'):
            try:
                # [!] 使用Blender主线程操作
                bpy.app.timers.register(
                    lambda: self._thread_safe_redraw(),
                    first_interval=0.01
                )
            except ReferenceError:
                debug_print("操作符实例已释放")

    def _thread_safe_redraw(self):
        """Blender主线程安全的重绘操作"""
        if hasattr(bpy, '_embedded_qt'):
            try:
                bpy._embedded_qt.update()
                bpy._embedded_qt.repaint()
                debug_print("安全重绘完成")
            except ReferenceError:
                debug_print("窗口对象已释放")
        return None  # 单次执行

    def __del__(self):
        """析构时清理资源"""
        debug_print("操作符实例被销毁")
        if hasattr(bpy, '_embedded_qt'):
            bpy._embedded_qt.deleteLater()


def register():
    debug_print("注册面板和操作符")
    bpy.utils.register_class(QtEmbedPanel)
    bpy.utils.register_class(EmbedQtOperator)


def unregister():
    debug_print("注销面板和操作符")
    bpy.utils.unregister_class(QtEmbedPanel)
    bpy.utils.unregister_class(EmbedQtOperator)
    if hasattr(bpy, '_embedded_qt'):
        debug_print("清理Qt窗口")
        bpy._embedded_qt.deleteLater()
    if hasattr(bpy, '_qt_app'):
        debug_print("关闭Qt应用")
        bpy._qt_app.quit()


if __name__ == "__main__":
    register()