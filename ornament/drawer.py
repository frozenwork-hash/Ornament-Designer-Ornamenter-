import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QToolBar, QAction, QActionGroup,
    QFormLayout, QRadioButton, QButtonGroup, QSlider, QSpinBox,
    QPushButton, QColorDialog, QCheckBox, QComboBox, QDialog,
    QDialogButtonBox, QTableWidget, QTableWidgetItem, QDoubleSpinBox,
    QGroupBox, QMessageBox, QScrollArea)
from PyQt5.QtCore import Qt, QPointF, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QColor

from .core import (Point, Segment, StraightLine, ArcLine, Gradient,
                   save_segment, load_segment)
from .render import draw_segment, line_to_path
from .styler import StylerWidget
from .segment_io import SegmentIOWidget


# ==================== Canvas ====================

class DrawerCanvas(QWidget):
    pointClicked = pyqtSignal(int)
    lineSelected = pyqtSignal(object)
    deselected = pyqtSignal()
    segmentChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(800, 600)
        self.setMouseTracking(True)

        self.segment = Segment()
        self.left_points = [Point(200, y) for y in (100, 200, 300, 400, 500)]
        self.right_points = [Point(600, y) for y in (100, 200, 300, 400, 500)]
        self.all_points = self.left_points + self.right_points
        self.segment.base_points = list(self.all_points)

        self.pending_idx = None
        self.selected_line = None
        self.pending_type = "straight"

    def set_segment(self, seg: Segment):
        self.segment = seg
        self.selected_line = None
        self.pending_idx = None
        self.update()

    def _hit_point(self, x, y):
        for i, p in enumerate(self.all_points):
            if (x - p.x) ** 2 + (y - p.y) ** 2 <= 10 ** 2:
                return i
        return -1

    def _line_distance(self, line, x, y):
        if isinstance(line, ArcLine):
            p0, p2, c = line.start_point, line.end_point, line.control_point()
            best = 1e18
            for i in range(21):
                t = i / 20.0
                mt = 1 - t
                px = mt * mt * p0.x + 2 * mt * t * c.x + t * t * p2.x
                py = mt * mt * p0.y + 2 * mt * t * c.y + t * t * p2.y
                d = (px - x) ** 2 + (py - y) ** 2
                if d < best:
                    best = d
            return best ** 0.5
        x1, y1 = line.start_point.x, line.start_point.y
        x2, y2 = line.end_point.x, line.end_point.y
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy
        if L2 == 0:
            return ((x - x1) ** 2 + (y - y1) ** 2) ** 0.5
        t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / L2))
        px, py = x1 + t * dx, y1 + t * dy
        return ((x - px) ** 2 + (y - py) ** 2) ** 0.5

    def _hit_line(self, x, y):
        for line in sorted(self.segment.lines, key=lambda l: -l.z_index):
            if self._line_distance(line, x, y) < 8:
                return line
        return None

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(250, 250, 250))

        p.setPen(QPen(QColor(230, 230, 230), 1))
        for x in range(0, self.width(), 50):
            p.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), 50):
            p.drawLine(0, y, self.width(), y)

        p.setPen(QPen(QColor(200, 200, 200), 1, Qt.DashLine))
        p.drawLine(400, 0, 400, self.height())

        draw_segment(p, self.segment)

        if self.selected_line:
            pen = QPen(QColor(0, 150, 255), self.selected_line.stroke_width + 4)
            pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawPath(line_to_path(self.selected_line))

        for i, pt in enumerate(self.all_points):
            p.setBrush(QColor(255, 100, 100) if self.pending_idx == i
                       else QColor(255, 255, 255))
            p.setPen(QPen(QColor(30, 30, 30), 2))
            p.drawEllipse(QPointF(pt.x, pt.y), 6, 6)

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        idx = self._hit_point(e.x(), e.y())
        if idx >= 0:
            self.pointClicked.emit(idx)
            return
        line = self._hit_line(e.x(), e.y())
        if line is not None:
            self.selected_line = line
            self.lineSelected.emit(line)
            self.update()
            return
        self.selected_line = None
        self.pending_idx = None
        self.deselected.emit()
        self.update()

    def handle_point(self, idx):
        if self.pending_idx is None:
            self.pending_idx = idx
            self.update()
            return
        if self.pending_idx == idx:
            self.pending_idx = None
            self.update()
            return
        a = self.all_points[self.pending_idx]
        b = self.all_points[idx]
        if self.pending_type == "arc":
            line = ArcLine(Point(a.x, a.y), Point(b.x, b.y), bend=40.0)
        else:
            line = StraightLine(Point(a.x, a.y), Point(b.x, b.y))
        self.segment.add_line(line)
        self.pending_idx = None
        self.selected_line = line
        self.lineSelected.emit(line)
        self.segmentChanged.emit()


