from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QToolButton, QLabel, QFrame,QSizePolicy,QLayout
)
from PySide6.QtCore import Qt,QPropertyAnimation,QEasingCurve
class CollapsibleWidget(QWidget):
    def __init__(self, title="", content_layout: QLayout = None, parent=None):
        super().__init__(parent)

        # 折叠按钮
        self.toggle_button = QToolButton(text=title)
        self.toggle_button.setStyleSheet("""
            QToolButton {
                background-color: #333333;
                color: #ffffff;
                border: none;
                text-align: left;
                font-weight: bold;
            }
            QToolButton:hover {
                background-color: #444444;
            }
            QToolButton:pressed {
                background-color: #222222;
            }
        """)
        self.toggle_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(False)
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(Qt.RightArrow)
        self.toggle_button.clicked.connect(self.toggle_content)

        # 内容区域（动画目标）
        self.content_area = QWidget()
        self.content_area.setMaximumHeight(0)
        self.content_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
         # 如果外部传入 layout，就直接用；否则新建一个 VStack
        if content_layout is not None:
            self.content_area.setLayout(content_layout)
            self.content_layout = content_layout
        else:
            self.content_layout = QVBoxLayout(self.content_area)
            self.content_layout.setContentsMargins(0, 0, 0, 0)

        # 把按钮和 content_area 加到自己的主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.toggle_button)
        main_layout.addWidget(self.content_area)
        # 动画
        self.toggle_animation = QPropertyAnimation(self.content_area, b"maximumHeight", self)
        self.toggle_animation.setDuration(150)
        self.toggle_animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.toggle_animation.finished.connect(self._refresh_parent_layout)
        
        # 存储内容的“自然高度”
        self.content_height = 0

        # # 总布局
        # layout = QVBoxLayout(self)
        # layout.setSpacing(2)
        # layout.setContentsMargins(0, 0, 0, 0)
        # layout.addWidget(self.toggle_button)
        # layout.addWidget(self.content_area)

        # 初始化外部 layout
        # if content_layout is not None:
        #     self.set_content_layout(content_layout)

    def set_content_layout(self, layout: QLayout):
        """
        挂载外部传入的 layout 到 content_area，
        并测量出 content_height。
        """
        # 清除可能已有的子布局
        old = self.content_area.layout()
        if old:
            QWidget().setLayout(old)

        # 去除额外边距
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self.content_area.setLayout(layout)
        # 强制调整一次大小，拿到正确的 sizeHint
        self.content_area.adjustSize()
        self.content_height = self.content_area.sizeHint().height()

        # 如果当前是折叠态，保持隐藏
        if not self.toggle_button.isChecked():
            self.content_area.setMaximumHeight(0)

    def toggle_content(self):
        checked = self.toggle_button.isChecked()
        self.toggle_button.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)

        # 动态重新测一次——应对内容动态变化
        self.content_area.adjustSize()
        self.content_height = self.content_area.sizeHint().height()

        start_value = self.content_area.maximumHeight()
        end_value   = self.content_height if checked else 0

        self.toggle_animation.stop()
        self.toggle_animation.setStartValue(start_value)
        self.toggle_animation.setEndValue(end_value)
        self.toggle_animation.start()

    def _refresh_parent_layout(self):
        """动画结束后，让父布局重新布局，后续控件自动上移/下移"""
        parent = self.parentWidget()
        if parent and parent.layout():
            parent.layout().invalidate()
            parent.layout().activate()




import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QTreeWidget, QTreeWidgetItem, QToolButton, QFrame,
    QLayout, QPushButton, QSizePolicy, QAbstractScrollArea
)
from PySide6.QtCore import Qt, QSize


