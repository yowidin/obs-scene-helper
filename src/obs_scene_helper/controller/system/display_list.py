from typing import List
from sys import platform

from PySide6.QtCore import QObject, Signal

from obs_scene_helper.controller.system.log import Log


class DisplayList(QObject):
    LOG_NAME = 'dl'

    changed = Signal(list)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.log = Log.child(self.LOG_NAME)
        self.log.debug('Initialized')

        if platform == 'win32':
            from obs_scene_helper.controller.system.provider.display_list.windows import WindowsProvider
            self._provider = WindowsProvider(*args, **kwargs)
            self.log.info('Configured windows provider')
        else:
            from obs_scene_helper.controller.system.provider.display_list.qt import QtProvider
            self._provider = QtProvider(*args, **kwargs)
            self.log.info('Configured Qt provider')

        if self._provider is not None:
            self._provider.changed.connect(self._handle_display_list_change)

            # Simulate a display list changed event.
            # This way the clients will start with a valid list of displays
            self._handle_display_list_change(self._provider.displays)

    @property
    def displays(self):
        return self._provider.displays

    def _handle_display_list_change(self, displays: List[str]):
        # Just propagate the signal
        self.log.info(f'Display list change: {displays}')
        self.changed.emit(displays)
