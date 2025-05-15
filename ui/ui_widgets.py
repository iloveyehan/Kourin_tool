import ctypes
from math import inf
from pathlib import Path
import sys
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt, QTimer, QTranslator, QSize, QSettings,QByteArray
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel,QHBoxLayout,QMenu
from PySide6.QtGui import QKeyEvent, QCursor,QIcon,QPixmap
from time import time

import bpy
def refocus_blender_window():
    print('焦点重回blender')
    blender_hwnd = ctypes.windll.user32.FindWindowW("GHOST_WindowClass", None)
    if blender_hwnd:
        # 强制将焦点切回 Blender
        ctypes.windll.user32.SetForegroundWindow(blender_hwnd)
        # 可选：确保允许设置前台窗口（对一些权限受限的情况）
        ctypes.windll.user32.AllowSetForegroundWindow(-1)
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
class MenuButton(QPushButton):
    def __init__(self,parent = None,text='',icon_path=None,size=(20,20)):
        super(MenuButton,self).__init__(parent)
        self.setText(f"{text}")
        self.icon_path=icon_path
        self.icon_size=size
        self.setStyleSheet("""
            Button:pressed {
                background-color: #bbbbbb;
            }
            Button:focus {
                outline: none;
            }
        """)
        if icon_path is not None:
            my_icon = icon_from_dat(icon_path)
            self.setIcon(my_icon)
            self.setIconSize(QSize(*self.icon_size))
            self.setFixedSize(*self.icon_size)

        self.icon_dict={
            '混合后的新形态':['NewShapeFromMix','add.svg'],
            '镜像形态键':['Mirror','arrow_leftright.svg'],
            '镜像形态键(拓扑)':['MirrorTopo',''],
            '合并为形变':['JoinAs',''],
            '传递形态键':['Trans',''],
            '删除全部':['DelteAll','panel_close.svg'],
            '应用全部':['ApplyAll',''],
            '全部锁定':['Lock','locked.svg'],
            '全部解锁':['Unlock','unlocked.svg'],
            '移至顶部':['MoveToTop','tria_up_bar.svg'],
            '移至底部':['MoveToBottom','tria_down_bar.svg'],
            '应用到basis':['ApplyToBasis',''],
            '移除未使用':['RemoveUnuse',''],
        }
        self.createContextMenu()  
 
    def createContextMenu(self):  
        # 创建右键菜单 
        # 必须将ContextMenuPolicy设置为Qt.CustomContextMenu  
        # 否则无法使用customContextMenuRequested信号  
        # self.setContextMenuPolicy(Qt.CustomContextMenu)  
        # self.customContextMenuRequested.connect(self.showContextMenu) 
         
        # 创建QMenu
        self.contextMenu = QMenu(self)  
        # self.contextMenu.setIconVisibleInMenu(False)
        for name in self.icon_dict:
            self.contextMenu.addAction(name)  
        # self.actionA = self.contextMenu.addAction('混合后的新形态')  
        # self.actionB = self.contextMenu.addAction('镜像形态键')  
        # self.actionC = self.contextMenu.addAction('镜像形态键(拓扑)') 

        for action in self.contextMenu.actions():
            action.setData(self.icon_dict[action.text()][0])
            action.triggered.connect(self.actionHandler)
            icon_path=self.icon_dict[action.text()][1]
            print('icon路径',icon_path)
            if icon_path !='':
                my_icon = icon_from_dat(icon_path)
                action.setIcon(my_icon)
    def handle_NewShapeFromMix(self):
        bpy.ops.object.shape_key_add(from_mix=True)
        return None  # 只执行一次
    def handle_Mirror(self):
        bpy.ops.object.shape_key_mirror(use_topology=False)
        return None  # 只执行一次
    def handle_MirrorTopo(self):
        bpy.ops.object.shape_key_mirror(use_topology=True)
        return None  # 只执行一次
    def handle_JoinAs(self):
        bpy.ops.object.join_shapes()
        return None  # 只执行一次
    def handle_Trans(self):
        bpy.ops.object.shape_key_transfer()
        return None  # 只执行一次
    def handle_DelteAll(self):
        bpy.ops.object.shape_key_remove(all=True, apply_mix=False)
        return None  # 只执行一次
    def handle_ApplyAll(self):
        bpy.ops.object.shape_key_remove(all=True, apply_mix=True)
        return None  # 只执行一次
    def handle_Lock(self):
        bpy.ops.object.shape_key_lock(action='LOCK')
        return None  # 只执行一次
    def handle_Unlock(self):
        bpy.ops.object.shape_key_lock(action='UNLOCK')
        return None  # 只执行一次
    def handle_MoveToTop(self):
        bpy.ops.object.shape_key_move(type='TOP')
        return None  # 只执行一次
    def handle_MoveToBottom(self):
        bpy.ops.object.shape_key_move(type='BOTTOM')
        return None  # 只执行一次
    def handle_ApplyToBasis(self):
        bpy.ops.cats_shapekey.shape_key_to_basis()
        return None  # 只执行一次
    def handle_RemoveUnuse(self):
        bpy.ops.cats_shapekey.shape_key_prune()
        return None  # 只执行一次
    def actionHandler(self):  
        name = self.sender().data()
        # 动态找到处理函数或从映射里取
        func = getattr(self, f"handle_{name}")
        bpy.app.timers.register(func)
    def mousePressEvent(self, event):
        # 如果是左键点击，显示菜单
        if event.button() == Qt.LeftButton:
            print("左键点击，显示菜单")
            self.contextMenu.exec_(QCursor.pos())
        # 调用父类的 mousePressEvent，确保按钮的默认行为仍然有效
        QPushButton.mousePressEvent(self, event)
