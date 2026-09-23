"""Import/export of a single Segment (the piece drawn in the Drawer).

Provides:
  * save / load JSON
  * export to a standalone SVG document
  * export to PNG / JPEG (raster)
  * clipboard copy / paste as JSON
  * a folder-based library of named segments
  * SegmentIOWidget — a self-contained panel that plugs into Drawer
"""
from __future__ import annotations
import os, json, re
from typing import Callable, List, Optional, Tuple

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QListWidget, QListWidgetItem, QPushButton,
    QFileDialog, QMessageBox, QInputDialog)
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QGuiApplication

from .core import Segment, ArcLine, save_segment, load_segment


# ==================== Pure helpers ====================

def segment_bounds(segment: Segment,
                   padding: float = 0.0) -> Tuple[float, float, float, float]:
    """Bounding box of the segment, including arc control points, padded."""
    xs, ys = [], []
    for l in segment.lines:
        for p in (l.start_point, l.end_point):
            xs.append(p.x); ys.append(p.y)
        if isinstance(l, ArcLine):
            c = l.control_point()
            xs.append(c.x); ys.append(c.y)
    if not xs:
        return (0.0, 0.0, 1.0, 1.0)
    x0 = min(xs) - padding
    y0 = min(ys) - padding
    x1 = max(xs) + padding
    y1 = max(ys) + padding
    if x1 - x0 < 1.0: x1 = x0 + 1.0
    if y1 - y0 < 1.0: y1 = y0 + 1.0
    return (x0, y0, x1, y1)


def segment_to_svg(segment: Segment, padding: float = 10.0,
                   background: Optional[Tuple[int, int, int, int]] = None) -> str:
    """A full standalone SVG document containing the segment.

    Wraps Segment.get_svg() (which returns only the <line>/<path> elements)
    in a proper <svg> root with a viewBox computed from the segment bounds.
    Gradient defs are hoisted into <defs>.
    """
    x0, y0, x1, y1 = segment_bounds(segment, padding)
    w, h = x1 - x0, y1 - y0
    defs: List[str] = []
    body = segment.get_svg(defs, "seg")
    bg = ""
    if background is not None:
        r, g, b, a = background
        bg = (f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" '
              f'fill="rgb({r},{g},{b})" fill-opacity="{a/255:.3f}"/>')
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{w:.2f}" height="{h:.2f}" '
        f'viewBox="{x0} {y0} {w} {h}">\n'
        f'<defs>{"".join(defs)}</defs>\n'
        f'{bg}\n{body}\n</svg>\n'
    )


def segment_to_png(segment: Segment, path: str,
                   width: int = 1200, height: int = 900,
                   background: Optional[Tuple[int, int, int, int]] = None):
    """Render the segment to a raster file (PNG/JPG). Format from extension."""
    # Local import to avoid any chance of a cycle if exporter starts using us later.
    from .exporter import export_object
    fmt = os.path.splitext(path)[1].lstrip(".").lower() or "png"
    if fmt == "jpeg":
        fmt = "jpg"
    export_object(segment, path, fmt, width, height,
                  background=background, quality=92)


# ==================== Clipboard ====================

def segment_to_clipboard_json(segment: Segment) -> str:
    return json.dumps(segment.to_dict(), ensure_ascii=False)


def segment_from_clipboard_json(text: str) -> Optional[Segment]:
    try:
        d = json.loads(text)
        if not isinstance(d, dict):
            return None
        return Segment.from_dict(d)
    except Exception:
        return None


# ==================== Library ====================

_SAFE_NAME = re.compile(r"[^A-Za-z0-9_\-\. ]+")


def sanitize_name(name: str) -> str:
    name = (name or "").strip()
    name = _SAFE_NAME.sub("_", name)
    return name or "segment"


