from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QGuiApplication, QScreen


class QtProvider(QObject):
    changed = Signal(list)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # noinspection PyTypeChecker
        self._app = QGuiApplication.instance()  # type: QGuiApplication

        self._app.screenAdded.connect(self.screen_added)
        self._app.screenRemoved.connect(self.screen_removed)

        self._displays = [x.name() for x in self._app.screens()]

    @property
    def displays(self):
        return self._displays

    def _update_display_list(self):
        new_displays = [x.name() for x in self._app.screens()]
        if sorted(new_displays) != sorted(self._displays):
            self._displays = new_displays
            self.changed.emit(self._displays)

    def screen_added(self, _: QScreen):
        self._update_display_list()

    def screen_removed(self, _: QScreen):
        self._update_display_list()
