from functools import partial
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
    QStyledItemDelegate, QStyle, QSplitter, QSizePolicy,QLineEdit,QAbstractItemView,QSpacerItem
)
from PySide6.QtCore import Qt, QStringListModel,QEvent,QAbstractListModel,QModelIndex,QRect,QSize
from PySide6.QtGui import QColor
import bpy

from .qt_toastwindow import ToastWindow

from ..utils.utils import undoable

class VgItem:
    def __init__(self, name, checked=False):
        self.name = name
        self.checked = checked
class VgListModel(QAbstractListModel):
    NameRole = Qt.UserRole + 1
    ValueRole = Qt.UserRole + 2
    CheckedRole = Qt.UserRole + 3

    def __init__(self, items=None, parent=None):
        super().__init__(parent)
        self._items = items or []

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._items):
            return None
            
        item = self._items[index.row()]
        
        if role == Qt.DisplayRole:
            return item.name
        elif role == VgListModel.NameRole:
            return item.name
        return None

    def rowCount(self, parent=QModelIndex()):
        return len(self._items)

    def roleNames(self):
        return {
            VgListModel.NameRole: b"name",
            VgListModel.ValueRole: b"value",
            VgListModel.CheckedRole: b"checked"
        }

    def flags(self, index):
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

    def setData(self, index, value, role):
        if not index.isValid():
            return False
        item = self._items[index.row()]
        if role == VgListModel.NameRole:
            item.name = value
        else:
            return False
        self.dataChanged.emit(index, index, [role])
        return True
class VgItemDelegate(QStyledItemDelegate):
    # DRAG_ROLE       = Qt.UserRole + 99
    def __init__(self, parent=None, main_widget=None):
        super().__init__(parent)
        self.qt_window=main_widget



        # 拖拽状态
        self._dragging = False
        self._drag_start_x = 0
        self._drag_start_val = 0.0
    def calculate_regions(self, option):
        # print('区域计算')
        # a=time()
        """区域计算方法，必须接受QStyleOptionViewItem参数"""
        total_width = option.rect.width() - 40
        return {
            "name": QRect(
                option.rect.left() + 4, 
                option.rect.top(),
                int(total_width ), 
                option.rect.height()
            ),
   
        }
    def sizeHint(self, option, index):
        return QSize(option.rect.width(), 20)
    def paint(self, painter, option, index):
        # a=time()
        # print('触发绘图事件',a-self.parent_wg.b)
        model = index.model()
        regions = self.calculate_regions(option)

        # 绘制背景
        bg_color = QColor('#585858' if option.state & QStyle.State_Selected else '#383838')
        painter.fillRect(option.rect, bg_color)

        # 绘制名称
        painter.setPen(QColor('white'))
        painter.drawText(
            regions["name"], 
            Qt.AlignVCenter | Qt.AlignLeft,
            model.data(index, VgListModel.NameRole)
        )

        # print('绘图事件',time()-a)
    def setEditorData(self, editor, index):
        # print('setEditorData')
        if isinstance(editor, QLineEdit):
            # print('正在输入')
            field = editor.property("field")
            if field == "name":
                editor.setText(index.data(VgListModel.NameRole))
            editor.setFocus(Qt.OtherFocusReason)
    def createEditor(self, parent, option, index):
        from .qt_shapekey import ListView
        list_view = self.parent().list_view
        if not isinstance(list_view, ListView) or not list_view.last_double_click_pos:
            return None

        click_pos = list_view.last_double_click_pos
        regions = self.calculate_regions(option)

        # 名称编辑器
        if regions["name"].contains(click_pos):
            editor = QLineEdit(parent)
            self.vg_name=index.data(VgListModel.NameRole)
            editor.setText(index.data(VgListModel.NameRole))
            editor.selectAll()
            editor.setProperty("field", "name")
            editor.setFocus(Qt.OtherFocusReason)
            return editor
            
        
        return None

    def setModelData(self, editor, model, index):
        # print('setModelData')
        if isinstance(editor, QLineEdit):
            field = editor.property("field")
            if field == "name":
                model.setData(index, editor.text(), VgListModel.NameRole)
                # print('editor.text()',str(index.data(VgListModel.NameRole)))
                if self.qt_window.obj is not None:
                        print('正在输入2')
                        self.qt_window.obj.vertex_groups[self.vg_name].name=editor.text()
                
            editor.setFocus(Qt.OtherFocusReason)
    def updateEditorGeometry(self, editor, option, index):
        regions = self.calculate_regions(option)
        if editor.property("field") == "name":
            editor.setGeometry(regions["name"])

    def enterEvent(self, event):
        
        return super().enterEvent(event)
    def leaveEvent(self, event):
        return super().leaveEvent(event)

