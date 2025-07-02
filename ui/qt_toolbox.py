from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QScrollArea, QFileDialog
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, Slot, QFile

from .qt_load_icon import pixmap_from_dat


class ToolPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.m_bIsExpanded = True

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 折叠按钮
        self.pushButtonFold = QPushButton("", self)
        self.pushButtonFold.setCheckable(True)
        self.pushButtonFold.setChecked(True)
        self.pushButtonFold.clicked.connect(self.onPushButtonFoldClicked)

        # 按钮布局：文本 + 图标
        btn_layout = QHBoxLayout(self.pushButtonFold)
        btn_layout.setContentsMargins(0, 0, 5, 0)
        

        # 箭头图标
        self.m_pLabel = QLabel(self)
        self.m_pLabel.setFixedSize(20, 20)
        self._updateArrowIcon()
        btn_layout.addWidget(self.m_pLabel)
        btn_layout.addStretch(1)
        main_layout.addWidget(self.pushButtonFold)

        # 内容容器
        self.widgetContent = QWidget(self)
        content_layout = QVBoxLayout(self.widgetContent)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(2)
        self.verticalLayoutContent = content_layout

        main_layout.addWidget(self.widgetContent)

        # 加载样式表
        qss_file = QFile(":/qss/toolpage.qss")
        if qss_file.open(QFile.ReadOnly):
            self.setStyleSheet(qss_file.readAll().data().decode())
        qss_file.close()
        self.collapse()
    @Slot()
    def onPushButtonFoldClicked(self):
        if self.m_bIsExpanded:
            self.collapse()
        else:
            self.expand()

    def expand(self):
        self.widgetContent.show()
        self.m_bIsExpanded = True
        self.pushButtonFold.setChecked(True)
        self._updateArrowIcon()

    def collapse(self):
        self.widgetContent.hide()
        self.m_bIsExpanded = False
        self.pushButtonFold.setChecked(False)
        self._updateArrowIcon()

    def addWidget(self, title: str, widget: QWidget):
        self.pushButtonFold.setText(title)
        self.verticalLayoutContent.addWidget(widget)

    def _updateArrowIcon(self):
        icon_path = "tria_down.svg" if self.m_bIsExpanded else "tria_right.svg"
        # pix = QPixmap(icon_path).scaled(
        #     self.m_pLabel.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation
        # )
        pix=pixmap_from_dat(icon_path)
        self.m_pLabel.setPixmap(pix)


class ToolBox(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 滚动区
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        main_layout.addWidget(scroll)

        # 滚动区内容容器
        container = QWidget(self)
        self.m_pContentVBoxLayout = QVBoxLayout(container)
        self.m_pContentVBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.m_pContentVBoxLayout.setSpacing(2)
        self.m_pContentVBoxLayout.addStretch(1)

        scroll.setWidget(container)

    def addWidget(self, title: str, widget: QWidget):
        page = ToolPage(self)
        page.addWidget(title, widget)
        # 在倒数第一个 Stretch 之前插入
        self.m_pContentVBoxLayout.insertWidget(
            self.m_pContentVBoxLayout.count() - 1, page
        )
# import sys
# from PySide6.QtWidgets import QApplication, QLabel
# # 假设你把前面的代码保存为 pyside6_toolbox.py 并放在同级目录

# if __name__ == "__main__":
#     app = QApplication(sys.argv)

#     # 创建一个 ToolBox 实例
#     toolbox = ToolBox()
#     toolbox.setWindowTitle("我的工具箱示例")
#     toolbox.resize(300, 400)

#     # 向 toolbox 添加几个示例面板
#     toolbox.addWidget("面板 A", QLabel("这是面板 A 的内容"))
#     toolbox.addWidget("面板 B", QLabel("这是面板 B 的内容"))
#     toolbox.addWidget("面板 C", QLabel("这是面板 C 的内容"))

#     toolbox.show()
#     sys.exit(app.exec())
