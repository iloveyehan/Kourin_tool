from math import inf
import sys
from PySide6 import QtCore, QtGui, QtWidgets

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
    def __init__(self, parent=None, value_min=0.0, value_max=1.0):
        super().__init__(parent)
        self.value_min = value_min  # 最小值
        self.value_max = value_max  # 最大值
    def calculate_regions(self, option):
        """区域计算方法，必须接受QStyleOptionViewItem参数"""
        total_width = option.rect.width() - 40
        return {
            "name": QtCore.QRect(
                option.rect.left() + 4, 
                option.rect.top(),
                int(total_width * 0.5), 
                option.rect.height()
            ),
            "value": QtCore.QRect(
                option.rect.left() + 4 + int(total_width * 0.5) + 4,
                option.rect.top(),
                int(total_width * 0.5),
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

        # 绘制数值（保留1位小数）
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

    def createEditor(self, parent, option, index):
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
            editor.setText(index.data(ListModel.NameRole))
            editor.setText(str(name_data))  # 强制转换为字符串
            editor.selectAll()
            editor.setProperty("field", "name")
            return editor
            
        # 数值编辑器
        if regions["value"].contains(click_pos):
            editor = QtWidgets.QLineEdit(parent)
            # 设置带范围的验证器（最小值，最大值，小数位数）
            editor.setValidator(QtGui.QDoubleValidator(
                -inf, 
                inf, 
                2,  # 允许1位小数
                editor
            ))
            editor.setText(f"{index.data(ListModel.ValueRole):.2f}")
            editor.selectAll()
            editor.setProperty("field", "value")
            return editor

        return None

    def setModelData(self, editor, model, index):
        if isinstance(editor, QtWidgets.QLineEdit):
            field = editor.property("field")
            if field == "name":
                model.setData(index, editor.text(), ListModel.NameRole)
            elif field == "value":
                try:
                    raw_value = float(editor.text())
                    # 二次范围验证确保数据正确性
                    clamped_value = max(self.value_min, min(raw_value, self.value_max))
                    model.setData(index, clamped_value, ListModel.ValueRole)
                    print('clamped_value',clamped_value)
                except ValueError:
                    pass
    def updateEditorGeometry(self, editor, option, index):
        regions = self.calculate_regions(option)
        if editor.property("field") == "name":
            editor.setGeometry(regions["name"])
        elif editor.property("field") == "value":
            editor.setGeometry(regions["value"])

    def editorEvent(self, event, model, option, index):
        if event.type() == QtCore.QEvent.MouseButtonRelease:
            regions = self.calculate_regions(option)
            if regions["checkbox"].contains(event.pos()):
                checked = model.data(index, ListModel.CheckedRole)
                model.setData(index, not checked, ListModel.CheckedRole)
                return True
        return super().editorEvent(event, model, option, index)

