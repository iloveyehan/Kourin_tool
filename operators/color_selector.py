import math
import sys
import bpy
import ctypes
from pathlib import Path
import platform
import weakref
import numpy as np
from PySide6.QtCore import Qt, QRect, QPoint, Signal,QRectF,QPointF
from PySide6.QtGui import QPaintEvent, QWindow, QGuiApplication, QConicalGradient, QLinearGradient,QColor,QKeyEvent, QPainter,QPen
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout,QPushButton,QSlider


from ..utils.color_selector import debug_print,set_brush_color_based_on_mode,get_brush_color_based_on_mode,exchange_brush_color_based_on_mode
# from ..ui.ui_color_selector import EmbeddedQtWidget,CustomColorPicker
from ..common.class_loader.auto_load import ClassAutoloader
color_selector=ClassAutoloader(Path(__file__))
def reg_color_selector():
    color_selector.init()
    color_selector.register()
def unreg_color_selector():
    color_selector.unregister()
# 调试模式开关
DEBUG_MODE = True
import math
from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import QPainter, QConicalGradient, QLinearGradient, QColor
from PySide6.QtWidgets import QWidget

class CustomColorPicker(QWidget):
    # 当颜色变化时发出信号
    colorChanged = Signal(QColor)

    def __init__(self,parent, **k):
        super().__init__(parent)
        for key,v in k.items():
            setattr(self,key,v)
        
        self.mode=self.context.mode
        self.sv_pressed=False
        self.init_pos=QPointF(*tuple(self.init_pos-self.cp_margin))
        # 初始 HSV 值
        self.color=get_brush_color_based_on_mode(self)
        self.h = self.color.h*360.0         # 色相 [0, 360)
        self.s = self.color.s # 饱和度 [0, 1]
        self.v = self.color.v      # 明度 [0, 1]
        # 用于交互状态，指示当前处于哪个区域控制中："ring" 或 "sv"
        self.activeControl = None

        # 用于缓存绘制时的关键参数
        self._cached_center = None
        self._cached_outer_radius = None
        self._cached_inner_radius = None

        #rbg hsv模式切换
        self.is_ryb_mode=True
        # 控制正方形与圆环之间的间隙
        self.gap = 0
        # self.setWindowFlags(Qt.FramelessWindowHint)  # [!] 关键：必须无边框
        # self.setAttribute(Qt.WA_TranslucentBackground, True)  # [!] 核心透明度属性

  
    def toggle_color_mode(self):
        """切换色环模式"""
        self.is_ryb_mode = not self.is_ryb_mode
        self.update()
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # === 计算基本参数 ===
  
        center = self.init_pos
        self._cached_center = center
        
        # 外圈半径：取宽高较小者的一半，再减去 margin
        outer_radius = self.cp_radius 
        # 环的厚度（可调），例如 30 像素
        ring_thickness = 20
        # 内圈半径
        inner_radius = outer_radius - ring_thickness
        self._cached_outer_radius = outer_radius
        self._cached_inner_radius = inner_radius
        self.gap=int(inner_radius/3)
        # === 绘制色相环 ===
        # 外圈所在的矩形区域
        outer_rect = QRectF(center.x() - outer_radius, center.y() - outer_radius,
                            2 * outer_radius, 2 * outer_radius)
        # 构造色相渐变：用 QConicalGradient 绘制 0～360 度颜色
        conical = QConicalGradient(center,90)
 
        for angle in range(0, 361, 10):
            col = QColor.fromHsv(angle % 360, 255, 255)
            conical.setColorAt(1-angle / 360.0, col)
        painter.setBrush(conical)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(outer_rect)


        # 获取实际颜色
        current_color = QColor.fromHsvF(
            self.h/360.0,
            self.s,
            self.v
        )

        # 用控件背景色“挖空”内侧，形成环状效果
        inner_rect = QRect(center.x() - inner_radius, center.y() - inner_radius,
                            2 * inner_radius, 2 * inner_radius)
        # 先挖掉,再绘制一层背景色,才能设置半透明
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.drawEllipse(inner_rect)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(*self.bg_color))
        painter.drawEllipse(inner_rect)
  
    

        # 绘制当前色相指示点
        mid_radius = float(outer_radius-10)
        angle_rad = math.radians(self.h - 90)
        # print(f'center {center}angle_rad',angle_rad)
        indicator_pos = QPointF((center.x() + mid_radius * math.cos(angle_rad)),
                               (center.y() + mid_radius * math.sin(angle_rad))
                               )
         # 绘制指示器线条


        # 定义双边框参数
        quad_border_w = 16    # 外层边框总宽度
        quad_border_l = 26    # 外层边框总长度
        inner_gap = 2         # 内外边框间距

        black = 30            # 内层边框颜色（深灰）
        white = 220           # 外层边框颜色（浅灰）

        painter.save()
        painter.translate(center)
        painter.rotate(math.degrees(angle_rad))

        # ===== 绘制外层白色边框 =====
        outer_rect = QRectF(
            inner_radius - 0.5*(quad_border_l - ring_thickness),
            -0.5 * quad_border_w,  # Y轴居中
            quad_border_l,
            quad_border_w
        )
        painter.setPen(QPen(QColor(black, black, black), 1.5))
        painter.setBrush(Qt.NoBrush)  # 外层不填充
        painter.drawRect(outer_rect)

        # ===== 绘制内层黑色边框 =====
        inner_rect = QRectF(
            outer_rect.x() + inner_gap,            # X方向内缩
            outer_rect.y() + inner_gap,            # Y方向内缩
            outer_rect.width() - 2 * inner_gap,    # 宽度减小
            outer_rect.height() - 2 * inner_gap    # 高度减小
        )
        painter.setPen(QPen(QColor(white, white, white), 2))
        painter.drawRect(inner_rect)

        # ===== 填充中心区域 =====
        fill_rect = QRectF(
            inner_rect.x() + 1,                    # 进一步内缩
            inner_rect.y() + 1,
            inner_rect.width() - 2,
            inner_rect.height() - 2
        )
        painter.setPen(Qt.NoPen)                   # 无边框
        painter.setBrush(current_color)            # 使用外部传入的颜色
        painter.drawRect(fill_rect)

        painter.restore()





        # === 绘制正方形（SV 选择区） ===
        # 正方形放置于内圈内部，但与内圈边缘留有一定 gap
        # 正方形边长 = 内圈直径 - 2 * gap
        square_side = (2 * inner_radius) - 2 * self.gap
        # square_side = (2 * inner_radius) - 80
        svRect = QRectF(center.x() - square_side / 2, center.y() - square_side / 2,
                        square_side, square_side)
        # 1. 填充当前色相的纯色
        baseColor = QColor.fromHsv(self.h, 255, 255)
        painter.fillRect(svRect, baseColor)
        # 2. 叠加水平渐变：从白色到透明，调节饱和度
        gradSat = QLinearGradient(svRect.topLeft(), svRect.topRight())
        gradSat.setColorAt(0, Qt.white)
        gradSat.setColorAt(1, QColor(255, 255, 255, 0))
        painter.fillRect(svRect, gradSat)
        # 3. 叠加垂直渐变：从透明到黑色，调节明度
        gradVal = QLinearGradient(svRect.topLeft(), svRect.bottomLeft())
        gradVal.setColorAt(0, QColor(0, 0, 0, 0))
        gradVal.setColorAt(1, Qt.black)
        painter.fillRect(svRect, gradVal)
        
        # 绘制当前选择指示点
        indX = svRect.left() + self.s * svRect.width()
        indY = svRect.top() + (1 - self.v) * svRect.height()

        # === 修改后的SV指示点绘制 ===
        base_radius = 9.5
        mid_radius = 8
        inner_radius = 6

        if self.sv_pressed:  # 按下时放大
            base_radius += 2
            mid_radius += 2
            inner_radius += 2

        # 黑色外圈
        painter.setPen(QPen(QColor(black, black, black), 1.5))
        painter.setBrush(QColor(black, black, black))
        painter.drawEllipse(QPointF(indX, indY), base_radius, base_radius)

        # 白色中间圈
        painter.setPen(QPen(QColor(white, white, white), 2))
        painter.setBrush(QColor(white, white, white))
        painter.drawEllipse(QPointF(indX, indY), mid_radius, mid_radius)

        # 颜色内圈
        painter.setPen(QPen(current_color, 2))
        painter.setBrush(current_color)
        painter.drawEllipse(QPointF(indX, indY), inner_radius, inner_radius)
        painter.end()
    def mousePressEvent(self, event):
        pos = event.pos()
        center = self._cached_center if self._cached_center is not None else self.init_pos
        dx = pos.x() - center.x()
        dy = pos.y() - center.y()
        distance = math.hypot(dx, dy)
        # 判断是否在色相环区域内（距离在 [inner_radius, outer_radius] 内，允许一定容错）
        inner = self._cached_inner_radius if self._cached_inner_radius is not None else 0
        outer = self._cached_outer_radius if self._cached_outer_radius is not None else 0
        tolerance = 5  # 允许一定误差
        if inner - tolerance <= distance <= outer + tolerance:
            self.activeControl = "ring"
            self.updateHueFromPos(pos)
            return

        # 如果点击在正方形区域内，则控制饱和度和明度
        half_side = inner - self.gap
        square_side = 2 * half_side
        svRect = QRectF(center.x() - half_side, center.y() - half_side,
                        square_side, square_side)
        if svRect.contains(pos):
            self.activeControl = "sv"
            self.sv_pressed = True  # 设置按下状态
            self.updateSVFromPos(pos)
            return

    def mouseMoveEvent(self, event):
        pos = event.pos()
        if self.activeControl == "ring":
            self.updateHueFromPos(pos)
        elif self.activeControl == "sv":
            self.updateSVFromPos(pos)
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._pressed = False
            self.sv_pressed = False  # 清除按下状态
            self.activeControl = None
            self.update()  # 触发重绘
    def updateHueFromPos(self, pos):
        # 根据鼠标位置计算新的色相
        center = self._cached_center if self._cached_center is not None else self.init_pos
        dx = pos.x() - center.x()
        dy = pos.y() - center.y()
        angle = math.degrees(math.atan2(dy, dx))
        if angle < 0:
            angle += 360
        # 调整角度，保证正上方为 0 度
        angle = (angle + 90) % 360
        self.h = angle
        set_brush_color_based_on_mode(self,color=(angle/360.0,self.s,self.v),hsv=1)
        self.update()


    def updateSVFromPos(self, pos):
        # 根据鼠标位置更新饱和度和明度
        center = self.init_pos
        inner = self._cached_inner_radius if self._cached_inner_radius is not None else 0
        square_side = 2 * (inner-self.gap)
        svRect = QRectF(center.x() - square_side / 2, center.y() - square_side / 2,
                        square_side, square_side)
        x = pos.x() - svRect.left()
        y = pos.y() - svRect.top()
        self.s = max(0.0, min(1.0, x / svRect.width()))
        self.v = max(0.0, min(1.0, 1 - y / svRect.height()))
        
        set_brush_color_based_on_mode(self,color=(self.h/360.0,self.s,self.v),hsv=1)
        self.update()
    def keyPressEvent(self, event: QKeyEvent):
        debug_print('按键事件')
        if event.key() == Qt.Key_X:
            print("按下了 'X' 键")
        else:
            print("按下了 '1' 键")
            super().keyPressEvent(event)  # 处理其他按键事件  

