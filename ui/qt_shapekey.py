import ctypes
from math import inf
from pathlib import Path
import sys
import bpy
from functools import partial
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtWidgets import QListView,QSizePolicy,QSizeGrip,QSplitter,QAbstractItemView,QLineEdit,QAbstractItemDelegate
from PySide6.QtCore import Qt, QTimer, QTranslator, QSize, QEvent,QByteArray,QPoint,QSortFilterProxyModel,Slot
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel,QHBoxLayout,QMenu
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QCompleter,
    QLabel, QSizeGrip,
)
from PySide6.QtGui import QCursor

from ..utils.utils import has_shapekey, undoable

from .qt_load_icon import icon_from_dat
class MenuButton(QPushButton):
    def __init__(self,parent = None,text='',icon_path=None,size=(20,20)):
        super().__init__(parent)
        self.setText(f"{text}")
        self.parent_wd=parent
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

        # 创建QMenu
        self.contextMenu = QMenu(self)  
        # self.contextMenu.setIconVisibleInMenu(False)
        for name in self.icon_dict:
            self.contextMenu.addAction(name)  
        for action in self.contextMenu.actions():
            action.setData(self.icon_dict[action.text()][0])
            action.triggered.connect(self.actionHandler)
            icon_path=self.icon_dict[action.text()][1]
            # print('icon路径',icon_path)
            if icon_path !='':
                my_icon = icon_from_dat(icon_path)
                action.setIcon(my_icon)
    def handle_NewShapeFromMix(self):
        bpy.ops.object.shape_key_add(from_mix=True)

    def handle_Mirror(self):
        bpy.ops.object.shape_key_mirror(use_topology=False)

    def handle_MirrorTopo(self):
        bpy.ops.object.shape_key_mirror(use_topology=True)

    def handle_JoinAs(self):
        bpy.ops.object.join_shapes()

    def handle_Trans(self):
        bpy.ops.object.shape_key_transfer()

    def handle_DelteAll(self):
        bpy.ops.object.shape_key_remove(all=True, apply_mix=False)

    def handle_ApplyAll(self):
        bpy.ops.object.shape_key_remove(all=True, apply_mix=True)
        # print(123)
    def handle_Lock(self):
        bpy.ops.object.shape_key_lock(action='LOCK')

    def handle_Unlock(self):
        bpy.ops.object.shape_key_lock(action='UNLOCK')

    def handle_MoveToTop(self):
        bpy.ops.object.shape_key_move(type='TOP')

    def handle_MoveToBottom(self):
        bpy.ops.object.shape_key_move(type='BOTTOM')

    def handle_ApplyToBasis(self):
        bpy.ops.cats_shapekey.shape_key_to_basis()

    def handle_RemoveUnuse(self):
        bpy.ops.cats_shapekey.shape_key_prune()

    def actionHandler(self):  
        from .ui_vrc_panel import qt_window,on_shape_key_index_change
        print('actionhandle')
        name = self.sender().data()
        # 动态找到处理函数或从映射里取
        func = getattr(self, f"handle_{name}")
        bpy.app.timers.register(func)
        bpy.app.timers.register(self.parent_wd.update_shape_keys)
        bpy.app.timers.register(partial(on_shape_key_index_change,qt_window))
# partial(on_shape_key_index_change,self.parent_wg)
    def mousePressEvent(self, event):
        # 如果是左键点击，显示菜单
        if event.button() == Qt.LeftButton:
            # print("左键点击，显示菜单")
            self.contextMenu.exec_(QCursor.pos())
        # 调用父类的 mousePressEvent，确保按钮的默认行为仍然有效
        QPushButton.mousePressEvent(self, event)
class Item:
    def __init__(self, name, value, checked=False):
        self.name = name
        self.value = value
        self.checked = checked
