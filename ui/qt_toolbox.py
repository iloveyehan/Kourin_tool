from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QScrollArea, QFileDialog, QScrollBar
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, Slot

from .qt_load_icon import pixmap_from_dat

# —————— 1. 样式表（内嵌） ——————
SCROLLBAR_QSS = """
QScrollBar:vertical {
    background: transparent;
    width: 3px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: rgba(100,100,100,180);
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}
"""

# —————— 2. 悬浮滚动条 ——————
class SuspendedScrollBar(QScrollBar):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.setStyleSheet(SCROLLBAR_QSS)
        self.setRange(0, 0)
        self.hide()

    @Slot(int)
    def slt_valueChange_scrollBar(self, val):
        self.setValue(val)

    @Slot(int, int)
    def slt_rangeChanged(self, minimum, maximum):
        self.setMinimum(minimum)
        self.setMaximum(maximum)
        total = maximum - minimum
        if total > 0:
            vis_h = self.parent().viewport().height()
            ratio = vis_h / (vis_h + total)
            self.setPageStep(int(ratio * (self.height() + total)))
            self.show()
        else:
            self.setPageStep(0)
            self.hide()

# —————— 3. 悬浮滚动区域 ——————
class SuspendedScrollArea(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        # 关闭内置滚动条
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # 创建并定位自定义滚动条
        self._vbar = SuspendedScrollBar(Qt.Vertical, self)
        # 同步信号—槽
        orig_vbar = super().verticalScrollBar()
        orig_vbar.valueChanged.connect(self._vbar.slt_valueChange_scrollBar)
        orig_vbar.rangeChanged.connect(self._vbar.slt_rangeChanged)
        self._vbar.valueChanged.connect(orig_vbar.setValue)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 把悬浮滚动条贴到右侧
        w = self.viewport().width()
        h = self.viewport().height()
        # mapToParent 因为 scrollarea 有 frame
        geo = self.viewport().geometry()
        x = geo.x() + geo.width() - 3
        y = geo.y()
        self._vbar.setGeometry(x, y, 3, h)

    def enterEvent(self, event):
        # 鼠标进入时，如果需要就显示
        if self._vbar.maximum() > 0:
            self._vbar.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._vbar.hide()
        super().leaveEvent(event)


# —————— 4. 你的原有 ToolPage ——————
class ToolPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.m_bIsExpanded = True
        self.mouse_in = False
        self.setFocusPolicy(Qt.StrongFocus)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.pushButtonFold = QPushButton("", self)
        self.pushButtonFold.setCheckable(True)
        self.pushButtonFold.setChecked(True)
        self.pushButtonFold.clicked.connect(self.onPushButtonFoldClicked)

        btn_layout = QHBoxLayout(self.pushButtonFold)
        btn_layout.setContentsMargins(0, 0, 5, 0)
        self.m_pLabel = QLabel(self)
        self.m_pLabel.setFixedSize(20, 20)
        self._updateArrowIcon()
        btn_layout.addWidget(self.m_pLabel)
        btn_layout.addStretch(1)
        main_layout.addWidget(self.pushButtonFold)

        self.widgetContent = QWidget(self)
        content_layout = QVBoxLayout(self.widgetContent)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(2)
        self.verticalLayoutContent = content_layout
        main_layout.addWidget(self.widgetContent)

        # 加载原有 qss
        # from PySide6.QtCore import QFile
        # qss_file = QFile(":/qss/toolpage.qss")
        # if qss_file.open(QFile.ReadOnly):
        #     self.setStyleSheet(qss_file.readAll().data().decode())
        # qss_file.close()
        self.setStyleSheet(SCROLLBAR_QSS)
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
        pix = pixmap_from_dat(icon_path)
        self.m_pLabel.setPixmap(pix)

    def enterEvent(self, event):
        self.mouse_in = True
        self.setFocus()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.mouse_in = False
        super().leaveEvent(event)

    def keyPressEvent(self, event):
        if self.mouse_in and event.key() == Qt.Key_A:
            self.onPushButtonFoldClicked()
        super().keyPressEvent(event)


# —————— 5. 在 ToolBox 中使用 SuspendedScrollArea ——————
class ToolBox(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 用自定义悬浮滚动区
        scroll = SuspendedScrollArea(self)
        scroll.setWidgetResizable(True)
        main_layout.addWidget(scroll)

        container = QWidget(self)
        self.m_pContentVBoxLayout = QVBoxLayout(container)
        self.m_pContentVBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.m_pContentVBoxLayout.setSpacing(2)
        self.m_pContentVBoxLayout.addStretch(1)

        scroll.setWidget(container)

    def addWidget(self, title: str, widget: QWidget):
        page = ToolPage(self)
        page.addWidget(title, widget)
        # 在 最后一条 stretch 之前 插入
        self.m_pContentVBoxLayout.insertWidget(
            self.m_pContentVBoxLayout.count() - 1, page
        )
