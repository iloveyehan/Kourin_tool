import ctypes
import platform
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PySide6.QtGui import QWindow, QGuiApplication
from PySide6.QtCore import Qt, QTimer,QPoint,Signal
import bpy

from ..utils.color_selector import debug_print

DEBUG_MODE=1
class EmbeddedQtWidget(QWidget):
    frame_changed_signal = Signal(int)  # 新增信号
    def __init__(self, parent_hwnd):
        super().__init__()
        # 连接信号到槽
        self.frame_changed_signal.connect(self.update_frame_label)
        # Windows DPI处理
        if platform.system() == "Windows":
            # ctypes.windll.shcore.SetProcessDpiAwareness(2)
            self.setAttribute(Qt.WA_NativeWindow, True)

        # 强制创建窗口句柄
        # self.setAttribute(Qt.WA_DontShowOnScreen, True)
        # self.show()
        # self.hide()
        # self.setAttribute(Qt.WA_DontShowOnScreen, False)

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
            debug_print(DEBUG_MODE,f"Windows窗口句柄ui: {hwnd}")

            # 设置窗口层级
            # ctypes.windll.user32.SetWindowPos(
            #     hwnd, -1,  # HWND_TOPMOST
            #     50, 50, 300, 200,
            #     0x40 | 0x10  # SWP_SHOWWINDOW|SWP_NOACTIVATE
            # )

            # 强制刷新
            # ctypes.windll.user32.UpdateWindow(hwnd)
            # ctypes.windll.user32.FlashWindow(hwnd, True)

        self.show()
        debug_print(DEBUG_MODE,"窗口显示命令执行完毕")
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

    def _on_frame_changed(self,*a):
        # debug_print(1,a)
        """Blender帧变化回调函数"""
        # 通过Qt信号机制安全更新UI
        self.frame_changed_signal.emit(a[0].frame_current)

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
import sys
import math
from math import sin, cos
from PySide6.QtCore import Qt, QRect, QPoint, Signal
from PySide6.QtGui import QPainter, QConicalGradient, QLinearGradient, QColor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QApplication

