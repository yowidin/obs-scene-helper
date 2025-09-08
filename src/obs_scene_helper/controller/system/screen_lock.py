from enum import Enum
from sys import platform

from PySide6.QtCore import QObject, Signal

from obs_scene_helper.controller.system.log import Log


class ScreenLockState(Enum):
    Unlocked = False
    Locked = True


class ScreenLock(QObject):
    LOG_NAME = 'sl'

    screen_locked = Signal()
    screen_unlocked = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.log = Log.child(self.LOG_NAME)
        self.log.debug('Initialized')

        self.current_state = ScreenLockState.Unlocked

        if platform == 'darwin':
            from obs_scene_helper.controller.system.provider.screen_lock.macos import MacOSScreenLockProvider
            self._provider = MacOSScreenLockProvider(*args, **kwargs)
            self._provider.screen_locked.connect(self._handle_screen_locked)
            self._provider.screen_unlocked.connect(self._handle_screen_unlocked)
            self.log.debug('Configured macOS provider')
        elif platform == 'win32':
            from obs_scene_helper.controller.system.provider.screen_lock.windows import WindowsScreenLockProvider
            self._provider = WindowsScreenLockProvider(*args, **kwargs)
            self._provider.screen_locked.connect(self._handle_screen_locked)
            self._provider.screen_unlocked.connect(self._handle_screen_unlocked)
            self.log.debug('Configured windows provider')
        else:
            # TODO: Linux provider
            self._provider = None

    def _handle_screen_locked(self):
        self.log.info('Screen locked')
        self.current_state = ScreenLockState.Locked
        self.screen_locked.emit()

    def _handle_screen_unlocked(self):
        self.log.info('Screen unlocked')
        self.current_state = ScreenLockState.Unlocked
        self.screen_unlocked.emit()