class ListView(QtWidgets.QListView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget=parent
        self.last_double_click_pos = None

    def mouseDoubleClickEvent(self, event):
        self.last_double_click_pos = event.position().toPoint()
        super().mouseDoubleClickEvent(event)
    def enterEvent(self, event):
        return super().enterEvent(event)
    def leaveEvent(self, event):

        return super().leaveEvent(event)

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
        self._drag_index = None
        self._drag_model = None

        self._timer = QTimer()
        self._timer.timeout.connect(self._onDragTimeout)

        # 安装全局事件过滤器
        QtWidgets.QApplication.instance().installEventFilter(self)
    def calculate_regions(self, option):
        # print('区域计算')
        # a=time()
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
        # a=time()
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
        # print('setEditorData')
        if isinstance(editor, QtWidgets.QLineEdit):
            # print('正在输入')
            field = editor.property("field")
            if field == "name":
                editor.setText(index.data(ListModel.NameRole))
            elif field == "value":
                editor.setText(f"{index.data(ListModel.ValueRole):.2f}")
            editor.setFocus(QtCore.Qt.OtherFocusReason)
    def createEditor(self, parent, option, index):
        # print('createEditor')
        # a=time()
        list_view = self.parent().list_view
        if not isinstance(list_view, ListView) or not list_view.last_double_click_pos:
            return None

        click_pos = list_view.last_double_click_pos
        regions = self.calculate_regions(option)

        # 名称编辑器
        if regions["name"].contains(click_pos):
            name_data = index.data(ListModel.NameRole)
            # print(f'Creating name editor with data: {name_data}')  # 调试输出
            editor = QtWidgets.QLineEdit(parent)
            # print('index.data(ListModel.NameRole)',index.data(ListModel.NameRole))
            self.sk_name=index.data(ListModel.NameRole)
            editor.setText(index.data(ListModel.NameRole))
            # editor.setText(str(name_data))  # 强制转换为字符串
            editor.selectAll()
            editor.setProperty("field", "name")
            editor.setFocus(QtCore.Qt.OtherFocusReason)
            # print('点击list view name',time()-a)
            editor.editingFinished.connect(lambda ed=editor: self.commit_and_close(ed))
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
            editor.editingFinished.connect(lambda ed=editor: self.commit_and_close(ed))
            # print('点击list view value',time()-a)
            return editor
        # print('点击list view ',time()-a)
        return None
    @Slot()
    def commit_and_close(self, editor):
        # 提交数据
        self.commitData.emit(editor)
        # 关闭 editor
        self.closeEditor.emit(editor, QAbstractItemDelegate.NoHint)
        # view = self.parent()  # 你在构造 delegate 时，parent 就是 list_view
        # view.closeEditor(editor, QtWidgets.QAbstractItemDelegate.NoHint)
    def setModelData(self, editor, model, index):
        # print('setModelData')
        if isinstance(editor, QtWidgets.QLineEdit):
            field = editor.property("field")
            if field == "name":
                model.setData(index, editor.text(), ListModel.NameRole)
                print('editor.text()',str(index.data(ListModel.NameRole)))
                if self.parent().parent().parent_wg.obj is not None:
                        self.parent().parent().parent_wg.obj.data.shape_keys.key_blocks[self.sk_name].name=editor.text()
                
            elif field == "value":
                try:
                    raw_value = float(editor.text())
                    # 二次范围验证确保数据正确性
                    clamped_value = max(self.value_min, min(raw_value, self.value_max))
                    model.setData(index, clamped_value, ListModel.ValueRole)
                    # print('clamped_value',clamped_value)
                    if self.parent().parent().parent_wg.obj is not None:
                        self.parent().parent().parent_wg.obj.data.shape_keys.key_blocks[str(index.data(ListModel.NameRole))].value=clamped_value
                except ValueError:
                    pass
            editor.setFocus(QtCore.Qt.OtherFocusReason)
    def updateEditorGeometry(self, editor, option, index):
        # print('updateEditorGeometry')
        regions = self.calculate_regions(option)
        if editor.property("field") == "name":
            editor.setGeometry(regions["name"])
        elif editor.property("field") == "value":
            editor.setGeometry(regions["value"])

    def editorEvent(self, event, model, option, index):
        # print('editorEvent')
        if event.type() == QtCore.QEvent.MouseButtonRelease:
            regions = self.calculate_regions(option)
            if regions["checkbox"].contains(event.pos()):
                checked = model.data(index, ListModel.CheckedRole)
                model.setData(index, not checked, ListModel.CheckedRole)
                return True
        # 先算出各区域
        regions = self.calculate_regions(option)
        # 只关注 value 区域
        if regions["value"].contains(event.pos()):
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                self._dragging = True
                self._drag_start_x = QCursor.pos().x()
                self._drag_start_val = model.data(index, ListModel.ValueRole)
                # 保存当前编辑的 index、model
                self._drag_index = index
                self._drag_model = model
                self._timer.start(16)  # 约 60 FPS
                return True

            elif event.type() == QEvent.MouseButtonRelease and self._dragging:
                self._timer.stop()
                self._dragging = False
                return True
        return super().editorEvent(event, model, option, index)
    def enterEvent(self, event):
    #     # self.grabKeyboard()
    #     # self.grabMouse()
        print('进入空间')
        
        return super().enterEvent(event)
    def leaveEvent(self, event):
    #     # self.releaseKeyboard()
    #     # self.releaseMouse()
        return super().leaveEvent(event)
    def _onDragTimeout(self):
        if not self._dragging:
            return
        dx = QCursor.pos().x() - self._drag_start_x
        new_val = self._drag_start_val + dx * self.sensitivity
        new_val = max(self.value_min, min(new_val, self.value_max))
        self._drag_model.setData(self._drag_index, new_val, ListModel.ValueRole)
        sk_name = self._drag_model.data(self._drag_index, ListModel.NameRole)
        self.parent().parent().parent_wg.obj.data.shape_keys.key_blocks[sk_name].value = new_val
    def eventFilter(self, obj, event):
        if self._dragging and event.type() == QtCore.QEvent.MouseButtonRelease:
            # 鼠标在任何地方释放，终止拖动
            self._timer.stop()
            self._dragging = False
            return True  # 拦截，不让其他组件处理
        return False  # 其他事件照常分发
class ResizableListView(QWidget):
    """
    一个带有可拖拽手柄的QListView容器，允许用户动态调整其高度，
    并能自动适应父容器的大小，防止拖出边界。
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        # 主布局
        self.parent_original_height = self.parentWidget().height() if parent else 0
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 列表视图
        self.list_view = ListView()
        self.list_view.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.list_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)


        # 将组件添加到布局
        self.main_layout.addWidget(self.list_view)
    
        self.setMinimumHeight(110)

    def setModel(self, model):
        self.list_view.setModel(model)
    def setItemDelegate(self, delegate):
        self.list_view.setItemDelegate(delegate)
    def setEditTriggers(self,Trigger):
        self.list_view.setEditTriggers(Trigger)
    def setCurrentIndex(self,index):
        self.list_view.setCurrentIndex(index)
    def view(self):
        return self.list_view
class Qt_shapekey(QWidget):
    def __init__(self, parent=None):
        from .ui_widgets import Button
        super().__init__(parent)
        self.parent_wg = parent

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(3,3,3,3)
        main_layout.setSpacing(4)

        

        # —— 同步集合区 —— 
        sync_col_layout = QHBoxLayout()
        self.sync_col_label = QLabel('同步集合')
        self.show_only_sk = Button('', 'solo_off.svg')
        self.show_only_sk.setProperty('bt_name', 'show_only_sk')
        self.show_only_sk.setCheckable(True)
        self.show_only_sk.toggled.connect(self.button_check_handler)
        self.use_sk_edit = Button('', 'editmode_hlt.svg')
        self.use_sk_edit.setProperty('bt_name', 'use_sk_edit')
        self.use_sk_edit.setCheckable(True)
        self.use_sk_edit.toggled.connect(self.button_check_handler)

        self.sync_col_combox = QComboBox()
        # 允许 completer, 但只读
        self.sync_col_combox.setEditable(True)
        self.sync_col_combox.setInsertPolicy(QComboBox.NoInsert)
        le = self.sync_col_combox.lineEdit()
        le.setReadOnly(True)
        le.setCursorPosition(0)
        # Completer
        self.completer = QCompleter([], self.sync_col_combox)
        self.completer.setFilterMode(Qt.MatchContains)
        self.completer.setCompletionMode(QCompleter.PopupCompletion)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.sync_col_combox.setCompleter(self.completer)
        self.clear_button = Button('×')
        self.clear_button.setFixedSize(20,20)
        self.clear_button.clicked.connect(self.clear_sync_col)

        sync_col_layout.addWidget(self.sync_col_label)
        sync_col_layout.addWidget(self.show_only_sk)
        sync_col_layout.addWidget(self.use_sk_edit)
        sync_col_layout.addWidget(self.sync_col_combox)
        sync_col_layout.addWidget(self.clear_button)
        sync_col_layout.addStretch()
        main_layout.addLayout(sync_col_layout)

        # —— 形态键列表区 —— 
        # 原始模型
        self.model = ListModel([])
        # 过滤代理
        # —— 搜索框 —— 
        self.search_edit = QLineEdit(self)
        self.search_edit.setPlaceholderText("🔍 搜索形态键")
        
        self.proxy = QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.model)
        self.proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy.setFilterRole(Qt.DisplayRole)
        # 将输入框与过滤器关联
        self.search_edit.textChanged.connect(self.proxy.setFilterFixedString)

        # 列表视图
        # from .ui_widgets import ResizableListView, ItemDelegate
        self.list_view = ResizableListView(self)
        self.list_view.setModel(self.proxy)
        self.delegate = ItemDelegate(self.list_view, parent)
        self.list_view.setItemDelegate(self.delegate)
        self.list_view.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked)
        self.list_view.list_view.clicked.connect(self.on_item_clicked)
        main_layout.addWidget(self.list_view)
        main_layout.addWidget(self.search_edit)
        # —— 按钮区 —— 
        btn_layout = QVBoxLayout()
        for icon, name in [
            ('add.svg','add_shape_key'),
            ('plus.svg','add_shape_key_here'),
            ('remove.svg','rm_shape_key'),
        ]:
            btn = Button('', icon)
            btn.setProperty('bt_name', name)
            btn.clicked.connect(self.button_handler)
            btn_layout.addWidget(btn)
        self.sk_menu = MenuButton(self, '', 'downarrow_hlt.svg')
        btn_layout.addWidget(self.sk_menu)
        for icon, name in [
            ('tria_up.svg','up_shape_key'),
            ('tria_down.svg','dm_shape_key'),
            ('panel_close.svg','set_0'),
        ]:
            btn = Button('', icon)
            btn.setProperty('bt_name', name)
            btn.clicked.connect(self.button_handler)
            btn_layout.addWidget(btn)
        btn_layout.addStretch()

        # 水平组合列表与按钮
        content_layout = QHBoxLayout()
        content_layout.addWidget(self.list_view)
        content_layout.addLayout(btn_layout)
        main_layout.addLayout(content_layout)
        
        # 尺寸手柄
        size_grip = QSizeGrip(self)
        main_layout.addWidget(size_grip, 0, Qt.AlignRight|Qt.AlignBottom)

        # 信号连接
        self.sync_col_combox.currentIndexChanged.connect(self.on_combobox_changed)

        # 首次填充
        self.update_collection_items()
        self.update_shape_keys()

    def update_collection_items(self):
        # 保存并恢复当前
        current = self.sync_col_combox.currentText()
        self.sync_col_combox.blockSignals(True)
        self.sync_col_combox.clear()
        # 递归获取所有集合
        def gather(col):
            lst = [col]
            for c in col.children:
                lst += gather(c)
            return lst
        all_cols = gather(bpy.context.scene.collection)
        names = [c.name for c in all_cols if c.name != 'Scene Collection']
        self.sync_col_combox.addItem('')
        for n in names:
            self.sync_col_combox.addItem(n)
        # Completer 更新
        self.completer.model().setStringList(names)
        # 恢复选中
        idx = self.sync_col_combox.findText(current)
        if idx >= 0:
            self.sync_col_combox.setCurrentIndex(idx)
        self.sync_col_combox.blockSignals(False)

    def update_shape_keys(self, new_sks=None):
        from .ui_vrc_panel import qt_window, on_shape_key_index_change

        if not qt_window:
            return

        # 1. 取出当前对象的所有 shape keys
        if not has_shapekey(qt_window.obj):
            items=[]
        else:
            sk_blocks = qt_window.obj.data.shape_keys.key_blocks

            # 2. 构造 Item 列表：用实际的 sk.value 而不是 0.0
            items = [Item(sk.name, sk.value) for sk in sk_blocks]
        

        # 3. 更新 Model
        self.model.beginResetModel()
        self.model._items = items
        self.model.endResetModel()

        # 4. 刷新过滤器 & Blender 激活 key
        self.proxy.invalidateFilter()
        bpy.app.timers.register(partial(on_shape_key_index_change, qt_window))

    # 以下为按钮和下拉框回调示例，需在类中实现
    def on_combobox_changed(self, index=None):
        from .ui_vrc_panel import qt_window
        from .qt_global import GlobalProperty as GP
        # print('更换同步集合')
        # 获取当前选中的文本
        selected_text = self.sync_col_combox.currentText()
        
        if selected_text =='':
            GP.get().obj_sync_col[qt_window.obj.as_pointer()]=None
            # qt_window.obj.mio3sksync.syncs=None
        else:
            GP.get().obj_sync_col[qt_window.obj.as_pointer()]=bpy.data.collections[f'{selected_text}']
        print(f'设置{selected_text},物体地址{qt_window.obj.as_pointer()}',GP.get().obj_sync_col[qt_window.obj.as_pointer()])
            # qt_window.obj.mio3sksync.syncs=bpy.data.collections[f'{selected_text}']
        # print(f"Selected item: {selected_text}")
        self.update_collection_items()
    def clear_sync_col(self):
        self.sync_col_combox.setCurrentIndex(-1)
        self.on_combobox_changed()
        self.update_collection_items()
    def button_handler(self):
        name = self.sender().property('bt_name')
        # print(f'dianjiele {name}')
        # 动态找到处理函数或从映射里取
        func = getattr(self, f"handle_{name}")
        bpy.app.timers.register(func)

    def button_check_handler(self,checked):
        # print('show_bone_name1')
        name = self.sender().property('bt_name')
        # print(f'dianjiele {name}')
        # 动态找到处理函数或从映射里取
        func = getattr(self, f"handle_{name}")
        bpy.app.timers.register(partial(func, checked))

    def on_item_clicked(self, index):
        import time
        a=time.time()
        item_text = self.model.data(index, Qt.DisplayRole)
        # print(f"点击了项: {item_text}")
        # 查找形态键的索引
        index = self.parent_wg.obj.data.shape_keys.key_blocks.find(item_text)
        # 设置激活的形态键
        if index != -1:
            self.parent_wg.obj.active_shape_key_index = index
    @undoable
    def handle_show_only_sk(self,checked):
        bpy.context.object.show_only_shape_key = checked
        if checked:
            self.show_only_sk.setStyleSheet("""
                QPushButton {
                    background-color: #4772b3;  /* 点击后常亮的颜色 */
                    color: white;
                }
            """)
        else:
            self.show_only_sk.setStyleSheet("""
                QPushButton {
                    background-color: none;  /* 恢复正常状态 */
                    color: black;
                }
            """)
    @undoable
    def handle_use_sk_edit(self,checked):
        bpy.context.object.use_shape_key_edit_mode = checked
        if checked:
            self.use_sk_edit.setStyleSheet("""
                QPushButton {
                    background-color: #4772b3;  /* 点击后常亮的颜色 */
                    color: white;
                }
            """)
        else:
            self.use_sk_edit.setStyleSheet("""
                QPushButton {
                    background-color: none;  /* 恢复正常状态 */
                    color: black;
                }
            """)
    @undoable
    def handle_add_shape_key(self):
        bpy.ops.object.shape_key_add(from_mix=False)
        self.update_shape_keys()
        return None
    @undoable
    def handle_add_shape_key_here(self):
        bpy.ops.mio3sk.add_key_current()
        self.update_shape_keys()
        return None
    @undoable
    def handle_rm_shape_key(self):
        bpy.ops.object.shape_key_remove(all=False)
        self.update_shape_keys()
        return None
    @undoable
    def handle_up_shape_key(self):
        bpy.ops.object.shape_key_move(type='UP')
        self.update_shape_keys()
        return None
    @undoable
    def handle_dm_shape_key(self):
        bpy.ops.object.shape_key_move(type='DOWN')
        self.update_shape_keys()
        return None
    @undoable
    def handle_set_0(self):
        bpy.ops.object.shape_key_clear()
        self.update_shape_keys()
        return None