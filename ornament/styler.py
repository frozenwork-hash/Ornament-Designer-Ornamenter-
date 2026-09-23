"""Style panel for the selected line.

Self-contained widget independent of Drawer. It is linked to a Line object
by reference: changes are written directly to the model, then styleChanged
is emitted.
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QLabel,
    QSlider, QSpinBox, QDoubleSpinBox, QPushButton, QColorDialog,
    QCheckBox, QComboBox, QRadioButton, QButtonGroup)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor

from .core import Line


# Dash presets: (name, pattern). None = "Custom" — pattern left untouched.
DASH_PRESETS = [
    ("Solid", []),
    ("Dash", [10.0, 5.0]),
    ("Dot", [1.0, 4.0]),
    ("Dash-dot", [10.0, 4.0, 1.0, 4.0]),
    ("Custom", None),
]


class StylerWidget(QWidget):
    styleChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._line: Line | None = None
        self._loading: bool = False
        self._build_ui()
        self.setEnabled(False)

    # ==================== UI ====================

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(8)

        root.addWidget(self._build_width_box())
        root.addWidget(self._build_opacity_box())
        root.addWidget(self._build_color_box())
        root.addWidget(self._build_dash_box())
        root.addWidget(self._build_cap_box())
        root.addWidget(self._build_join_box())
        root.addStretch(1)

    def _build_width_box(self) -> QGroupBox:
        box = QGroupBox("Width")
        lay = QHBoxLayout(box)
        # slider in tenths: 1..500  ⇔  0.1..50.0
        self.width_slider = QSlider(Qt.Horizontal)
        self.width_slider.setRange(1, 500)
        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(0.1, 50.0)
        self.width_spin.setSingleStep(0.1)
        self.width_spin.setDecimals(1)
        self.width_slider.valueChanged.connect(self._on_width_slider)
        self.width_spin.valueChanged.connect(self._on_width_spin)
        lay.addWidget(self.width_slider, 1)
        lay.addWidget(self.width_spin)
        return box

    def _build_opacity_box(self) -> QGroupBox:
        box = QGroupBox("Opacity")
        lay = QHBoxLayout(box)
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_spin = QSpinBox()
        self.opacity_spin.setRange(0, 100)
        self.opacity_spin.setSuffix(" %")
        self.opacity_slider.valueChanged.connect(self._on_opacity_slider)
        self.opacity_spin.valueChanged.connect(self._on_opacity_spin)
        lay.addWidget(self.opacity_slider, 1)
        lay.addWidget(self.opacity_spin)
        return box

    def _build_color_box(self) -> QGroupBox:
        box = QGroupBox("Color and alpha")
        lay = QVBoxLayout(box)
        self.color_btn = QPushButton("…")
        self.color_btn.clicked.connect(self._pick_color)
        lay.addWidget(self.color_btn)

        row = QHBoxLayout()
        row.addWidget(QLabel("Alpha"))
        self.alpha_slider = QSlider(Qt.Horizontal)
        self.alpha_slider.setRange(0, 255)
        self.alpha_slider.setValue(255)
        self.alpha_spin = QSpinBox()
        self.alpha_spin.setRange(0, 255)
        self.alpha_slider.valueChanged.connect(self._on_alpha_slider)
        self.alpha_spin.valueChanged.connect(self._on_alpha_spin)
        row.addWidget(self.alpha_slider, 1)
        row.addWidget(self.alpha_spin)
        lay.addLayout(row)
        return box

    def _build_dash_box(self) -> QGroupBox:
        box = QGroupBox("Dash")
        form = QFormLayout(box)

        self.dash_preset = QComboBox()
        for name, _ in DASH_PRESETS:
            self.dash_preset.addItem(name)
        self.dash_preset.currentIndexChanged.connect(self._on_dash_preset)
        form.addRow("Preset", self.dash_preset)

        self.dash_len = QDoubleSpinBox()
        self.dash_len.setRange(0.1, 200.0)
        self.dash_len.setDecimals(1)
        self.dash_len.setValue(10.0)
        self.dash_len.valueChanged.connect(self._on_dash_fields)
        form.addRow("Dash", self.dash_len)

        self.dash_gap = QDoubleSpinBox()
        self.dash_gap.setRange(0.1, 200.0)
        self.dash_gap.setDecimals(1)
        self.dash_gap.setValue(5.0)
        self.dash_gap.valueChanged.connect(self._on_dash_fields)
        form.addRow("Gap", self.dash_gap)

        self.dash_offset = QDoubleSpinBox()
        self.dash_offset.setRange(0.0, 500.0)
        self.dash_offset.setDecimals(1)
        self.dash_offset.valueChanged.connect(self._on_dash_offset)
        form.addRow("Offset", self.dash_offset)

        return box

    def _build_cap_box(self) -> QGroupBox:
        box = QGroupBox("Line caps")
        lay = QVBoxLayout(box)
        self.cap_group = QButtonGroup(self)
        for val, title in (("flat", "Flat"),
                           ("round", "Round"),
                           ("square", "Square")):
            rb = QRadioButton(title)
            rb.setProperty("cap_value", val)
            self.cap_group.addButton(rb)
            lay.addWidget(rb)
        self.cap_group.buttonClicked.connect(self._on_cap_changed)
        return box

    def _build_join_box(self) -> QGroupBox:
        box = QGroupBox("Joins")
        lay = QVBoxLayout(box)
        self.join_group = QButtonGroup(self)
        for val, title in (("miter", "Miter"),
                           ("round", "Round"),
                           ("bevel", "Bevel")):
            rb = QRadioButton(title)
            rb.setProperty("join_value", val)
            self.join_group.addButton(rb)
            lay.addWidget(rb)
        self.join_group.buttonClicked.connect(self._on_join_changed)
        return box

    # ==================== Public API ====================

    def set_line(self, line: Line | None):
        """Bind to the selected line. None → panel inactive."""
        self._line = line
        if line is None:
            self.setEnabled(False)
            return
        self.setEnabled(True)

        self._loading = True
        try:
            # width
            self.width_slider.setValue(int(round(line.stroke_width * 10)))
            self.width_spin.setValue(line.stroke_width)
            # opacity
            op = int(round(line.opacity * 100))
            self.opacity_slider.setValue(op)
            self.opacity_spin.setValue(op)
            # color and alpha
            self.alpha_slider.setValue(line.stroke_color[3])
            self.alpha_spin.setValue(line.stroke_color[3])
            self._update_color_swatch(line.stroke_color)
            # dash
            self._sync_dash_from_line(line)
            # caps
            for rb in self.cap_group.buttons():
                if rb.property("cap_value") == line.cap_style:
                    rb.setChecked(True)
                    break
            # joins
            for rb in self.join_group.buttons():
                if rb.property("join_value") == line.join_style:
                    rb.setChecked(True)
                    break
        finally:
            self._loading = False

    def clear(self):
        """Unbind."""
        self._line = None
        self.setEnabled(False)

    # ==================== Internal helpers ====================

    def _update_color_swatch(self, rgba):
        r, g, b, a = rgba
        # invert foreground for readability based on perceived luminance
        lum = (0.299 * r + 0.587 * g + 0.114 * b)
        fg = "#000" if lum > 140 else "#FFF"
        self.color_btn.setStyleSheet(
            f"background-color: rgba({r},{g},{b},{a});"
            f"color: {fg}; border: 1px solid #333; padding: 4px;")
        self.color_btn.setText(f"#{r:02X}{g:02X}{b:02X}  (a={a})")

    def _sync_dash_from_line(self, line: Line):
        pat = list(line.dash_pattern)
        # pick matching preset
        idx = len(DASH_PRESETS) - 1  # "Custom" by default
        for i, (_, preset) in enumerate(DASH_PRESETS):
            if preset is not None and list(preset) == pat:
                idx = i
                break
        self.dash_preset.setCurrentIndex(idx)
        # fill dash/gap fields
        ln = pat[0] if len(pat) >= 1 else 10.0
        gp = pat[1] if len(pat) >= 2 else 5.0
        self.dash_len.setValue(ln)
        self.dash_gap.setValue(gp)
        self.dash_offset.setValue(line.dash_offset)

    def _apply_simple_dash(self):
        """Write a simple [len, gap] pattern into the model (used for 'Custom')."""
        if self._line is None:
            return
        self._line.dash_pattern = [self.dash_len.value(), self.dash_gap.value()]
        self.styleChanged.emit()

    # ==================== Handlers ====================

    def _on_width_slider(self, v):
        if self._loading or self._line is None:
            return
        w = v / 10.0
        self.width_spin.blockSignals(True)
        self.width_spin.setValue(w)
        self.width_spin.blockSignals(False)
        self._line.stroke_width = w
        self.styleChanged.emit()

    def _on_width_spin(self, v):
        if self._loading or self._line is None:
            return
        self.width_slider.blockSignals(True)
        self.width_slider.setValue(int(round(v * 10)))
        self.width_slider.blockSignals(False)
        self._line.stroke_width = float(v)
        self.styleChanged.emit()

    def _on_opacity_slider(self, v):
        if self._loading or self._line is None:
            return
        self.opacity_spin.blockSignals(True)
        self.opacity_spin.setValue(v)
        self.opacity_spin.blockSignals(False)
        self._line.opacity = v / 100.0
        self.styleChanged.emit()

    def _on_opacity_spin(self, v):
        if self._loading or self._line is None:
            return
        self.opacity_slider.blockSignals(True)
        self.opacity_slider.setValue(v)
        self.opacity_slider.blockSignals(False)
        self._line.opacity = v / 100.0
        self.styleChanged.emit()

    def _pick_color(self):
        if self._loading or self._line is None:
            return
        c = self._line.stroke_color
        col = QColorDialog.getColor(QColor(*c), self, "Line color",
                                    QColorDialog.ShowAlphaChannel)
        if not col.isValid():
            return
        self._line.stroke_color = (col.red(), col.green(), col.blue(), col.alpha())
        self._loading = True
        self.alpha_slider.setValue(col.alpha())
        self.alpha_spin.setValue(col.alpha())
        self._loading = False
        self._update_color_swatch(self._line.stroke_color)
        self.styleChanged.emit()

    def _on_alpha_slider(self, v):
        if self._loading or self._line is None:
            return
        self.alpha_spin.blockSignals(True)
        self.alpha_spin.setValue(v)
        self.alpha_spin.blockSignals(False)
        r, g, b, _ = self._line.stroke_color
        self._line.stroke_color = (r, g, b, int(v))
        self._update_color_swatch(self._line.stroke_color)
        self.styleChanged.emit()

    def _on_alpha_spin(self, v):
        if self._loading or self._line is None:
            return
        self.alpha_slider.blockSignals(True)
        self.alpha_slider.setValue(v)
        self.alpha_slider.blockSignals(False)
        r, g, b, _ = self._line.stroke_color
        self._line.stroke_color = (r, g, b, int(v))
        self._update_color_swatch(self._line.stroke_color)
        self.styleChanged.emit()

    def _on_dash_preset(self, idx):
        if self._loading or self._line is None:
            return
        _, preset = DASH_PRESETS[idx]
        if preset is None:
            # "Custom" — take values from the fields
            self._apply_simple_dash()
            return
        # fill fields to match the preset (for convenient manual tweaking)
        self._loading = True
        if preset:
            self.dash_len.setValue(preset[0])
            if len(preset) >= 2:
                self.dash_gap.setValue(preset[1])
        self._loading = False
        self._line.dash_pattern = list(preset)
        self.styleChanged.emit()

    def _on_dash_fields(self, _v):
        """User manually changes dash/gap → switch to 'Custom'."""
        if self._loading or self._line is None:
            return
        if self.dash_preset.currentIndex() != len(DASH_PRESETS) - 1:
            self._loading = True
            self.dash_preset.setCurrentIndex(len(DASH_PRESETS) - 1)
            self._loading = False
        self._apply_simple_dash()

    def _on_dash_offset(self, v):
        if self._loading or self._line is None:
            return
        self._line.dash_offset = float(v)
        self.styleChanged.emit()

    def _on_cap_changed(self, btn):
        if self._loading or self._line is None:
            return
        val = btn.property("cap_value")
        if val:
            self._line.cap_style = val
            self.styleChanged.emit()

    def _on_join_changed(self, btn):
        if self._loading or self._line is None:
            return
        val = btn.property("join_value")
        if val:
            self._line.join_style = val
            self.styleChanged.emit()