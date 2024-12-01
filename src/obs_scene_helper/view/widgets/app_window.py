from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt


class AppWindow(QWidget):
    def __init__(self, title):
        super().__init__()
        self.setWindowTitle(title)
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.CustomizeWindowHint |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowTitleHint)

    def closeEvent(self, event):
        self.destroyed.emit()
        super().closeEvent(event)
