import sys
from PySide6.QtWidgets import QApplication

from obs_scene_helper.view.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
