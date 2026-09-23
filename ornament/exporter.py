import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QComboBox, QSpinBox, QCheckBox,
    QPushButton, QLabel, QFileDialog, QMessageBox, QColorDialog, QFormLayout)
from PyQt5.QtCore import Qt, QSize, QRectF, QSizeF
from PyQt5.QtGui import QImage, QPainter, QColor, QPdfWriter, QPageSize
from PyQt5.QtSvg import QSvgGenerator

from .core import Ornament, ArcLine
from .render import draw_ornament, draw_segment


def render_to_painter(painter, obj, width, height, background=None):
    painter.setRenderHint(QPainter.Antialiasing)
    if background is not None:
        painter.fillRect(0, 0, width, height, QColor(*background))

    if isinstance(obj, Ornament):
        x0, y0, x1, y1 = obj.bounds()
    else:
        xs, ys = [], []
        for l in obj.lines:
            xs += [l.start_point.x, l.end_point.x]
            ys += [l.start_point.y, l.end_point.y]
            if isinstance(l, ArcLine):
                c = l.control_point()
                xs.append(c.x); ys.append(c.y)
        if not xs:
            return
        x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)

    w = max(1.0, x1 - x0); h = max(1.0, y1 - y0)
    scale = min(width / w, height / h) * 0.95
    painter.translate((width - w * scale) / 2 - x0 * scale,
                      (height - h * scale) / 2 - y0 * scale)
    painter.scale(scale, scale)
    if isinstance(obj, Ornament):
        draw_ornament(painter, obj)
    else:
        draw_segment(painter, obj)


def export_object(obj, path, fmt, width, height,
                  background=None, quality=90):
    fmt = fmt.lower()
    if fmt == "svg":
        gen = QSvgGenerator()
        gen.setFileName(path)
        gen.setSize(QSize(width, height))
        gen.setViewBox(QRectF(0, 0, width, height))
        gen.setTitle("Ornament")
        p = QPainter(gen)
        try:
            render_to_painter(p, obj, width, height, background)
        finally:
            p.end()

    elif fmt == "pdf":
        writer = QPdfWriter(path)
        writer.setPageSize(QPageSize(QSizeF(width, height), QPageSize.Point))
        writer.setResolution(72)
        p = QPainter(writer)
        try:
            render_to_painter(p, obj, width, height, background)
        finally:
            p.end()

    else:  # png / jpg
        img = QImage(width, height, QImage.Format_ARGB32)
        img.fill(Qt.transparent if background is None else QColor(*background))
        p = QPainter(img)
        try:
            render_to_painter(p, obj, width, height, background)
        finally:
            p.end()
        if fmt == "png":
            img.save(path, "PNG")
        else:
            if background is None:
                bg = QImage(width, height, QImage.Format_RGB32)
                bg.fill(QColor(255, 255, 255))
                pp = QPainter(bg)
                pp.drawImage(0, 0, img)
                pp.end()
                bg.save(path, "JPEG", quality)
            else:
                img.save(path, "JPEG", quality)


class ExporterWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.obj = None
        self.bg_color = None
        self.output_path = None

        form = QFormLayout()
        self.fmt = QComboBox()
        self.fmt.addItems(["SVG", "PNG", "JPG", "PDF"])
        form.addRow("Format", self.fmt)

        self.w = QSpinBox(); self.w.setRange(16, 20000); self.w.setValue(1200)
        self.h = QSpinBox(); self.h.setRange(16, 20000); self.h.setValue(1200)
        form.addRow("Width (px/pt)", self.w)
        form.addRow("Height (px/pt)", self.h)

        self.transparent = QCheckBox("Transparent background")
        self.transparent.setChecked(True)
        form.addRow(self.transparent)

        self.bg_btn = QPushButton("Background color…")
        self.bg_btn.clicked.connect(self._pick_bg)
        form.addRow(self.bg_btn)

        self.quality = QSpinBox()
        self.quality.setRange(1, 100); self.quality.setValue(90)
        form.addRow("JPG quality", self.quality)

        self.path_label = QLabel("(not set)")
        form.addRow("File", self.path_label)

        self.choose_btn = QPushButton("Choose file…")
        self.choose_btn.clicked.connect(self._choose_path)
        form.addRow(self.choose_btn)

        self.export_btn = QPushButton("Export")
        self.export_btn.clicked.connect(self._export)
        form.addRow(self.export_btn)

        root = QVBoxLayout(self)
        root.addLayout(form)
        root.addStretch(1)

    def set_object(self, obj):
        self.obj = obj
        # new object — previous path no longer applies;
        # the user must explicitly choose a file or confirm overwrite
        self.output_path = None
        self.path_label.setText("(not set)")

    def _pick_bg(self):
        col = QColorDialog.getColor(QColor(255, 255, 255), self, "Background color")
        if col.isValid():
            self.bg_color = (col.red(), col.green(), col.blue(), col.alpha())
            self.transparent.setChecked(False)

    def _choose_path(self):
        fmt = self.fmt.currentText().lower()
        if fmt == "jpg":
            fmt = "jpeg"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save", f"ornament.{fmt}",
            f"{fmt.upper()} (*.{fmt})")
        if path:
            self.output_path = path
            self.path_label.setText(path)

    def _export(self):
        if self.obj is None:
            QMessageBox.warning(self, "Export", "Nothing to export.")
            return

        if not self.output_path:
            self._choose_path()
            if not self.output_path:
                return
        else:
            # path already set for the current object — ask before overwriting
            if os.path.exists(self.output_path):
                r = QMessageBox.question(
                    self, "Overwrite",
                    f"File already exists:\n{self.output_path}\n\nOverwrite?")
                if r != QMessageBox.Yes:
                    self._choose_path()
                    if not self.output_path:
                        return

        bg = None if self.transparent.isChecked() else self.bg_color
        try:
            export_object(self.obj, self.output_path,
                          self.fmt.currentText(),
                          self.w.value(), self.h.value(),
                          background=bg, quality=self.quality.value())
            QMessageBox.information(self, "Export",
                                    "Done:\n" + self.output_path)
        except Exception as e:
            QMessageBox.critical(self, "Export error", str(e))