class Item:
    def __init__(self, name, value, checked=False):
        self.name = name
        self.value = value
        self.checked = checked

class ListModel(QtCore.QAbstractListModel):
    NameRole = QtCore.Qt.UserRole + 1
    ValueRole = QtCore.Qt.UserRole + 2
    CheckedRole = QtCore.Qt.UserRole + 3

    def __init__(self, items=None, parent=None,value_min=0.0, value_max=1.0):
        super().__init__(parent)
        self._items = items or []
        self.value_min = value_min  # 新增最小值属性
        self.value_max = value_max  # 新增最大值属性
    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._items):
            return None
            
        item = self._items[index.row()]
        
        if role == QtCore.Qt.DisplayRole:
            return item.name
        elif role == ListModel.NameRole:
            return item.name
        elif role == ListModel.ValueRole:
            return item.value
        elif role == ListModel.CheckedRole:
            return item.checked
        return None

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._items)

    def roleNames(self):
        return {
            ListModel.NameRole: b"name",
            ListModel.ValueRole: b"value",
            ListModel.CheckedRole: b"checked"
        }

    def flags(self, index):
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable

    def setData(self, index, value, role):
        if not index.isValid():
            return False
        item = self._items[index.row()]
        if role == ListModel.NameRole:
            item.name = value
        elif role == ListModel.ValueRole:
            # 数值范围强制限制
            clamped_value = max(self.value_min, min(value, self.value_max))
            item.value = clamped_value
        elif role == ListModel.CheckedRole:
            item.checked = value
        else:
            return False
        self.dataChanged.emit(index, index, [role])
        return True

