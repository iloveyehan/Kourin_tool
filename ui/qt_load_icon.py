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
MODULE_DIR = Path(__file__).parent.parent.resolve()
def icon_from_dat(filename: str) -> QIcon:
    """
    从模块下的 icons 子文件夹读取指定文件并返回 QIcon。
    
    :param filename: 如 'brush_data.svg'
    :raises FileNotFoundError: 若文件不存在
    """
    # 2. 拼接到 icons 子目录
    file_path = MODULE_DIR / "icons" / filename
    if not file_path.exists():
        raise FileNotFoundError(f"找不到文件: {file_path}")
    
    # 3. 读取二进制并转换为 QIcon
    data = file_path.read_bytes()
    pixmap = QPixmap()
    if not pixmap.loadFromData(QByteArray(data)):
        raise ValueError(f"无法从 {file_path} 解析为图标")
    return QIcon(pixmap)
def pixmap_from_dat(filename: str) -> QIcon:
    """
    从模块下的 icons 子文件夹读取指定文件并返回 QIcon。
    
    :param filename: 如 'brush_data.svg'
    :raises FileNotFoundError: 若文件不存在
    """
    # 2. 拼接到 icons 子目录
    file_path = MODULE_DIR / "icons" / filename
    if not file_path.exists():
        raise FileNotFoundError(f"找不到文件: {file_path}")
    
    # 3. 读取二进制并转换为 QIcon
    data = file_path.read_bytes()
    pixmap = QPixmap()
    if not pixmap.loadFromData(QByteArray(data)):
        raise ValueError(f"无法从 {file_path} 解析为图标")
    return pixmap