class SegmentLibrary:
    """A folder full of named .json segments."""

    def __init__(self, folder: str):
        self.folder = folder
        os.makedirs(folder, exist_ok=True)

    def _path(self, name: str) -> str:
        return os.path.join(self.folder, sanitize_name(name) + ".json")

    def list_names(self) -> List[str]:
        out = []
        for fn in sorted(os.listdir(self.folder)):
            if fn.endswith(".json"):
                out.append(fn[:-5])
        return out

    def exists(self, name: str) -> bool:
        return os.path.isfile(self._path(name))

    def save(self, segment: Segment, name: str) -> str:
        path = self._path(name)
        save_segment(segment, path)
        return path

    def load(self, name: str) -> Segment:
        return load_segment(self._path(name))

    def delete(self, name: str) -> bool:
        path = self._path(name)
        if os.path.isfile(path):
            os.remove(path)
            return True
        return False


# ==================== UI ====================

class SegmentIOWidget(QWidget):
    """Panel for import/export of a single Segment.

    The widget does not own the segment: the owner supplies it via a
    ``segment_getter`` callback. On successful import, emits
    ``segmentLoaded(Segment)`` so the owner can install it on the canvas.
    """
    segmentLoaded = pyqtSignal(object)   # Segment
    statusMessage = pyqtSignal(str)

    def __init__(self, segment_getter: Callable[[], Segment],
                 library_dir: str, parent=None):
        super().__init__(parent)
        self._getter = segment_getter
        self.library = SegmentLibrary(library_dir)
        self._build_ui()
        self.refresh_library()

    # --- UI ---

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        # File
        box = QGroupBox("Segment file")
        v = QVBoxLayout(box)
        row1 = QHBoxLayout()
        self.btn_load = QPushButton("Load JSON…")
        self.btn_save = QPushButton("Save JSON…")
        self.btn_load.clicked.connect(self.load_from_file)
        self.btn_save.clicked.connect(self.save_to_file)
        row1.addWidget(self.btn_load); row1.addWidget(self.btn_save)
        v.addLayout(row1)
        row2 = QHBoxLayout()
        self.btn_svg = QPushButton("Export SVG…")
        self.btn_png = QPushButton("Export PNG…")
        self.btn_svg.clicked.connect(self.export_svg)
        self.btn_png.clicked.connect(self.export_png)
        row2.addWidget(self.btn_svg); row2.addWidget(self.btn_png)
        v.addLayout(row2)
        root.addWidget(box)

        # Clipboard
        box = QGroupBox("Clipboard")
        h = QHBoxLayout(box)
        self.btn_copy = QPushButton("Copy as JSON")
        self.btn_paste = QPushButton("Paste JSON")
        self.btn_copy.clicked.connect(self.copy_to_clipboard)
        self.btn_paste.clicked.connect(self.paste_from_clipboard)
        h.addWidget(self.btn_copy); h.addWidget(self.btn_paste)
        root.addWidget(box)

        # Library
        box = QGroupBox("Library")
        v = QVBoxLayout(box)
        self.lib_list = QListWidget()
        self.lib_list.setMinimumHeight(120)
        self.lib_list.itemDoubleClicked.connect(lambda _: self.load_from_library())
        v.addWidget(self.lib_list)

        r1 = QHBoxLayout()
        self.btn_lib_save = QPushButton("Save…")
        self.btn_lib_load = QPushButton("Load")
        self.btn_lib_save.clicked.connect(self.save_to_library)
        self.btn_lib_load.clicked.connect(self.load_from_library)
        r1.addWidget(self.btn_lib_save); r1.addWidget(self.btn_lib_load)
        v.addLayout(r1)

        r2 = QHBoxLayout()
        self.btn_lib_del = QPushButton("Delete")
        self.btn_lib_refresh = QPushButton("Refresh")
        self.btn_lib_del.clicked.connect(self.delete_from_library)
        self.btn_lib_refresh.clicked.connect(self.refresh_library)
        r2.addWidget(self.btn_lib_del); r2.addWidget(self.btn_lib_refresh)
        v.addLayout(r2)

        root.addWidget(box)
        root.addStretch(1)

    # --- helpers ---

    def _current(self) -> Segment:
        seg = self._getter()
        return seg if seg is not None else Segment()

    def _library_selection(self) -> Optional[str]:
        item = self.lib_list.currentItem()
        return item.text() if item else None

    # --- file ops ---

    def save_to_file(self):
        seg = self._current()
        if not seg.lines:
            QMessageBox.information(self, "Save", "Segment is empty.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save segment as JSON", "segment.json", "JSON (*.json)")
        if not path:
            return
        try:
            save_segment(seg, path)
            self.statusMessage.emit("Saved: " + path)
        except Exception as e:
            QMessageBox.critical(self, "Save error", str(e))

    def load_from_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load segment JSON", "", "JSON (*.json)")
        if not path:
            return
        try:
            seg = load_segment(path)
        except Exception as e:
            QMessageBox.critical(self, "Load error", str(e))
            return
        self.segmentLoaded.emit(seg)
        self.statusMessage.emit("Loaded: " + path)

    def export_svg(self):
        seg = self._current()
        if not seg.lines:
            QMessageBox.information(self, "Export SVG", "Segment is empty.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export segment as SVG", "segment.svg", "SVG (*.svg)")
        if not path:
            return
        try:
            svg = segment_to_svg(seg, padding=10.0)
            with open(path, "w", encoding="utf-8") as f:
                f.write(svg)
            self.statusMessage.emit("SVG exported: " + path)
        except Exception as e:
            QMessageBox.critical(self, "SVG export error", str(e))

    def export_png(self):
        seg = self._current()
        if not seg.lines:
            QMessageBox.information(self, "Export PNG", "Segment is empty.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export segment as PNG", "segment.png",
            "PNG (*.png);;JPEG (*.jpg *.jpeg)")
        if not path:
            return
        try:
            segment_to_png(seg, path, width=1200, height=900)
            self.statusMessage.emit("Raster exported: " + path)
        except Exception as e:
            QMessageBox.critical(self, "Raster export error", str(e))

    # --- clipboard ---

    def copy_to_clipboard(self):
        seg = self._current()
        if not seg.lines:
            return
        text = segment_to_clipboard_json(seg)
        QGuiApplication.clipboard().setText(text)
        self.statusMessage.emit("Segment copied to clipboard as JSON.")

    def paste_from_clipboard(self):
        text = QGuiApplication.clipboard().text()
        if not text:
            return
        seg = segment_from_clipboard_json(text)
        if seg is None:
            QMessageBox.warning(
                self, "Paste",
                "Clipboard doesn't contain a valid segment JSON.")
            return
        self.segmentLoaded.emit(seg)
        self.statusMessage.emit("Segment pasted from clipboard.")

    # --- library ---

    def refresh_library(self):
        self.lib_list.clear()
        for name in self.library.list_names():
            self.lib_list.addItem(QListWidgetItem(name))

    def save_to_library(self):
        seg = self._current()
        if not seg.lines:
            QMessageBox.information(self, "Library", "Segment is empty.")
            return
        default = "segment"
        item = self.lib_list.currentItem()
        if item:
            default = item.text()
        name, ok = QInputDialog.getText(
            self, "Save to library", "Name:", text=default)
        if not ok or not name.strip():
            return
        name = name.strip()
        if self.library.exists(name):
            r = QMessageBox.question(
                self, "Overwrite",
                f"A segment named '{name}' already exists.\nOverwrite?")
            if r != QMessageBox.Yes:
                return
        try:
            path = self.library.save(seg, name)
            self.refresh_library()
            safe = sanitize_name(name)
            for i in range(self.lib_list.count()):
                if self.lib_list.item(i).text() == safe:
                    self.lib_list.setCurrentRow(i)
                    break
            self.statusMessage.emit("Saved to library: " + path)
        except Exception as e:
            QMessageBox.critical(self, "Library save error", str(e))

    def load_from_library(self):
        name = self._library_selection()
        if not name:
            return
        try:
            seg = self.library.load(name)
        except Exception as e:
            QMessageBox.critical(self, "Library load error", str(e))
            return
        self.segmentLoaded.emit(seg)
        self.statusMessage.emit("Loaded from library: " + name)

    def delete_from_library(self):
        name = self._library_selection()
        if not name:
            return
        r = QMessageBox.question(
            self, "Delete", f"Delete '{name}' from the library?")
        if r != QMessageBox.Yes:
            return
        self.library.delete(name)
        self.refresh_library()
        self.statusMessage.emit("Deleted from library: " + name)