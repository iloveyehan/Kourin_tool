import ctypes
from ctypes import wintypes
from functools import partial
import os
from pathlib import Path
import platform
import sys
import weakref
from PySide6.QtWidgets import QApplication, QWidget,QVBoxLayout, QLabel,QHBoxLayout

from PySide6.QtGui import QWindow, QMouseEvent,QRegion
from PySide6.QtCore import Qt, QTimer,QPoint,Signal,QRect,QTranslator
import bpy
import numpy as np

from ..translations import get_blender_language

from ..ui.ui_widgets import Button
from ..operators.color_selector import get_blender_hwnd

from ..utils.color_selector import debug_print

from ..utils.utils import undoable
class BaseQtOperator():
    # [!] 使用弱引用持有Qt实例
    _qt_app_ref = None
    _qt_window_ref = None

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
        # else:
        #     debug_print( "使用现有QApplication实例")
        translator = QTranslator()
        BaseQtOperator._qt_translator = translator
        lang = get_blender_language()
        
        qm_path = Path(__file__).parent.parent / "translations" / f"{lang}.qm"
        print('[DEBUG]',lang)
        print('[DEBUG] qm_path', qm_path)

        if qm_path.exists():
            t=translator.load(str(qm_path))
            QApplication.instance().installTranslator(translator)
            print(f"[Qt] Loaded language: {lang}",t)
        else:
            print(f"[Qt] Translation file not found: {qm_path}")
        print("Translator isEmpty?", translator.isEmpty())
        print("File path:", translator.filePath())
        return QApplication.instance()

    def execute(self, context):
        
        return {'RUNNING_MODAL'}
    def get_mouse_pos(self):
        pt = wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        return pt.x, pt.y
    def modal(self, context, event):
        if hasattr(self,'auto_close'):
            if self.auto_close:
                self._cleanup()
                return {'FINISHED'}
        if event.type == 'SPACE' and event.value == 'PRESS':
            # print('123')
            if self._qt_window_ref:
                window = self._qt_window_ref()
                window.show()
                # [!] Windows专用激活代码
                if platform.system() == "Windows":
                    window.winId()  # 强制创建窗口句柄
                window.raise_()
                self.key_space_press_ops()
                # window.Sculptwheel.set_global_mouse(*self.get_mouse_pos())
        elif event.type in ['SPACE','Z'] and event.value == 'RELEASE':
            # 把 Blender 坐标先给 Sculptwheel，内部会做转换并重绘
            self.key_space_release_ops()
            # sculptwheel = self._qt_window_ref().Sculptwheel
            # sculptwheel.set_global_mouse(*self.get_mouse_pos())
            # sculptwheel.keyReleaseOps()
            self._cleanup()
            return {'FINISHED'}

        if event.type in {'ESC', 'RIGHTMOUSE'}:
            self._cleanup()
            return {'CANCELLED'}
        
        return {'PASS_THROUGH'}
    def key_space_release_ops(self):
        pass
    def key_space_press_ops(self):
        pass
    # window.Sculptwheel.set_global_mouse(*self.get_mouse_pos())
    def _cleanup(self):
        """安全清理资源"""
        if self._qt_window_ref :
            window = self._qt_window_ref()
            window.close()
            window.deleteLater()
        if self._qt_app_ref:
            app = self._qt_app_ref()
            app.quit()

    def invoke(self, context, event):
        mouse_pose=(event.mouse_x,event.mouse_y)
        if hasattr(self,'auto_close'):
            self.auto_close=False
        # [!] 统一初始化入口
        self._ensure_qt_app()
        
        parent_hwnd = get_blender_hwnd()
        if not parent_hwnd:
            self.report({'ERROR'}, "无法获取窗口句柄")
            return {'CANCELLED'}

        try:
            # [!] 清理旧窗口
            # if hasattr(bpy, '_embedded_qt'):
            #     bpy._embedded_qt.close()
            #     del bpy._embedded_qt
            # —— 安全销毁旧窗口 ——
            old = getattr(bpy, "_embedded_qt", None)
            print('old',old)
            if old is not None:
                old.deleteLater()
                del bpy._embedded_qt
                # 处理一下事件队列，确保 C++ 对象真的被销毁
                QApplication.processEvents()
            bpy._embedded_qt = self.set_embedded_qt(context,parent_hwnd,init_pos=mouse_pose)

            self.__class__._qt_window_ref = weakref.ref(bpy._embedded_qt)
# 启动模态
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
            
        except Exception as e:
            self.report({'ERROR'}, f"窗口创建失败: {str(e)}")
            return {'CANCELLED'}
    def set_embedded_qt(self,context,parent_hwnd,init_pos):
        '返回主窗口'
        pass
        # return SculptMenuWidget(context,parent_hwnd,init_pos=init_pos)
            