class QtCategoryButton(QToolButton):
    """
    Toggle button to expand/collapse associated QTreeWidgetItem.
    """
    def __init__(self, text, tree_widget, tree_item, parent=None):
        super().__init__(parent)
        self.setText(text)
        self.setCheckable(True)
        self.setChecked(True)
        self.tree_widget = tree_widget
        self.tree_item = tree_item
        self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.setArrowType(Qt.DownArrow)
        self.setStyleSheet("""
            QToolButton {
                background-color: #333333;
                color: #ffffff;
                border: none;
                text-align: left;
                font-weight: bold;
                padding: 4px;
            }
            QToolButton:hover {
                background-color: #444444;
            }
            QToolButton:pressed {
                background-color: #222222;
            }
        """)
        self.toggled.connect(self.on_toggled)

    def on_toggled(self, checked):
        self.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)
        self.tree_item.setExpanded(checked)
        # Trigger geometry and layout updates
        self.tree_widget.updateGeometry()
        parent = self.tree_widget.parentWidget()
        if parent:
            parent.updateGeometry()
            parent.adjustSize()
            layout = parent.layout()
            if layout:
                layout.invalidate()
                layout.activate()

    def sizeHint(self):
        hint = super().sizeHint()
        width = self.tree_widget.viewport().width()
        return QSize(width, hint.height())



class CategoryTreeWidget(QWidget):
    """
    Widget encapsulating a QTreeWidget with collapsible categories.
    Allows passing either a QWidget or a QLayout as the content of each category.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tree = QTreeWidget(self)
        self.tree.setColumnCount(1)
        self.tree.setHeaderHidden(True)
        self.tree.setRootIsDecorated(False)
        self.tree.setIndentation(0)
        self.tree.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.tree.setContentsMargins(0, 0, 0, 0)

        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tree)

        self.tree.itemCollapsed.connect(self._on_item_toggled)
        self.tree.itemExpanded.connect(self._on_item_toggled)

    def add_category(self,
                     title: str,
                     *,
                     content_widget: QWidget = None,
                     content_layout: QLayout = None,
                     buttons: list[str] | None = None):
        """
        添加一个可折叠的分类：
          - title: 分类标题
          - content_widget: 已有的 QWidget，直接作为折叠内容
          - content_layout: 如果你只有一个 QLayout，可传进来，内部会包一层 QWidget
          - buttons: （暂未使用，保留扩展）
        """
        # 1) 在 tree 上新建顶级 item + 标题按钮
        item = QTreeWidgetItem(self.tree)
        item.setExpanded(True)
        btn = QtCategoryButton(title, self.tree, item)
        self.tree.setItemWidget(item, 0, btn)

        # 2) 准备一个 container，它永远是新的 widget，不会跟你窗体的 layout 重复
        if content_widget is not None:
            container = content_widget
        else:
            # 用 QFrame 或 QWidget 都行，只要它是新的 container
            container = QFrame(self.tree)
            # 复用你传进来的 layout，但在 container 上重新 set 一次
            if content_layout is not None:
                content_layout.setContentsMargins(0, 0, 0, 0)
                content_layout.setSpacing(0)
                container.setLayout(content_layout)
            else:
                # 如果两者都没给，可以自己在这里新建一个 VBox 布局
                tmp = QVBoxLayout(container)
                tmp.setContentsMargins(0, 0, 0, 0)
                tmp.setSpacing(0)
                if buttons:
                    for txt in buttons:
                        btn = QPushButton(txt, container)
                        tmp.addWidget(btn)

        # 3) 挂到一个“子 item”上，这个子 item 只是用来装 container
        child = QTreeWidgetItem(item)
        child.setDisabled(True)  # 子项不响应点击
        self.tree.setItemWidget(child, 0, container)

        self.tree.resizeColumnToContents(0)
        # self._adjust_parent()

    def _on_item_toggled(self, item: QTreeWidgetItem):
        # 每次折叠／展开都触发
        self.tree.resizeColumnToContents(0)
        # 更新自己和外层布局
        self._adjust_parent()

    def _adjust_parent(self):
        # 通用的刷新布局逻辑
        self.updateGeometry()
        parent = self.parentWidget()
        if parent:
            parent.updateGeometry()
            parent.adjustSize()
            if parent.layout():
                parent.layout().invalidate()
                parent.layout().activate()

    def sizeHint(self) -> QSize:
        hint = self.tree.sizeHint()
        return QSize(hint.width(), hint.height())

