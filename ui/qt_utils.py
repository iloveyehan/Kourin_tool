import ctypes
from math import inf
from pathlib import Path
import sys
import bpy
from functools import partial
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtWidgets import QListView,QSizePolicy,QSizeGrip,QSplitter,QAbstractItemView
from PySide6.QtCore import Qt, QTimer, QTranslator, QSize, QSettings,QByteArray,QPoint
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel,QHBoxLayout,QMenu
from PySide6.QtGui import QKeyEvent, QCursor,QIcon,QPixmap,QWindow
from time import time
def refocus_blender_window():
    # print('焦点重回blender')
    blender_hwnd = ctypes.windll.user32.FindWindowW("GHOST_WindowClass", None)
    if blender_hwnd:
        # 强制将焦点切回 Blender
        ctypes.windll.user32.SetForegroundWindow(blender_hwnd)
        # 可选：确保允许设置前台窗口（对一些权限受限的情况）
        ctypes.windll.user32.AllowSetForegroundWindow(-1)