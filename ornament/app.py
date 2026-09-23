from PyQt5.QtWidgets import (QMainWindow, QTabWidget, QAction,
                             QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt

from .drawer import DrawerWidget
from .ornamenter import OrnamenterWidget
from .exporter import ExporterWidget


class MainWindow(QMainWindow):
    def __init__(self, templates_dir="templates"):
        super().__init__()
        self.setWindowTitle("Ornament Designer")
        self.resize(1280, 820)

        self.drawer = DrawerWidget()
        self.ornamenter = OrnamenterWidget(templates_dir=templates_dir)
        self.exporter = ExporterWidget()

        # sync empty states so the first switch to the Ornamenter tab
        # doesn't wipe a preview that doesn't exist yet
        self.ornamenter.segment = self.drawer.canvas.segment.clone()

        self.tabs = QTabWidget()
        self.tabs.addTab(self.drawer, "Drawer")
        self.tabs.addTab(self.ornamenter, "Ornamenter")
        self.tabs.addTab(self.exporter, "Exporter")
        self.setCentralWidget(self.tabs)

        self._build_menu()

        # "→ Export" button in Ornamenter: hand the finished ornament to Exporter
        self.ornamenter.ornamentGenerated.connect(self._on_ornament_ready)
        # when switching to the Ornamenter tab, sync the segment
        # only if it has really changed
        self.tabs.currentChanged.connect(self._on_tab_change)

    def _build_menu(self):
        m = self.menuBar()

        fm = m.addMenu("File")
        fm.addAction(QAction("New segment", self, triggered=self._new))
        fm.addAction(QAction("Open segment…", self, triggered=self._open))
        fm.addAction(QAction("Save segment…", self, triggered=self._save))
        fm.addSeparator()
        fm.addAction(QAction("Quit", self, triggered=self.close))

        om = m.addMenu("Ornament")
        om.addAction(QAction("→ Ornamenter", self, triggered=self._to_orn))
        om.addAction(QAction("Generate (current template)",
                             self, triggered=self.ornamenter.generate))

        em = m.addMenu("Export")
        em.addAction(QAction("Export segment",
                             self, triggered=self._export_segment))
        em.addAction(QAction("Export ornament",
                             self, triggered=self._export_ornament))

    @staticmethod
    def _segments_differ(a, b) -> bool:
        return a.to_dict() != b.to_dict()

    def _on_tab_change(self, idx):
        if idx == 1:  # Ornamenter
            new_seg = self.drawer.canvas.segment.clone()
            if self._segments_differ(new_seg, self.ornamenter.segment):
                self.ornamenter.set_segment(new_seg)

    def _on_ornament_ready(self, orn):
        self.exporter.set_object(orn)
        self.tabs.setCurrentIndex(2)

    def _to_orn(self):
        self.ornamenter.set_segment(self.drawer.canvas.segment.clone())
        self.tabs.setCurrentIndex(1)

    def _new(self):
        self.drawer.clear_all()

    def _open(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open segment", "", "JSON (*.json)")
        if path:
            try:
                self.drawer.load_from(path)
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _save(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save segment", "segment.json", "JSON (*.json)")
        if path:
            self.drawer.save_to(path)

    def _export_segment(self):
        self.exporter.set_object(self.drawer.canvas.segment.clone())
        self.tabs.setCurrentIndex(2)

    def _export_ornament(self):
        if self.ornamenter.ornament is None:
            self.ornamenter.generate()
        self.exporter.set_object(self.ornamenter.ornament)
        self.tabs.setCurrentIndex(2)