class ListView(QtWidgets.QListView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.last_double_click_pos = None

    def mouseDoubleClickEvent(self, event):
        self.last_double_click_pos = event.position().toPoint()
        super().mouseDoubleClickEvent(event)

class ItemDelegate(QtWidgets.QStyledItemDelegate):
    # DRAG_ROLE       = QtCore.Qt.UserRole + 99
    def __init__(self, parent=None, parent_wg=None,value_min=0.0, value_max=1.0,sensitivity=0.005):
        super().__init__(parent)
        self.parent_wg=parent_wg
        self.obj=parent_wg.obj
        self.value_min = value_min  # 最小值
        self.value_max = value_max  # 最大值
        # 每像素数值增量
        self.sensitivity = sensitivity

        # 拖拽状态
        self._dragging = False
        self._drag_start_x = 0
        self._drag_start_val = 0.0
    def calculate_regions(self, option):
        # print('区域计算')
        a=time()
        """区域计算方法，必须接受QStyleOptionViewItem参数"""
        total_width = option.rect.width() - 40
        return {
            "name": QtCore.QRect(
                option.rect.left() + 4, 
                option.rect.top(),
                int(total_width * 0.8), 
                option.rect.height()
            ),
            "value": QtCore.QRect(
                option.rect.left() + 4 + int(total_width * 0.8) + 4,
                option.rect.top(),
                int(total_width * 0.2),
                option.rect.height()
            ),
            "checkbox": QtCore.QRect(
                option.rect.right() - 24,
                option.rect.top(),
                20,
                option.rect.height()
            )
        }

    def paint(self, painter, option, index):
        a=time()
        # print('触发绘图事件',a-self.parent_wg.b)
        model = index.model()
        regions = self.calculate_regions(option)

        # 绘制背景
        bg_color = QtGui.QColor('#585858' if option.state & QtWidgets.QStyle.State_Selected else '#383838')
        painter.fillRect(option.rect, bg_color)

        # 绘制名称
        painter.setPen(QtGui.QColor('white'))
        painter.drawText(
            regions["name"], 
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
            model.data(index, ListModel.NameRole)
        )

        # 绘制数值（保留2位小数）
        painter.drawText(
            regions["value"],
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight,
            f"{model.data(index, ListModel.ValueRole):.2f}"
        )

        # 绘制复选框
        opt = QtWidgets.QStyleOptionButton()
        opt.rect = regions["checkbox"]
        opt.state = QtWidgets.QStyle.State_Enabled
        if model.data(index, ListModel.CheckedRole):
            opt.state |= QtWidgets.QStyle.State_On
        else:
            opt.state |= QtWidgets.QStyle.State_Off
        QtWidgets.QApplication.style().drawControl(QtWidgets.QStyle.CE_CheckBox, opt, painter)
        # print('绘图事件',time()-a)
    def setEditorData(self, editor, index):
        print('setEditorData')
        if isinstance(editor, QtWidgets.QLineEdit):
            field = editor.property("field")
            if field == "name":
                editor.setText(index.data(ListModel.NameRole))
            elif field == "value":
                editor.setText(f"{index.data(ListModel.ValueRole):.2f}")
            editor.setFocus(QtCore.Qt.OtherFocusReason)
    def createEditor(self, parent, option, index):
        print('createEditor')
        a=time()
        list_view = self.parent()
        if not isinstance(list_view, ListView) or not list_view.last_double_click_pos:
            return None

        click_pos = list_view.last_double_click_pos
        regions = self.calculate_regions(option)

        # 名称编辑器
        if regions["name"].contains(click_pos):
            name_data = index.data(ListModel.NameRole)
            print(f'Creating name editor with data: {name_data}')  # 调试输出
            editor = QtWidgets.QLineEdit(parent)
            print('index.data(ListModel.NameRole)',index.data(ListModel.NameRole))
            self.sk_name=index.data(ListModel.NameRole)
            editor.setText(index.data(ListModel.NameRole))
            # editor.setText(str(name_data))  # 强制转换为字符串
            editor.selectAll()
            editor.setProperty("field", "name")
            editor.setFocus(QtCore.Qt.OtherFocusReason)
            print('点击list view name',time()-a)
            return editor
            
        # 数值编辑器
        if regions["value"].contains(click_pos):
            editor = QtWidgets.QLineEdit(parent)
            # 设置带范围的验证器（最小值，最大值，小数位数）
            editor.setValidator(QtGui.QDoubleValidator(
                -inf, 
                inf, 
                2,  # 允许2位小数
                editor
            ))
            editor.setText(f"{index.data(ListModel.ValueRole):.2f}")
            editor.selectAll()
            editor.setProperty("field", "value")
            editor.setFocus(QtCore.Qt.OtherFocusReason)
            print('点击list view value',time()-a)
            return editor
        print('点击list view ',time()-a)
        return None

    def setModelData(self, editor, model, index):
        print('setModelData')
        if isinstance(editor, QtWidgets.QLineEdit):
            field = editor.property("field")
            if field == "name":
                model.setData(index, editor.text(), ListModel.NameRole)
                print('editor.text()',str(index.data(ListModel.NameRole)))
                if self.obj is not None:
                        self.obj.data.shape_keys.key_blocks[self.sk_name].name=editor.text()
                
            elif field == "value":
                try:
                    raw_value = float(editor.text())
                    # 二次范围验证确保数据正确性
                    clamped_value = max(self.value_min, min(raw_value, self.value_max))
                    model.setData(index, clamped_value, ListModel.ValueRole)
                    print('clamped_value',clamped_value)
                    if self.obj is not None:
                        self.obj.data.shape_keys.key_blocks[str(index.data(ListModel.NameRole))].value=clamped_value
                except ValueError:
                    pass
            editor.setFocus(QtCore.Qt.OtherFocusReason)
    def updateEditorGeometry(self, editor, option, index):
        print('updateEditorGeometry')
        regions = self.calculate_regions(option)
        if editor.property("field") == "name":
            editor.setGeometry(regions["name"])
        elif editor.property("field") == "value":
            editor.setGeometry(regions["value"])

    def editorEvent(self, event, model, option, index):
        print('editorEvent')
        if event.type() == QtCore.QEvent.MouseButtonRelease:
            regions = self.calculate_regions(option)
            if regions["checkbox"].contains(event.pos()):
                checked = model.data(index, ListModel.CheckedRole)
                model.setData(index, not checked, ListModel.CheckedRole)
                
                return True
        return super().editorEvent(event, model, option, index)

