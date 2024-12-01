from enum import Enum
from sys import platform

from PySide6.QtCore import QObject, Signal


class ScreenLockState(Enum):
    Unlocked = False
    Locked = True


class ScreenLock(QObject):
    screen_locked = Signal()
    screen_unlocked = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.current_state = ScreenLockState.Unlocked

        if platform == 'darwin':
            from obs_scene_helper.controller.system.provider.screen_lock.macos import MacOSScreenLockProvider
            self._provider = MacOSScreenLockProvider(*args, **kwargs)
            self._provider.screen_locked.connect(self._handle_screen_locked)
            self._provider.screen_unlocked.connect(self._handle_screen_unlocked)
        else:
            # TODO: Windows and Linux providers
            self._provider = None

    def _handle_screen_locked(self):
        self.current_state = ScreenLockState.Locked
        self.screen_locked.emit()

    def _handle_screen_unlocked(self):
        self.current_state = ScreenLockState.Unlocked
        self.screen_unlocked.emit()
