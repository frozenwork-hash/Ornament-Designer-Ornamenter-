import sys, os
from PyQt5.QtWidgets import QApplication
from ornament.app import MainWindow
import sys
import os

def resource_path(relative_path):
    """Возвращает абсолютный путь к ресурсу, работает и для dev, и для PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller создаёт временную папку и хранит путь в _MEIPASS
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    here = os.path.dirname(os.path.abspath(__file__))
    templates_dir = resource_path("templates")
    w = MainWindow(templates_dir=templates_dir)
    w.show()
    sys.exit(app.exec_())