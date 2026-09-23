from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QPushButton, QFormLayout,
    QDoubleSpinBox, QSpinBox, QCheckBox, QLabel, QGroupBox, QSplitter,
    QMessageBox)
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QPainter, QColor

from .core import Segment, Ornament, apply_template, load_templates
from .render import draw_ornament


class OrnamentCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(600, 600)
        self.ornament = None

    def set_ornament(self, orn):
        self.ornament = orn
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(255, 255, 255))
        if not self.ornament or not self.ornament.segments:
            return
        x0, y0, x1, y1 = self.ornament.bounds()
        w = max(1.0, x1 - x0); h = max(1.0, y1 - y0)
        scale = min(self.width() / w, self.height() / h) * 0.9
        p.translate((self.width() - w * scale) / 2 - x0 * scale,
                    (self.height() - h * scale) / 2 - y0 * scale)
        p.scale(scale, scale)
        draw_ornament(p, self.ornament)


class OrnamenterWidget(QWidget):
    ornamentGenerated = pyqtSignal(object)

    def __init__(self, templates_dir="templates", parent=None):
        super().__init__(parent)
        self.templates = load_templates(templates_dir)
        self.segment = Segment()
        self.ornament = None

        # IMPORTANT: param_widgets, params_box and params_layout must exist
        # BEFORE we connect currentTextChanged / call setCurrentRow(0),
        # because setCurrentRow emits the signal synchronously.
        self.param_widgets = {}

        # --- left panel ---
        left = QWidget()
        ll = QVBoxLayout(left)

        ll.addWidget(QLabel("Template"))
        self.template_list = QListWidget()
        for name in self.templates:
            self.template_list.addItem(name)
        ll.addWidget(self.template_list)

        self.params_box = QGroupBox("Parameters")
        self.params_layout = QFormLayout(self.params_box)
        ll.addWidget(self.params_box)

        # now it's safe to wire the signal and pick the initial item:
        # _rebuild_params will find params_layout and param_widgets ready
        self.template_list.currentTextChanged.connect(self._rebuild_params)
        if self.template_list.count():
            self.template_list.setCurrentRow(0)

        self.gen_btn = QPushButton("Generate")
        self.gen_btn.clicked.connect(self._generate)
        ll.addWidget(self.gen_btn)

        self.send_btn = QPushButton("→ Export")
        self.send_btn.setEnabled(False)
        self.send_btn.clicked.connect(
            lambda: self.ornamentGenerated.emit(self.ornament))
        ll.addWidget(self.send_btn)

        # --- canvas ---
        self.canvas = OrnamentCanvas()

        splitter = QSplitter()
        splitter.addWidget(left)
        splitter.addWidget(self.canvas)
        splitter.setStretchFactor(1, 1)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(splitter)

    def set_segment(self, seg: Segment):
        self.segment = seg
        self.ornament = None
        self.canvas.set_ornament(None)
        self.send_btn.setEnabled(False)

    def _current_template(self):
        item = self.template_list.currentItem()
        name = item.text() if item else None
        return self.templates.get(name)

    def _rebuild_params(self):
        # defensive guard: if the widget is (re)constructed in a way that
        # fires this signal before UI is ready, just do nothing
        if not hasattr(self, "params_layout") or not hasattr(self, "param_widgets"):
            return

        while self.params_layout.count():
            item = self.params_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self.param_widgets.clear()

        tpl = self._current_template()
        if not tpl:
            return
        p = tpl.get("params", {})
        for k, v in p.items():
            if isinstance(v, bool):
                w = QCheckBox(); w.setChecked(v)
            elif isinstance(v, int):
                w = QSpinBox(); w.setRange(-10000, 10000); w.setValue(v)
            else:
                w = QDoubleSpinBox()
                w.setRange(-100000, 100000); w.setDecimals(3); w.setValue(float(v))
            self.params_layout.addRow(k, w)
            self.param_widgets[k] = w

        # color_shift
        cs = tpl.get("color_shift", {}) or {}
        cb = QCheckBox("Enable color shift")
        cb.setChecked(bool(cs.get("enabled", False)))
        self.params_layout.addRow(cb)
        self.param_widgets["cs_enabled"] = cb
        for k in ("hue_shift_per_step", "saturation_shift",
                  "lightness_shift", "alpha_shift"):
            w = QDoubleSpinBox()
            w.setRange(-1000, 1000); w.setDecimals(3)
            w.setValue(float(cs.get(k, 0.0)))
            self.params_layout.addRow(k, w)
            self.param_widgets[k] = w

    def _collect_template(self):
        tpl = self._current_template()
        if not tpl:
            return None
        tpl = dict(tpl)
        params = dict(tpl.get("params", {}))
        for k, w in self.param_widgets.items():
            if k == "cs_enabled" or k in ("hue_shift_per_step", "saturation_shift",
                                          "lightness_shift", "alpha_shift"):
                continue
            params[k] = w.isChecked() if isinstance(w, QCheckBox) else w.value()
        tpl["params"] = params
        tpl["color_shift"] = {
            "enabled": self.param_widgets["cs_enabled"].isChecked(),
            "hue_shift_per_step": self.param_widgets["hue_shift_per_step"].value(),
            "saturation_shift": self.param_widgets["saturation_shift"].value(),
            "lightness_shift": self.param_widgets["lightness_shift"].value(),
            "alpha_shift": self.param_widgets["alpha_shift"].value(),
        }
        return tpl

    def _generate(self):
        if not self.segment.lines:
            return
        tpl = self._collect_template()
        if tpl is None:
            QMessageBox.warning(self, "Ornamenter", "No template selected")
            return
        self.ornament = apply_template(self.segment, tpl)
        self.canvas.set_ornament(self.ornament)
        self.send_btn.setEnabled(True)

    # --- public API ---
    def generate(self):
        self._generate()