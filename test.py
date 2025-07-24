import sys, math
from functools import partial
from PySide6.QtWidgets import QApplication, QWidget, QPushButton, QGraphicsDropShadowEffect
from PySide6.QtGui import QPainter, QColor, QPen, QIcon
from PySide6.QtCore import Qt, QPointF, QRectF, QSize

class DraggableCircularMenu(QWidget):
    def __init__(self, radius=100, button_infos=None, parent=None):
        super().__init__(parent)
        self.radius = radius
        size = radius * 2 + 40
        self.setFixedSize(size, size)
        self.buttons = []
        self._drag_button = None
        self._drag_offset = QPointF()
        self.button_infos = button_infos.copy() if button_infos else []
        self._init_ui()
        self._dragging_widget = False
        self._widget_drag_offset = QPointF()

    def _init_ui(self):
        for btn in self.buttons:
            btn.deleteLater()
        self.buttons.clear()

        n = len(self.button_infos)
        if n == 0:
            return

        center = QPointF(self.width() / 2, self.height() / 2)

        # 分布在右半边（从 -90° 到 +90°）
        start_angle = -math.pi / 2  # -90°
        angle_span = math.pi        # 180°
        angle_step = angle_span / (n - 1) if n > 1 else 0

        for i, (icon_or_text, cb) in enumerate(self.button_infos):
            angle = start_angle + angle_step * i
            x = center.x() + math.cos(angle) * self.radius
            y = center.y() + math.sin(angle) * self.radius

            btn = QPushButton(self)
            if isinstance(icon_or_text, str) and icon_or_text.endswith(('.png', '.svg')):
                btn.setIcon(QIcon(icon_or_text))
                btn.setIconSize(QSize(24, 24))
            else:
                btn.setText(icon_or_text)
            btn.setFixedSize(40, 40)
            btn.move(int(x - btn.width() / 2), int(y - btn.height() / 2))
            btn.setStyleSheet("""
                QPushButton {
                    border: none;
                    background-color: #444;
                    color: white;
                    border-radius: 20px;
                }
                QPushButton:hover {
                    background-color: #666;
                }
                QPushButton:pressed {
                    background-color: #222;
                }
            """)
            effect = QGraphicsDropShadowEffect(btn)
            effect.setBlurRadius(10)
            effect.setOffset(2, 2)
            btn.setGraphicsEffect(effect)
            btn.clicked.connect(partial(cb, i))
            btn.installEventFilter(self)
            self.buttons.append(btn)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor('#888888'), 4)
        painter.setPen(pen)
        rect = QRectF(20, 20, self.radius * 2, self.radius * 2)
        painter.drawEllipse(rect)

    def _on_button_drop(self, btn):
        center = QPointF(self.width() / 2, self.height() / 2)
        btn_center = QPointF(btn.x() + btn.width() / 2, btn.y() + btn.height() / 2)
        dx = btn_center.x() - center.x()
        dy = btn_center.y() - center.y()
        angle = math.atan2(dy, dx) + math.pi / 2
        if angle < 0:
            angle += 2 * math.pi
        n = len(self.buttons)
        target_idx = int(round(angle / (2 * math.pi) * n)) % n
        src_idx = self.buttons.index(btn)
        self.button_infos[src_idx], self.button_infos[target_idx] = \
            self.button_infos[target_idx], self.button_infos[src_idx]
        self._init_ui()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    def callback(idx, *_):
        print(f"Button {idx} clicked")
    infos = ['A', 'B', 'C', 'D', 'E', 'F']
    button_infos = [(label, callback) for label in infos]
    window = QWidget()
    window.setWindowTitle("Draggable Circular Menu")
    window.setGeometry(100, 100, 400, 400)
    menu = DraggableCircularMenu(radius=120, button_infos=button_infos, parent=window)
    menu.move(100, 100)
    window.show()
    sys.exit(app.exec())