bg_color=(30, 30, 30, 200)
# -----------------------------------------------------------------
# EmbeddedQtWidget：嵌入 Blender 的窗口，内部包含一个 CustomColorPicker
# -----------------------------------------------------------------
class EmbeddedQtWidget(QWidget):
    frame_changed_signal = Signal(int)

    def __init__(self,context, parent_hwnd,init_pos,):
        # for key,v in context_dict.items():
        #     setattr(self,key,v)
        
        self.context=context
        self.bg_color=bg_color
        window=bpy.context.window
        height=window.height
        width=window.width
        
        self.init_pos=np.array([init_pos[0],height-init_pos[1]])
        super().__init__()
        
        # Windows DPI处理
        if platform.system() == "Windows":
            self.setAttribute(Qt.WA_NativeWindow, True)
        
        
        
        # 嵌入 Blender 主窗口（将传入的句柄转换为 QWindow 对象）
        blender_window = QWindow.fromWinId(parent_hwnd)
        if blender_window.screen() is None:
            raise RuntimeError("无效的父窗口")
        self.windowHandle().setParent(blender_window)

        self.setWindowOpacity(0.99999)


        self.setGeometry(0, 0, width, height)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowFlags(Qt.FramelessWindowHint)  # [!] 关键：必须无边框
        self.show()
        self.setFocusPolicy(Qt.StrongFocus)

        # 创建自定义颜色选择器控件
        self.cp_dict={
            'cp_radius':150,
            'cp_margin':10,
            'bg_color':self.bg_color,
            'init_pos':self.init_pos,
            'context':bpy.context,
            'tool_settings':bpy.context,
            'scene':bpy.context.scene,
            'mode':bpy.context.mode,
            'area':bpy.context.area,
            'ui_mode':None,
            'vertex_paint':context.tool_settings.vertex_paint if hasattr(context.tool_settings,'vertex_paint') else None,
            'image_paint':context.tool_settings.image_paint if hasattr(context.tool_settings,'image_paint') else None,
            'gpencil_paint':context.tool_settings.gpencil_paint if hasattr(context.tool_settings,'gpencil_paint') else None,
            'gpencil_vertex_paint':context.tool_settings.gpencil_paint if hasattr(context.tool_settings,'gpencil_vertex_paint') else None,
        
        }


        # 将矩形放到鼠标位置(考虑colorpicker的间隔)
        self.init_pos=self.init_pos-self.cp_dict['cp_radius']-self.cp_dict['cp_margin']
        self.customColorPicker = CustomColorPicker(self,**self.cp_dict)

        # 创建滑动条
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 20)
        self.slider.setValue(10)
        self.slider.setStyleSheet("""
            QSlider {
                width: 20px;
                background-color: #666;
                color: white;
                border: 2px solid #666;
                margin: 0px;
            }
        """)
        self.slider.setMinimumWidth(100)
        self.slider.setMinimumSize(100,100)
        self.slider.setSingleStep(5)
        self.slider.setPageStep(0)
        
        # self.customColorPicker.colorChanged.connect(self.on_color_changed)
         # 添加模式切换按钮
        self.toggle_btn = QPushButton("", self)
        self.toggle_btn.setFixedSize(50, 50)  # 正方形按钮
        self.toggle_btn.move(100+self.init_pos[0], 100+self.init_pos[1])  # 左上角位置
        self.toggle_btn.clicked.connect(self.toggle_color_mode)
        # self.update_button_style()
        # 布局管理，将帧号标签与颜色选择器放入布局中
        layout = QVBoxLayout()
        # layout.addWidget(self.frame_label)
        layout.addWidget(self.customColorPicker)
        # layout.addWidget(self.toggle_btn)
        # layout.addWidget(self.slider)
        
        self.setLayout(layout)
        self.setWindowOpacity(1)
        self.update()
  

        
        # 拖动相关变量及鼠标处理
        from PySide6.QtCore import QPoint
        self.dragging = False
        self.drag_start_position = self.pos()
        self.drag_mouse_start_pos = QPoint()
        
        self.draw_start_pos = QPoint(0, 0)  # 默认绘制起点
        self.setMouseTracking(True)
    def keyPressEvent(self, event: QKeyEvent):
        debug_print('按键事件')
        if event.key() == Qt.Key_X:
            print("按下了 'X' 键")
        else:
            print("按下了 '1' 键")
            super().keyPressEvent(event)  # 处理其他按键事件            
    def paintEvent(self, event: QPaintEvent) -> None:
        painter=QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 定义倒角（圆角）的半径
        corner_radius = 10  # 可以根据需要调整
        
        # 获取整个窗口的绘制区域
        # rect = self.rect()
        # 以鼠标位置为起点绘制
        rect = QRect(
            self.init_pos[0],  
            self.init_pos[1], 
            600, 320  # 100x100的矩形
        )
        
        # 绘制带圆角的矩形背景
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(*bg_color))
        painter.drawRoundedRect(rect, corner_radius, corner_radius)
        return super().paintEvent(event)
    def toggle_color_mode(self):
        """切换颜色模式"""
        # self.customColorPicker.toggle_color_mode()
        self.update_button_style()
    def update_button_style(self):
        """更新按钮样式指示当前模式"""
        pass
    def on_color_changed(self, color: QColor):
        # 示例：修改窗口背景色
        new_style = f"""
            QWidget {{
                background: {color.name()};
                border: 5px solid #00FF00;
            }}
            QLabel {{
                color: #FFFFFF;
                font-size: 24px;
                font-weight: bold;
            }}
        """
        self.setStyleSheet(new_style)
        # debug_print( f"选择的颜色: {color.name()}")
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_mouse_start_pos = event.globalPosition().toPoint()
            self.drag_start_position = self.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
        
    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() & Qt.LeftButton:
            delta = event.globalPosition().toPoint() - self.drag_mouse_start_pos
            new_pos = self.drag_start_position + delta
            self.move(new_pos)
            event.accept()
        
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
        


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
class EmbedQtOperator(bpy.types.Operator):
    bl_idname = "qt.color_selector"
    bl_label = "嵌入Qt窗口"
    
    # [!] 使用弱引用持有Qt实例
    _qt_app_ref = None
    _qt_window_ref = None
    @classmethod
    def poll(cls, context):
        if bpy.context.mode == 'SCULPT' and bpy.context.tool_settings.sculpt.brush == bpy.data.brushes['Paint']:
            sculpt = True
            return sculpt
        if context.area.type == 'IMAGE_EDITOR':
            if context.area.spaces.active.ui_mode=='PAINT':
                image_paint=True
                return image_paint
        if (context.mode in {'PAINT_VERTEX','VERTEX_PAINT','TEXTURE_PAINT', 'PAINT_TEXTURE', 'PAINT_GPENCIL', 'VERTEX_GPENCIL', }) and context.area.type == 'VIEW_3D':
            return True
        return False
    def _ensure_qt_app(self):
        """确保存在有效的QApplication实例"""
        if platform.system() == "Windows":
            # 设置 DPI 感知（兼容旧版 Windows）
            try:
                # 尝试使用较新的 API
                ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_AWARE
            except Exception as e:
                try:
                    # 回退到旧版 API
                    ctypes.windll.user32.SetProcessDPIAware()
                except Exception as e2:
                    debug_print( f"DPI 设置失败: {e2}")

        if not QApplication.instance():
            debug_print( "创建新的QApplication实例")
            app = QApplication(sys.argv)
            self.__class__._qt_app_ref = weakref.ref(app)
        else:
            debug_print( "使用现有QApplication实例")
        return QApplication.instance()

    def execute(self, context):
        
        return {'RUNNING_MODAL'}
    def modal(self, context, event):
        # if event.type == 'X' and event.value == 'RELEASE':
        #     exchange_brush_color_based_on_mode(bpy._embedded_qt.customColorPicker,exchange=True)
        # [!] 优化事件过滤
        # if event.type == 'SPACE':
        if event.value == 'PRESS':
            if self._qt_window_ref and self._qt_window_ref():
                window = self._qt_window_ref()
                window.show()
                # [!] Windows专用激活代码
                if platform.system() == "Windows":
                    window.winId()  # 强制创建窗口句柄
                    hwnd = window.windowHandle().winId()
                    # ctypes.windll.user32.ShowWindow(hwnd, 1)  # SW_SHOWNORMAL
                    # ctypes.windll.user32.SetForegroundWindow(hwnd)
                window.raise_()
        elif event.type in ['SPACE','Z'] and event.value == 'RELEASE':
            if self._qt_window_ref and self._qt_window_ref():
                self._qt_window_ref().hide()
            self._cleanup()
            return {'FINISHED'}
        # return {'RUNNING_MODAL'}
        
        # 退出逻辑
        if event.type in {'ESC', 'RIGHTMOUSE'}:
            self._cleanup()
            return {'CANCELLED'}
        
        return {'PASS_THROUGH'}

    def _cleanup(self):
        """安全清理资源"""
        if self._qt_window_ref and self._qt_window_ref():
            window = self._qt_window_ref()
            window.close()
            window.deleteLater()
        if self._qt_app_ref and self._qt_app_ref():
            app = self._qt_app_ref()
            app.quit()

    def invoke(self, context, event):
        region = bpy.context.region
        # debug_print('上下文1',context.mode)
        mouse_pose=(event.mouse_x,event.mouse_y)
        
        # [!] 统一初始化入口
        self._ensure_qt_app()
        
        parent_hwnd = get_blender_hwnd()
        if not parent_hwnd:
            self.report({'ERROR'}, "无法获取窗口句柄")
            return {'CANCELLED'}

        try:
            # [!] 清理旧窗口
            if hasattr(bpy, '_embedded_qt'):
                bpy._embedded_qt.close()
                del bpy._embedded_qt
            # print(context.tool_settings.vertex_paint)
            # [!] 创建窗口时立即显示
            # debug_print('鼠标坐标',mouse_pose)
            context_dict={
                'mode':context.mode,
                'area':context.area,
                'scene':context.scene,
                'vertex_paint':context.tool_settings.vertex_paint if hasattr(context.tool_settings,'vertex_paint') else None,
                'image_paint':context.tool_settings.image_paint if hasattr(context.tool_settings,'image_paint') else None,
                'gpencil_paint':context.tool_settings.gpencil_paint if hasattr(context.tool_settings,'gpencil_paint') else None,
                'gpencil_vertex_paint':context.tool_settings.gpencil_paint if hasattr(context.tool_settings,'gpencil_vertex_paint') else None,
            }
            bpy._embedded_qt = EmbeddedQtWidget(context,parent_hwnd,init_pos=mouse_pose)
            # debug_print('上下文2',context,context.mode)
            bpy._embedded_qt.show()
            self.__class__._qt_window_ref = weakref.ref(bpy._embedded_qt)
            
            # [!] 强制处理Qt事件队列
            QApplication.processEvents()
            QApplication.sendPostedEvents(None, 0)
            # debug_print('上下文3',context,context.mode)
            
            # debug_print('context.area.spaces.active.ui_mode',hasattr(context.area.spaces.active,'ui_mode'))
            # 启动模态
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
            
        except Exception as e:
            self.report({'ERROR'}, f"窗口创建失败: {str(e)}")
            return {'CANCELLED'}