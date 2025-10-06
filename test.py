"""
overinfluence_ui_pyside6.py
PySide6 UI that reproduces the Blender panel:
- Threshold (int)
- Point size (float)
- Recompute Now (button)
- Toggle Draw (button)
- Cached object / Cached count labels

Integration:
- If run inside Blender's Python where `bpy` is importable and your Blender operator
  (view3d.recompute_overinfluence / view3d.toggle_draw_overinfluence) is registered,
  this UI will call those operators.
- Otherwise it runs in "standalone demo" mode.
"""

import sys
import traceback

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSpinBox, QDoubleSpinBox, QGroupBox, QMessageBox
)
from PySide6.QtCore import Qt, QTimer

# Try import bpy if running inside Blender's Python environment
try:
    import bpy
    IN_BLENDER = True
except Exception:
    bpy = None
    IN_BLENDER = False

# Simple state to hold cached info (mimics Blender-side cached values)
class AppState:
    def __init__(self):
        self.threshold = 4
        self.point_size = 6.0
        self.cached_obj_name = None
        self.cached_count = 0
        self.drawing_enabled = False

STATE = AppState()


class OverInfluenceWindow(QWidget):
    def __init__(self):
        super().__init__()
        # self.setWindowTitle("Over-Influence (On-Demand) — PySide6")
        self.setMinimumWidth(360)
        self._build_ui()
        self._connect_signals()

        # If in Blender, try to initialize UI from scene props if present
        if IN_BLENDER:
            self._try_load_from_blender_scene()

    def _build_ui(self):
        # central = QWidget()
        # self.setLayout(central)
        main_l = QVBoxLayout()
        # central.setLayout(main_l)

        # Parameters group
        params_box = QGroupBox("Parameters")
        params_l = QHBoxLayout()
        params_box.setLayout(params_l)

        # Threshold
        thr_layout = QVBoxLayout()
        thr_label = QLabel("Threshold")
        thr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_threshold = QSpinBox()
        self.spin_threshold.setRange(0, 64)
        self.spin_threshold.setValue(STATE.threshold)
        thr_layout.addWidget(thr_label)
        thr_layout.addWidget(self.spin_threshold)

        # Point size
        ps_layout = QVBoxLayout()
        ps_label = QLabel("Point Size")
        ps_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_point = QDoubleSpinBox()
        self.spin_point.setRange(1.0, 50.0)
        self.spin_point.setSingleStep(0.5)
        self.spin_point.setValue(STATE.point_size)
        ps_layout.addWidget(ps_label)
        ps_layout.addWidget(self.spin_point)

        params_l.addLayout(thr_layout)
        params_l.addLayout(ps_layout)

        main_l.addWidget(params_box)

        # Buttons row
        btn_row = QHBoxLayout()
        self.btn_recompute = QPushButton("Recompute Now")
        self.btn_toggle = QPushButton("Toggle Draw")
        btn_row.addWidget(self.btn_recompute)
        btn_row.addWidget(self.btn_toggle)
        main_l.addLayout(btn_row)

        # Cached info display
        info_box = QGroupBox("Cached Info")
        info_l = QVBoxLayout()
        info_box.setLayout(info_l)

        self.lbl_cached_obj = QLabel("Cached object: —")
        self.lbl_cached_count = QLabel("Cached count: 0")

        info_l.addWidget(self.lbl_cached_obj)
        info_l.addWidget(self.lbl_cached_count)

        main_l.addWidget(info_box)

        # Status message
        self.lbl_status = QLabel("")
        main_l.addWidget(self.lbl_status)

        # Spacer
        main_l.addStretch(1)
        self.setLayout(main_l)
    def _connect_signals(self):
        self.spin_threshold.valueChanged.connect(self._on_threshold_changed)
        self.spin_point.valueChanged.connect(self._on_point_size_changed)
        self.btn_recompute.clicked.connect(self._on_recompute_clicked)
        self.btn_toggle.clicked.connect(self._on_toggle_clicked)

    def _on_threshold_changed(self, val):
        STATE.threshold = val
        self._set_status(f"Threshold set to {val}")

        # If in Blender and you want to immediately sync the scene property:
        if IN_BLENDER:
            try:
                bpy.context.scene.overinfluence_threshold = val
            except Exception:
                # safe ignore if property isn't present
                pass

    def _on_point_size_changed(self, val):
        STATE.point_size = val
        self._set_status(f"Point size set to {val}")

        if IN_BLENDER:
            try:
                bpy.context.scene.overinfluence_point_size = val
            except Exception:
                pass

    def _on_recompute_clicked(self):
        """
        Called when user clicks Recompute Now.
        If running inside Blender and operator exists, call it.
        Otherwise simulate with demo values.
        """
        self._set_status("Recomputing...")

        if IN_BLENDER:
            try:
                # Try calling the operator you registered in Blender
                op = bpy.ops.view3d.recompute_overinfluence()
                # operator returns a set-like mapping; check typical result
                # We can't reliably get the cached_count global from the other module,
                # but if you modified the Blender operator to write results into
                # scene properties we can read them here. Try to read them:
                sc = bpy.context.scene
                cached_count = getattr(sc, "overinfluence_cached_count", None)
                cached_obj = getattr(sc, "overinfluence_cached_obj_name", None)

                if cached_count is not None:
                    STATE.cached_count = int(cached_count)
                else:
                    # fallback message-only update
                    STATE.cached_count = 0

                if cached_obj is not None:
                    STATE.cached_obj_name = str(cached_obj)
                else:
                    # fallback to active object name
                    try:
                        STATE.cached_obj_name = bpy.context.object.name
                    except Exception:
                        STATE.cached_obj_name = None

                self._refresh_cached_labels()
                self._set_status("Recompute request sent to Blender operator.")
            except Exception:
                tb = traceback.format_exc()
                self._set_status("Failed to call Blender operator. See console.")
                print(tb)
                QMessageBox.warning(self, "Blender call failed",
                                    "Calling `bpy.ops.view3d.recompute_overinfluence()` failed.\n"
                                    "Make sure the operator is registered and this script is running inside Blender.")
        else:
            # Standalone demo: simulate a recompute (for testing the UI)
            import random
            STATE.cached_obj_name = "DemoMesh"
            STATE.cached_count = random.randint(0, 200)
            self._refresh_cached_labels()
            self._set_status("Recomputed (demo).")

    def _on_toggle_clicked(self):
        """
        Toggle drawing on Blender side if possible; otherwise toggle demo flag.
        """
        if IN_BLENDER:
            try:
                bpy.ops.view3d.toggle_draw_overinfluence()
                # Try to read a scene property if the Blender operator writes one (optional)
                sc = bpy.context.scene
                drawing = getattr(sc, "overinfluence_drawing_enabled", None)
                if drawing is not None:
                    STATE.drawing_enabled = bool(drawing)
                else:
                    # toggle local flag as best-effort
                    STATE.drawing_enabled = not STATE.drawing_enabled
                self._set_status("Toggled drawing in Blender.")
            except Exception:
                tb = traceback.format_exc()
                print(tb)
                QMessageBox.warning(self, "Blender call failed",
                                    "Calling `bpy.ops.view3d.toggle_draw_overinfluence()` failed.\n"
                                    "Make sure the operator is registered and this script is running inside Blender.")
        else:
            STATE.drawing_enabled = not STATE.drawing_enabled
            self._set_status(f"Drawing {'enabled' if STATE.drawing_enabled else 'disabled'} (demo).")

        # update toggle button text to reflect state
        self._update_toggle_text()

    def _update_toggle_text(self):
        self.btn_toggle.setText("Toggle Draw: ON" if STATE.drawing_enabled else "Toggle Draw: OFF")

    def _refresh_cached_labels(self):
        self.lbl_cached_obj.setText(f"Cached object: {STATE.cached_obj_name if STATE.cached_obj_name else '—'}")
        self.lbl_cached_count.setText(f"Cached count: {STATE.cached_count}")

    def _set_status(self, text: str):
        self.lbl_status.setText(text)

    def _try_load_from_blender_scene(self):
        """
        Optional: if the Blender side stores its cached info in scene properties
        (e.g. overinfluence_cached_count, overinfluence_cached_obj_name, overinfluence_drawing_enabled),
        read them to populate the UI when the window starts.
        (The Blender script I provided earlier did not set scene props by default;
         if you want automatic sync, add assignments in the operator to write these props.)
        """
        try:
            sc = bpy.context.scene
            if hasattr(sc, "overinfluence_threshold"):
                self.spin_threshold.setValue(int(sc.overinfluence_threshold))
            if hasattr(sc, "overinfluence_point_size"):
                self.spin_point.setValue(float(sc.overinfluence_point_size))

            cnt = getattr(sc, "overinfluence_cached_count", None)
            objname = getattr(sc, "overinfluence_cached_obj_name", None)
            drawing = getattr(sc, "overinfluence_drawing_enabled", None)

            if cnt is not None:
                STATE.cached_count = int(cnt)
            if objname is not None:
                STATE.cached_obj_name = str(objname)
            if drawing is not None:
                STATE.drawing_enabled = bool(drawing)

            self._refresh_cached_labels()
            self._update_toggle_text()
        except Exception:
            # ignore errors (e.g. no context)
            pass


def main():
    app = QApplication(sys.argv)
    win = OverInfluenceWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
