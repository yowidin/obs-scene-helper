from typing import List
from sys import platform

from PySide6.QtCore import QObject, Signal


class DisplayList(QObject):
    changed = Signal(list)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if platform == 'win32':
            # TODO: WinAPI provider
            self._provider = None
        else:
            from obs_scene_helper.controller.system.provider.display_list.qt import QtProvider
            self._provider = QtProvider(*args, **kwargs)
            self._provider.changed.connect(self._handle_display_list_change)

        if self._provider is not None:
            # Simulate a display list changed event.
            # This way the clients will start with a valid list of displays
            self._handle_display_list_change(self._provider.displays)

    @property
    def displays(self):
        return self._provider.displays

    def _handle_display_list_change(self, displays: List[str]):
        # Just propagate the signal
        self.changed.emit(displays)