# ==================== Gradient editor dialog ====================

class GradientEditor(QDialog):
    def __init__(self, gradient: Gradient, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit gradient")
        self.resize(360, 320)
        g = gradient or Gradient(
            stops=[(0.0, (255, 0, 0, 255)), (1.0, (0, 0, 255, 255))])

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.type_combo = QComboBox()
        self.type_combo.addItems(["linear", "radial"])
        self.type_combo.setCurrentText(g.type)
        form.addRow("Type", self.type_combo)
        self.x1 = QDoubleSpinBox(); self.x1.setRange(-10, 10); self.x1.setValue(g.x1)
        self.y1 = QDoubleSpinBox(); self.y1.setRange(-10, 10); self.y1.setValue(g.y1)
        self.x2 = QDoubleSpinBox(); self.x2.setRange(-10, 10); self.x2.setValue(g.x2)
        self.y2 = QDoubleSpinBox(); self.y2.setRange(-10, 10); self.y2.setValue(g.y2)
        form.addRow("x1", self.x1); form.addRow("y1", self.y1)
        form.addRow("x2 / r", self.x2); form.addRow("y2", self.y2)
        layout.addLayout(form)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Offset", "Color"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        for off, c in g.stops:
            self._add_row(off, c)

        btns = QHBoxLayout()
        add = QPushButton("+")
        add.clicked.connect(lambda: self._add_row(0.5, (128, 128, 128, 255)))
        rem = QPushButton("−")
        rem.clicked.connect(self._remove_row)
        btns.addWidget(add); btns.addWidget(rem)
        layout.addLayout(btns)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        layout.addWidget(bb)

    def _add_row(self, off, color):
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setItem(r, 0, QTableWidgetItem(str(off)))
        btn = QPushButton()
        btn.setProperty("color", list(color))
        self._style(btn, color)
        btn.clicked.connect(lambda _, b=btn: self._pick(b))
        self.table.setCellWidget(r, 1, btn)

    def _style(self, btn, c):
        btn.setStyleSheet(
            f"background-color: rgba({c[0]},{c[1]},{c[2]},{c[3]});")

    def _pick(self, btn):
        c = btn.property("color") or [0, 0, 0, 255]
        col = QColorDialog.getColor(QColor(*c), self, "Color",
                                    QColorDialog.ShowAlphaChannel)
        if col.isValid():
            nc = [col.red(), col.green(), col.blue(), col.alpha()]
            btn.setProperty("color", nc)
            self._style(btn, nc)

    def _remove_row(self):
        r = self.table.currentRow()
        if r >= 0:
            self.table.removeRow(r)

    def result_gradient(self) -> Gradient:
        g = Gradient()
        g.type = self.type_combo.currentText()
        g.x1 = self.x1.value(); g.y1 = self.y1.value()
        g.x2 = self.x2.value(); g.y2 = self.y2.value()
        g.stops = []
        for r in range(self.table.rowCount()):
            try:
                off = float(self.table.item(r, 0).text())
            except Exception:
                continue
            btn = self.table.cellWidget(r, 1)
            c = btn.property("color") or [0, 0, 0, 255]
            g.stops.append((off, tuple(c)))
        if not g.stops:
            g.stops = [(0.0, (0, 0, 0, 255)), (1.0, (255, 255, 255, 255))]
        return g


# ==================== Main Drawer widget ====================

class DrawerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._loading = False

        self.canvas = DrawerCanvas()
        self.canvas.pointClicked.connect(self.canvas.handle_point)
        self.canvas.lineSelected.connect(self._on_line_selected)
        self.canvas.deselected.connect(self._clear_props)
        self.canvas.segmentChanged.connect(self._refresh_props)

        # line styler
        self.styler = StylerWidget()
        self.canvas.lineSelected.connect(self.styler.set_line)
        self.canvas.deselected.connect(self.styler.clear)
        self.styler.styleChanged.connect(self.canvas.update)

        # segment import/export
        library_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "library")
        self.segment_io = SegmentIOWidget(
            segment_getter=lambda: self.canvas.segment,
            library_dir=library_dir)
        self.segment_io.segmentLoaded.connect(self._on_segment_loaded)
        self.segment_io.statusMessage.connect(self._on_status)

        # --- toolbar ---
        tb = QToolBar()
        self.act_straight = QAction("Straight", self, checkable=True, checked=True)
        self.act_arc = QAction("Arc", self, checkable=True)
        grp = QActionGroup(self)
        grp.addAction(self.act_straight)
        grp.addAction(self.act_arc)
        self.act_straight.triggered.connect(
            lambda: setattr(self.canvas, "pending_type", "straight"))
        self.act_arc.triggered.connect(
            lambda: setattr(self.canvas, "pending_type", "arc"))
        tb.addAction(self.act_straight)
        tb.addAction(self.act_arc)
        tb.addSeparator()
        tb.addAction(QAction("Clear", self, triggered=self._clear_all))

        # --- layout ---
        body = QHBoxLayout()
        body.addWidget(self.canvas, 1)

        # right column in a QScrollArea — props + styler + segment I/O
        right_inner = QWidget()
        right_layout = QVBoxLayout(right_inner)
        right_layout.setContentsMargins(6, 6, 6, 6)
        right_layout.setSpacing(8)
        right_layout.addWidget(self._build_props())
        right_layout.addWidget(self.styler)
        right_layout.addWidget(self.segment_io)
        right_layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidget(right_inner)
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(300)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        body.addWidget(scroll, 0)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(tb)
        root.addLayout(body)

    def _build_props(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        self._prop_boxes = []

        box = QGroupBox("Line type")
        self._prop_boxes.append(box)
        bl = QVBoxLayout(box)
        self.rb_straight = QRadioButton("Straight", checked=True)
        self.rb_arc = QRadioButton("Arc")
        bg = QButtonGroup(self)
        bg.addButton(self.rb_straight)
        bg.addButton(self.rb_arc)
        self.rb_straight.toggled.connect(self._on_type_toggle)
        bl.addWidget(self.rb_straight)
        bl.addWidget(self.rb_arc)
        lay.addWidget(box)

        box = QGroupBox("Bend")
        self._prop_boxes.append(box)
        bl = QHBoxLayout(box)
        self.bend_slider = QSlider(Qt.Horizontal); self.bend_slider.setRange(-200, 200)
        self.bend_value = QSpinBox(); self.bend_value.setRange(-200, 200)
        self.bend_slider.valueChanged.connect(self.bend_value.setValue)
        self.bend_value.valueChanged.connect(self.bend_slider.setValue)
        self.bend_value.valueChanged.connect(self._on_bend)
        bl.addWidget(self.bend_slider)
        bl.addWidget(self.bend_value)
        lay.addWidget(box)

        box = QGroupBox("Gradient")
        self._prop_boxes.append(box)
        bl = QVBoxLayout(box)
        self.grad_check = QCheckBox("Enable")
        self.grad_check.toggled.connect(self._on_grad_toggle)
        bl.addWidget(self.grad_check)
        self.grad_edit = QPushButton("Edit stops…")
        self.grad_edit.clicked.connect(self._edit_gradient)
        bl.addWidget(self.grad_edit)
        lay.addWidget(box)

        row = QHBoxLayout()
        self.up_btn = QPushButton("Up")
        self.up_btn.clicked.connect(lambda: self._z_move(+1))
        self.down_btn = QPushButton("Down")
        self.down_btn.clicked.connect(lambda: self._z_move(-1))
        row.addWidget(self.up_btn); row.addWidget(self.down_btn)
        lay.addLayout(row)

        self.del_btn = QPushButton("Delete line")
        self.del_btn.clicked.connect(self._delete_line)
        lay.addWidget(self.del_btn)

        self.props_widget = w
        self._enable_props(False)
        return w

    def _enable_props(self, on: bool):
        for box in self._prop_boxes:
            box.setEnabled(on)
        self.up_btn.setEnabled(on)
        self.down_btn.setEnabled(on)
        self.del_btn.setEnabled(on)

    def _refresh_props(self):
        self.canvas.update()

    def _on_line_selected(self, line):
        self._enable_props(True)
        self._loading = True
        if isinstance(line, ArcLine):
            self.rb_arc.setChecked(True)
        else:
            self.rb_straight.setChecked(True)
        self.bend_slider.setValue(int(getattr(line, "bend", 0)))
        self.grad_check.setChecked(line.gradient is not None)
        self._loading = False
        self.canvas.update()

    def _clear_props(self):
        self._enable_props(False)

    def _current(self):
        return self.canvas.selected_line

    def _on_type_toggle(self):
        line = self._current()
        if not line or self._loading:
            return
        if self.rb_arc.isChecked() and not isinstance(line, ArcLine):
            new = ArcLine(line.start_point, line.end_point,
                          line.stroke_color, line.stroke_width, line.z_index,
                          line.gradient, bend=40.0,
                          dash_pattern=list(line.dash_pattern),
                          dash_offset=line.dash_offset,
                          cap_style=line.cap_style,
                          join_style=line.join_style,
                          opacity=line.opacity)
        elif self.rb_straight.isChecked() and not isinstance(line, StraightLine):
            new = StraightLine(line.start_point, line.end_point,
                               line.stroke_color, line.stroke_width, line.z_index,
                               line.gradient,
                               dash_pattern=list(line.dash_pattern),
                               dash_offset=line.dash_offset,
                               cap_style=line.cap_style,
                               join_style=line.join_style,
                               opacity=line.opacity)
        else:
            return
        i = self.canvas.segment.lines.index(line)
        self.canvas.segment.lines[i] = new
        self.canvas.selected_line = new
        self._on_line_selected(new)
        self.styler.set_line(new)

    def _on_bend(self, v):
        if self._loading:
            return
        line = self._current()
        if isinstance(line, ArcLine):
            line.bend = float(v)
            self.canvas.update()

    def _on_grad_toggle(self, on):
        line = self._current()
        if not line or self._loading:
            return
        if on and line.gradient is None:
            line.gradient = Gradient(
                stops=[(0.0, line.stroke_color), (1.0, (255, 255, 255, 255))])
        elif not on:
            line.gradient = None
        self.canvas.update()

    def _edit_gradient(self):
        line = self._current()
        if not line:
            return
        dlg = GradientEditor(line.gradient, self)
        if dlg.exec_() == QDialog.Accepted:
            line.gradient = dlg.result_gradient()
            if not self.grad_check.isChecked():
                self.grad_check.setChecked(True)
            self.canvas.update()

    def _z_move(self, direction):
        line = self._current()
        if not line:
            return
        ordered = sorted(self.canvas.segment.lines, key=lambda l: l.z_index)
        idx = ordered.index(line)
        j = idx + direction
        if 0 <= j < len(ordered):
            ordered[idx], ordered[j] = ordered[j], ordered[idx]
            for k, l in enumerate(ordered):
                l.z_index = k
        self.canvas.update()

    def _delete_line(self):
        line = self._current()
        if not line:
            return
        self.canvas.segment.remove_line(line)
        self.canvas.selected_line = None
        self._clear_props()
        self.styler.clear()
        self.canvas.update()

    def _clear_all(self):
        if not self.canvas.segment.lines:
            return
        if QMessageBox.question(self, "Clear", "Delete all lines?") \
                == QMessageBox.Yes:
            self.canvas.segment.lines.clear()
            self.canvas.selected_line = None
            self._clear_props()
            self.styler.clear()
            self.canvas.update()

    # --- segment I/O wiring ---

    def _on_segment_loaded(self, seg: Segment):
        self.canvas.set_segment(seg)
        self._clear_props()
        self.styler.clear()
        self.canvas.update()

    def _on_status(self, message: str):
        # Optional: forward to a status bar if the owner has one.
        # Left as a no-op here so the widget stays self-contained.
        pass

    # --- public API ---
    def clear_all(self):
        self._clear_all()

    def save_to(self, path: str):
        save_segment(self.canvas.segment, path)

    def load_from(self, path: str):
        seg = load_segment(path)
        self.canvas.set_segment(seg)
        self._clear_props()
        self.styler.clear()