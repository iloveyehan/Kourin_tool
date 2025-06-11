from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QToolButton, QLabel, QFrame,QSizePolicy,QLayout
)
from PySide6.QtCore import Qt,QPropertyAnimation,QEasingCurve

# class CollapsibleWidget(QWidget):
#     def __init__(self, title="", content_layout = None, parent=None):
#         super().__init__(parent)

#     # 按钮设置
#         self.toggle_button = QToolButton(text=title)
#         self.toggle_button.setStyleSheet("""
#             QToolButton {
#                 background-color: #333333;
#                 color: #ffffff;
#                 border: none;
#                 text-align: left;
#                 font-weight: bold;
#             }
#             QToolButton:hover {
#                 background-color: #444444;
#             }
#             QToolButton:pressed {
#                 background-color: #222222;
#             }
#         """)
#         self.toggle_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
#         self.toggle_button.setCheckable(True)
#         self.toggle_button.setChecked(False)
#         self.toggle_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
#         self.toggle_button.setArrowType(Qt.RightArrow)
#         self.toggle_button.clicked.connect(self.toggle_content)

#         # 内容区域
#         self.content_area = QFrame()
#         # self.content_area.setStyleSheet("background-color: #1e1e1e; border: 1px solid #333;")
#         self.content_area.setMaximumHeight(0)  # 开始时隐藏
#         self.content_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

#         self.toggle_animation = QPropertyAnimation(self.content_area, b"maximumHeight")
#         self.toggle_animation.setDuration(150)
#         self.toggle_animation.setEasingCurve(QEasingCurve.InOutQuad)

#         # 主布局
#         layout = QVBoxLayout(self)
#         layout.setSpacing(2)
#         layout.setContentsMargins(0, 0, 0, 0)
#         layout.addWidget(self.toggle_button)
#         layout.addWidget(self.content_area)

#     def toggle_content(self):
#         checked = self.toggle_button.isChecked()
#         self.toggle_button.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)

#         content_height = self.content_area.layout().sizeHint().height() if self.content_area.layout() else 100
#         start_value = 0 if checked else content_height
#         end_value = content_height if checked else 0

#         self.toggle_animation.stop()
#         self.toggle_animation.setStartValue(start_value)
#         self.toggle_animation.setEndValue(end_value)
#         self.toggle_animation.start()
#     def set_content_layout(self, layout):
#         # 设置内容区域的布局
#         self.content_area.setLayout(layout)
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
    Automatically adjusts its size when categories collapse/expand.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tree = QTreeWidget()
        self.tree.setColumnCount(1)
        self.tree.setHeaderHidden(True)
        self.tree.setRootIsDecorated(False)
        self.tree.setIndentation(0)
        self.tree.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)

        # allow widget to shrink vertically
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tree)

        self.tree.itemCollapsed.connect(self._on_item_toggled)
        self.tree.itemExpanded.connect(self._on_item_toggled)

    def add_category(self, title: str, content_layout: QLayout = None, buttons: list[str] | None = None):
        item = QTreeWidgetItem(self.tree)
        item.setExpanded(True)
        btn = QtCategoryButton(title, self.tree, item)
        self.tree.setItemWidget(item, 0, btn)

        container = QFrame(self.tree)
        if content_layout:
            container.setLayout(content_layout)
        else:
            from PySide6.QtWidgets import QVBoxLayout
            default_layout = QVBoxLayout(container)
            default_layout.setContentsMargins(0, 0, 0, 0)
            default_layout.setSpacing(0)
            if buttons:
                for txt in buttons:
                    default_layout.addWidget(QPushButton(txt))

        child = QTreeWidgetItem(item)
        child.setDisabled(True)
        self.tree.setItemWidget(child, 0, container)

        self.tree.resizeColumnToContents(0)
        self._adjust_parent()

    def _on_item_toggled(self, item):
        self.tree.resizeColumnToContents(0)
        self._adjust_parent()

    def _adjust_parent(self):
        # Update self and parent layouts
        self.updateGeometry()
        self.adjustSize()
        parent = self.parentWidget()
        if parent:
            parent.updateGeometry()
            parent.adjustSize()
            layout = parent.layout()
            if layout:
                layout.invalidate()
                layout.activate()

    def sizeHint(self):
        tree_hint = self.tree.sizeHint()
        return QSize(tree_hint.width(), tree_hint.height())