class QtVertexGroup(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.qt_window=parent
        self._last_active_pose_bone=None
        # self.refresh_vertex_groups()
        self._build_ui()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    def _propagate_resize(self):
        # 从自己开始，一直往上调用 adjustSize()
        w = self
        while w is not None:
            w.adjustSize()
            # 如果是 layout 管理的容器，可以选做 w.layout().invalidate()
            w = w.parentWidget()

    # 然后在你的 eventFilter（或 mouseMoveEvent）里，设置完 new_h 之后：
    def eventFilter(self, obj, event):
        # … 你的 MouseMove 判断 …
        if event.type() == QEvent.MouseMove and self._dragging:
            delta = event.globalPosition().toPoint().y() - self._drag_start_pos.y()
            new_h = self._drag_start_h + delta
            new_h = max(self.minimumHeight(), min(self.maximumHeight(), new_h))
            self.setFixedHeight(new_h)

            # **关键**：让上层布局更新
            self._propagate_resize()
            return True
    def _build_ui(self):
        from .ui_widgets import Button
        from .qt_shapekey import ListView
        # 最外层垂直分割：上部为 List+右侧， 下部为固定控件
        outer_splitter = QSplitter(Qt.Vertical, self)
        outer_splitter.setChildrenCollapsible(False)
        outer_splitter.setHandleWidth(6)

        # —— 上半部分：水平布局 ListView + 右侧区 —— 
        top = QWidget()
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(0)
        
        # 可拉伸列表
        self.list_view = ListView(self)
        self.list_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        items = []
        self.model = VgListModel(items)
        self.delegate = VgItemDelegate(self,self.parent())
        self.list_view.setModel(self.model)
        self.list_view.setItemDelegate(self.delegate)
        self.list_view.setEditTriggers(
            QAbstractItemView.DoubleClicked
        )

        self.list_view.selectionModel().selectionChanged.connect(self.on_selection_changed)
        
        self.list_view.setFixedHeight(140)
        top_layout.addWidget(self.list_view)
        # top_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))
        vg_btn = QVBoxLayout()
        vg_btn.setContentsMargins(0, 0, 0, 0)
        vg_btn.setSpacing(0)
        for icon, name,tooltip in [
            ('add.svg','add_vg','新建'),
            ('remove.svg','rm_vg','移除'),
            ('vg_asign.png','vg_asign','把选中的顶点新建成顶点组'),
            ('vg_select_v.png','vg_select_v','选中当前组的顶点'),
            ('vg_rm_select.png','vg_rm_select','把选中的顶点移出顶点组'),
            ('vg_trans_modi.png','vg_trans_modi','添加数据传递修改器'),
            ('modi_shrink.png','vg_shrink_modi','添加缩裹修改器'),
        ]:
            btn = Button('', icon)
            btn.setProperty('bt_name', name)
            btn.setToolTip(tooltip)
            btn.clicked.connect(self.button_handler)
            vg_btn.addWidget(btn)
        vg_btn.addStretch()
        top_layout.addLayout(vg_btn)

        outer_splitter.addWidget(top)

        # —— 下半部分：固定高度控件区 —— 
        bottom = QWidget()
        # 按钮组
        vg_outer=QVBoxLayout(bottom)
        vg_outer.setContentsMargins(0, 0, 0, 0)
        vg_outer.setSpacing(0)
        vg_clean = QHBoxLayout()
        vg_clean.setContentsMargins(0, 0, 0, 0)
        vg_clean.setSpacing(0)
        for  name,bt_name,tooltip in [
            ['清','clean_zero','清理顶点组内的非法权重或0'],
            ['未','unused','删除没使用的顶点组\n(没形变或被修改器使用)'],
            ['零','rm_all_unused','删除0权重顶点组,所有物体'],
            ['rigify','vg_rigify','添加DEF-前缀'],
            ['普通','vg_normal','删除DEF-前缀'],
            ['剪切','vg_cut','复制权重并删除源'],
            ['粘贴','vg_paste','粘贴权重'],
        ]:
            btn = Button(name)
            btn.setProperty('bt_name', bt_name)
            btn.clicked.connect(self.button_handler)
            btn.setToolTip(tooltip)
            vg_clean.addWidget(btn)
        # vg_btn.addStretch()
        vg_mirror = QHBoxLayout()
        vg_mirror.setContentsMargins(0, 0, 0, 0)
        vg_mirror.setSpacing(0)
        self.btn_dict={}
        for  name,bt_name,tooltip in [
            ['←','vg_left','把顶点组顶点组复制到左边'],
            ['→','vg_right','把顶点组顶点组复制到右边'],
            [' | ','vg_middle','中间的顶点组,配合左右使用'],
            ['镜像','vg_mirror','把顶点组顶点组复制到箭头方向'],
            ['多','vg_mul','把一半的顶点组镜像到箭头方向'],
            ['选','vg_select','只镜像选中的顶点组\n姿态模式下选中骨骼'],
        ]:
            btn = Button(name)
            btn.setProperty('bt_name', bt_name)
            if bt_name in ['vg_left','vg_right','vg_middle','vg_mul','vg_select']:
                btn.setCheckable(True)
                btn.update_button_state(bt_name)
                btn.clicked.connect(self.button_check_handler)
            else:
                btn.clicked.connect(self.button_handler)
            btn.setToolTip(tooltip)
            vg_mirror.addWidget(btn)
            self.btn_dict[bt_name]=btn
        self.combo = QComboBox()
        self.combo.addItems(["最近", "面投射"])
        self.combo.currentTextChanged.connect(self.on_combo_changed)
        vg_mirror.addWidget(self.combo)
        vg_mirror.addStretch()

        
        vg_outer.addLayout(vg_clean)
        vg_outer.addLayout(vg_mirror)
        vg_outer.addStretch()
        outer_splitter.addWidget(bottom)

        # 初始比例：上部 70%，下部 30%
        outer_splitter.setStretchFactor(0, 5)
        outer_splitter.setStretchFactor(1, 5)

        # 把 splitter 放入主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(outer_splitter)
        self.setLayout(main_layout)
    def button_handler(self):
        self.msg='操作完成'
        name = self.sender().property('bt_name')
        func = getattr(self, f"handle_{name}", None)
        if func:
            self.qt_window.get_obj()
            def wrapped_func():
                func()  # 原函数执行
                # 然后注册 toast 显示（下一帧）
                def show_toast():
                    toast = ToastWindow(self.msg, parent=self.edit_widget)
                    toast.show_at_center_of()
                    return None  # 一次性定时器
                bpy.app.timers.register(show_toast)
                return None  # 一次性定时器

            bpy.app.timers.register(wrapped_func)
    def button_check_handler(self,):
        from .qt_global import GlobalProperty as GP 
        name = self.sender().property('bt_name')
        
        # 动态找到处理函数或从映射里取
        func = getattr(self, f"handle_{name}")
        bpy.app.timers.register(partial(func,name))
        print(f'点击 {name}',getattr(GP.get(),name))
    def on_combo_changed(self, text):
        from .qt_global import GlobalProperty as GP
        try:
            GP.get().vg_mirror_search = text=='最近'
            print(f"设置 vg_mirror_search = {text}")
        except Exception as e:
            print("设置失败：", e)
    @undoable
    def handle_add_vg(self):
        obj = self.qt_window.obj
        if obj:
            obj.vertex_groups.new(name="Group")
        self.refresh_vertex_groups()
    @undoable
    def handle_rm_vg(self):
        obj = self.qt_window.obj
        selected_indexes = self.list_view.selectedIndexes()
        if obj and selected_indexes:
            index = selected_indexes[0].row()
            vg = obj.vertex_groups[index]
            obj.vertex_groups.remove(vg)
        self.refresh_vertex_groups()
    @undoable
    def handle_vg_asign(self):
        bpy.ops.kourin.vg_asign_new_group()
        self.refresh_vertex_groups()
    @undoable
    def handle_vg_rm_select(self):
        bpy.ops.kourin.vg_rm_select()
        self.refresh_vertex_groups()
    @undoable
    def handle_vg_select_v(self):
        mode_t=bpy.context.object.mode
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.vertex_group_select()
        bpy.ops.object.mode_set(mode=mode_t)
        self.refresh_vertex_groups()
    @undoable
    def handle_vg_cut(self):
        # mode_t=bpy.context.object.mode
        # bpy.ops.object.mode_set(mode='EDIT')
        # bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.kourin.copy_vertex_group_weights()
        # bpy.ops.object.mode_set(mode=mode_t)
        self.refresh_vertex_groups()
    @undoable
    def handle_vg_paste(self):
        # mode_t=bpy.context.object.mode
        # bpy.ops.object.mode_set(mode='EDIT')
        # bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.kourin.paste_vertex_group_weights()
        # bpy.ops.object.mode_set(mode=mode_t)
        self.refresh_vertex_groups()
    @undoable
    def handle_vg_trans_modi(self):
        mode_t=bpy.context.object.mode
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.kourin.vg_trans_modi()
        bpy.ops.object.mode_set(mode=mode_t)
        self.refresh_vertex_groups()
    @undoable
    def handle_vg_shrink_modi(self):
        mode_t=bpy.context.object.mode
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.kourin.vg_shrink_modi()
        bpy.ops.object.mode_set(mode=mode_t)
        self.refresh_vertex_groups()
    def handle_vg_left(self,btname):
        print(btname)
        from .qt_global import GlobalProperty as GP 
        if not (GP.get().vg_middle or GP.get().vg_mul):
            print('不满足条件,返回',)
            print(f'左{GP.get().vg_left}右{GP.get().vg_right}')
            return None
        if GP.get().vg_left:
            print(f'左{GP.get().vg_left}右{GP.get().vg_right}')
            return
        GP.get().vg_left=True
        GP.get().vg_right=not GP.get().vg_left
        print('当前handle_左','左',GP.get().vg_left,'右',GP.get().vg_right)
        self.btn_dict[btname].update_button_state(btname)
        self.btn_dict['vg_right'].update_button_state('vg_right')
    def handle_vg_right(self,btname):
        from .qt_global import GlobalProperty as GP 
        if not (GP.get().vg_middle or GP.get().vg_mul):
            print('不满足条件,返回',)
            print(f'左{GP.get().vg_left}右{GP.get().vg_right}')
            return None
        if GP.get().vg_right:
            print(f'左{GP.get().vg_left}右{GP.get().vg_right}')
            return
        GP.get().vg_right=True
        GP.get().vg_left=not GP.get().vg_right
        print('当前handle_右','左',GP.get().vg_left,'右',GP.get().vg_right)
        self.btn_dict[btname].update_button_state(btname)
        self.btn_dict['vg_left'].update_button_state('vg_left')
    def handle_vg_select(self,btname):
        from .qt_global import GlobalProperty as GP 
        if not GP.get().vg_mul:
            return None
        GP.get().vg_select=not GP.get().vg_select
        self.btn_dict[btname].update_button_state(btname)
    def handle_vg_middle(self,btname):
        from .qt_global import GlobalProperty as GP 
        if GP.get().vg_middle:
            if GP.get().vg_left:
                GP.get().last_side='vg_left'
            if GP.get().vg_right:
                GP.get().last_side='vg_right'
            if not GP.get().vg_mul:
                GP.get().vg_left=False
                GP.get().vg_right=False
        else:
            if not (GP.get().vg_left or GP.get().vg_right):
                if len(GP.get().last_side):
                    if GP.get().last_side=='vg_left':
                        GP.get().vg_left=True
                    elif GP.get().last_side=='vg_right':
                        GP.get().vg_right=True
                    else:
                        GP.get().vg_left=True
                else:
                    GP.get().vg_left=True
                
        GP.get().vg_middle=not GP.get().vg_middle
        print(f'点击完成',getattr(GP.get(),btname),GP.get().vg_left,GP.get().vg_right)
        self.btn_dict[btname].update_button_state(btname)
        self.btn_dict['vg_left'].update_button_state('vg_left')
        self.btn_dict['vg_right'].update_button_state('vg_right')
    def handle_vg_mul(self,btname):
        from .qt_global import GlobalProperty as GP 
        if GP.get().vg_mul:
            GP.get().vg_select=False
        if GP.get().vg_mul:
            if GP.get().vg_left:
                GP.get().last_side='vg_left'
            if GP.get().vg_right:
                GP.get().last_side='vg_right'
            if not GP.get().vg_middle:
                GP.get().vg_left=False
                GP.get().vg_right=False
        else:
            if not (GP.get().vg_left or GP.get().vg_right):
                if len(GP.get().last_side):
                    if GP.get().last_side=='vg_left':
                        GP.get().vg_left=True
                    elif GP.get().last_side=='vg_right':
                        GP.get().vg_right=True
                    else:
                        GP.get().vg_left=True
                else:
                    GP.get().vg_left=True

        GP.get().vg_mul=not GP.get().vg_mul
        self.btn_dict['vg_mul'].update_button_state(btname)
        self.btn_dict['vg_left'].update_button_state('vg_left')
        self.btn_dict['vg_right'].update_button_state('vg_right')
        self.btn_dict['vg_select'].update_button_state('vg_select')
    def on_selection_changed(self):
        indexes = self.list_view.selectedIndexes()
        if not indexes:
            return
        obj = self.qt_window.obj
        if obj:
            index = indexes[0].row()
            obj.vertex_groups.active_index = index
    def refresh_vertex_groups(self):
        """同步 Blender 的顶点组到 Qt"""
        obj = self.qt_window.obj
        if obj and obj.type == 'MESH':
            names = [VgItem(vg.name) for vg in obj.vertex_groups]
        else:
            names = []
        self.model.beginResetModel()
        self.model._items = names
        self.model.endResetModel()
        self.update_vertex_group_index()
    def update_vertex_group_index(self):
        # if qt_window_widget is None:
        #     global qt_window
        # qt_window_widget=qt_window
        obj = bpy.context.view_layer.objects.active
        if obj is None:return None
        if obj.type!='MESH':return None
        # if self.qt_window is not None:
        index=self.model.index((obj.vertex_groups.active_index))
        self.list_view.setCurrentIndex(index)
        return None
    @undoable
    def handle_vg_mirror(self):
        bpy.ops.kourin.vg_mirror_weight()
        self.refresh_vertex_groups()
    @undoable
    def handle_clean_zero(self):
        bpy.ops.kourin.vg_clean_advanced()
    @undoable
    def handle_unused(self):
        bpy.ops.kourin.vg_clear_unused()
        self.refresh_vertex_groups()
    @undoable
    def handle_rm_zero(self):
        bpy.ops.kourin.vg_remove_zero()
        self.refresh_vertex_groups()
    def handle_rm_all_unused(self):
        bpy.ops.kourin.vg_rm_all_unused()
        self.refresh_vertex_groups()
    @undoable
    def handle_vg_rigify(self):
        bpy.ops.kourin.vg_metarig_to_rigify()
        self.refresh_vertex_groups()
    @undoable
    def handle_vg_normal(self):
        bpy.ops.kourin.vg_rigify_to_metarig()
        self.refresh_vertex_groups()

def armature_poll():
    if bpy.context.active_object is None:
        return False
    armatures = [obj for obj in bpy.context.selected_objects if obj.type == 'ARMATURE']
    return (len(armatures) == 2 and bpy.context.active_object.type == 'ARMATURE')