# =================================================================
# 自定义颜色选择器控件
# =================================================================
class CustomColorPicker(QWidget):
    # 当选中的颜色发生变化时发出信号
    colorChanged = Signal(QColor)

    def __init__(self, parent=None):
        super().__init__(parent)
        # 定义各个区域的位置和尺寸
        # 色相轮：圆形区域
        self.hueWheelRect = QRect(10, 10, 150, 150)
        # 中间的饱和度/明度方块
        self.svSquareRect = QRect(180, 10, 150, 150)
        # 右侧的 4 个长方形条（默认水平放置）
        # 这里以竖直排列为例，条的尺寸与间距可调
        sliderWidth = 30
        sliderHeight = 150
        gap = 10
        sliderX = self.svSquareRect.right() + 20
        sliderY = self.svSquareRect.top()
        self.sliderRectangles = {}
        self.sliderRectangles['S'] = QRect(sliderX, sliderY, sliderWidth, sliderHeight)
        self.sliderRectangles['R'] = QRect(sliderX, sliderY + sliderHeight + gap, sliderWidth, sliderHeight)
        self.sliderRectangles['G'] = QRect(sliderX, sliderY + 2*(sliderHeight+gap), sliderWidth, sliderHeight)
        self.sliderRectangles['B'] = QRect(sliderX, sliderY + 3*(sliderHeight+gap), sliderWidth, sliderHeight)

        # 根据各区域计算控件的最小尺寸
        totalWidth = sliderX + sliderWidth + 20
        totalHeight = self.sliderRectangles['B'].bottom() + 20
        self.setMinimumSize(totalWidth, totalHeight)

        # 内部状态：  
        # 色相（0~359）
        self.hue = 0  
        # 饱和度和明度（0～1）——中间方块所选
        self.saturation = 1.0  
        self.value = 1.0  
        # 附加调节：  
        # S：调节饱和度倍率，范围 0～2，默认 1
        self.s_adj = 1.0  
        # R/G/B：通道偏移，范围 -100～100，默认 0
        self.r_adj = 0  
        self.g_adj = 0  
        self.b_adj = 0  

        # 用于记录当前正在拖动的控制区域：'hue'、'sv' 或其中某个 slider 的 key ('S','R','G','B')
        self.activeControl = None

    def paintEvent(self, event):
        painter = QPainter(self)

        # -------------------------
        # 绘制色相轮区域
        # -------------------------
        center = self.hueWheelRect.center()
        radius = self.hueWheelRect.width() / 2
        conical = QConicalGradient(center, -90)
        # 构造 0~360 度的颜色渐变
        for angle in range(0, 361, 10):
            col = QColor.fromHsv(angle % 360, 255, 255)
            conical.setColorAt(angle / 360.0, col)
        painter.setBrush(conical)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(self.hueWheelRect)

        # 绘制色相指示线：从圆心到边缘指示当前色相
        painter.setPen(Qt.black)
        angle_rad = math.radians(self.hue - 90)
        indicatorX = center.x() + radius * 0.9 * cos(angle_rad)
        indicatorY = center.y() + radius * 0.9 * sin(angle_rad)
        painter.drawLine(center, QPoint(int(indicatorX), int(indicatorY)))

        # -------------------------
        # 绘制中间的饱和度/明度选择方块
        # -------------------------
        svRect = self.svSquareRect
        # 1. 先填充当前色相的纯色
        baseColor = QColor.fromHsv(self.hue, 255, 255)
        painter.fillRect(svRect, baseColor)
        # 2. 水平渐变：从白色到透明（调节饱和度）
        gradSat = QLinearGradient(svRect.topLeft(), svRect.topRight())
        gradSat.setColorAt(0, Qt.white)
        gradSat.setColorAt(1, QColor(255, 255, 255, 0))
        painter.fillRect(svRect, gradSat)
        # 3. 垂直渐变：从透明到黑色（调节明度）
        gradVal = QLinearGradient(svRect.topLeft(), svRect.bottomLeft())
        gradVal.setColorAt(0, QColor(0, 0, 0, 0))
        gradVal.setColorAt(1, Qt.black)
        painter.fillRect(svRect, gradVal)
        # 绘制当前选择指示：小圆点的位置根据饱和度和明度
        indX = svRect.left() + self.saturation * svRect.width()
        indY = svRect.top() + (1 - self.value) * svRect.height()
        painter.setPen(Qt.black)
        painter.drawEllipse(QPoint(int(indX), int(indY)), 5, 5)

        # -------------------------
        # 绘制右侧的 4 个滑动条
        # -------------------------
        for key, rect in self.sliderRectangles.items():
            painter.setPen(Qt.black)
            painter.drawRect(rect)
            # 根据不同的 slider 定义数值归一化方法和背景渐变
            if key == 'S':
                # S：范围 0～2，归一化：0 对应 0，1 对应 1/2，2 对应 1
                normVal = (self.s_adj - 0) / 2.0
                grad = QLinearGradient(rect.topLeft(), rect.topRight())
                # 渐变从 desaturated 到 fully saturated（使用当前色相）
                grad.setColorAt(0, QColor.fromHsv(self.hue, 0, 255))
                grad.setColorAt(1, QColor.fromHsv(self.hue, 255, 255))
            elif key in ['R', 'G', 'B']:
                # R/G/B：范围 -100～100，归一化：-100 -> 0, 0 -> 0.5, 100 -> 1
                if key == 'R':
                    normVal = (self.r_adj + 100) / 200.0
                    baseVal = QColor.fromHsv(self.hue, int(self.saturation * 255), int(self.value * 255)).red()
                    grad = QLinearGradient(rect.topLeft(), rect.topRight())
                    grad.setColorAt(0, QColor(max(0, baseVal - 100), 0, 0))
                    grad.setColorAt(1, QColor(min(255, baseVal + 100), 0, 0))
                elif key == 'G':
                    normVal = (self.g_adj + 100) / 200.0
                    baseVal = QColor.fromHsv(self.hue, int(self.saturation * 255), int(self.value * 255)).green()
                    grad = QLinearGradient(rect.topLeft(), rect.topRight())
                    grad.setColorAt(0, QColor(0, max(0, baseVal - 100), 0))
                    grad.setColorAt(1, QColor(0, min(255, baseVal + 100), 0))
                elif key == 'B':
                    normVal = (self.b_adj + 100) / 200.0
                    baseVal = QColor.fromHsv(self.hue, int(self.saturation * 255), int(self.value * 255)).blue()
                    grad = QLinearGradient(rect.topLeft(), rect.topRight())
                    grad.setColorAt(0, QColor(0, 0, max(0, baseVal - 100)))
                    grad.setColorAt(1, QColor(0, 0, min(255, baseVal + 100)))
            else:
                normVal = 0
                grad = QLinearGradient(rect.topLeft(), rect.topRight())
            # 填充滑动条背景
            painter.fillRect(rect.adjusted(1, 1, -1, -1), grad)
            # 在条上画一条指示线（垂直线）显示当前值
            indicatorX = rect.left() + normVal * rect.width()
            painter.setPen(Qt.white)
            painter.drawLine(int(indicatorX), rect.top(), int(indicatorX), rect.bottom())
            # 绘制标识文字
            painter.setPen(Qt.black)
            painter.drawText(rect, Qt.AlignCenter, key)

    # -------------------------
    # 鼠标事件处理
    # -------------------------
    def mousePressEvent(self, event):
        pos = event.pos()
        # 判断点击位置属于哪个区域
        if self.hueWheelRect.contains(pos):
            # 判断是否在圆形内
            center = self.hueWheelRect.center()
            dx = pos.x() - center.x()
            dy = pos.y() - center.y()
            if dx * dx + dy * dy <= (self.hueWheelRect.width()/2)**2:
                self.activeControl = 'hue'
                self.updateHueFromPos(pos)
                return
        if self.svSquareRect.contains(pos):
            self.activeControl = 'sv'
            self.updateSVFromPos(pos)
            return
        for key, rect in self.sliderRectangles.items():
            if rect.contains(pos):
                self.activeControl = key
                self.updateSliderFromPos(key, pos)
                return

    def mouseMoveEvent(self, event):
        pos = event.pos()
        if self.activeControl == 'hue':
            self.updateHueFromPos(pos)
        elif self.activeControl == 'sv':
            self.updateSVFromPos(pos)
        elif self.activeControl in self.sliderRectangles:
            self.updateSliderFromPos(self.activeControl, pos)

    def mouseReleaseEvent(self, event):
        self.activeControl = None

    # -------------------------
    # 根据鼠标位置更新各区域的数值
    # -------------------------
    def updateHueFromPos(self, pos):
        center = self.hueWheelRect.center()
        dx = pos.x() - center.x()
        dy = pos.y() - center.y()
        angle = math.degrees(math.atan2(dy, dx))
        if angle < 0:
            angle += 360
        self.hue = int(angle)
        self.emitColorChanged()
        self.update()

    def updateSVFromPos(self, pos):
        rect = self.svSquareRect
        x = pos.x() - rect.left()
        y = pos.y() - rect.top()
        self.saturation = max(0.0, min(1.0, x / rect.width()))
        self.value = max(0.0, min(1.0, 1 - y / rect.height()))
        self.emitColorChanged()
        self.update()

    def updateSliderFromPos(self, key, pos):
        rect = self.sliderRectangles[key]
        x = pos.x() - rect.left()
        norm = max(0.0, min(1.0, x / rect.width()))
        if key == 'S':
            self.s_adj = norm * 2.0  # 范围 0～2
        elif key in ['R', 'G', 'B']:
            # 范围 -100～100
            value = norm * 200 - 100
            if key == 'R':
                self.r_adj = int(value)
            elif key == 'G':
                self.g_adj = int(value)
            elif key == 'B':
                self.b_adj = int(value)
        self.emitColorChanged()
        self.update()

    def emitColorChanged(self):
        # 根据当前参数计算最终颜色
        # 首先根据色相和 SV 得到 HSV 基础色
        base = QColor.fromHsv(self.hue,
                              int(self.saturation * 255 * self.s_adj),
                              int(self.value * 255))
        # 转换到 RGB 后叠加 R/G/B 偏移（注意控制范围在 0～255 内）
        r = max(0, min(255, base.red() + self.r_adj))
        g = max(0, min(255, base.green() + self.g_adj))
        b = max(0, min(255, base.blue() + self.b_adj))
        finalColor = QColor(r, g, b)
        self.colorChanged.emit(finalColor)
# =================================================================
# 示例：将自定义颜色选择器嵌入到一个简单窗口中
# =================================================================
if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWidget = QWidget()
    layout = QVBoxLayout(mainWidget)
    colorPicker = CustomColorPicker()
    layout.addWidget(colorPicker)
    
    # 标签用于显示当前选中的颜色
    from PySide6.QtWidgets import QLabel
    colorLabel = QLabel("当前颜色")
    colorLabel.setAlignment(Qt.AlignCenter)
    colorLabel.setStyleSheet("background: #ffffff; font-size: 18px;")
    layout.addWidget(colorLabel)
    
    # 当颜色发生变化时更新标签背景色
    def on_color_changed(col):
        colorLabel.setText(f"当前颜色: {col.name()}")
        colorLabel.setStyleSheet(f"background: {col.name()}; font-size: 18px;")
    colorPicker.colorChanged.connect(on_color_changed)
    
    mainWidget.show()
    sys.exit(app.exec())
