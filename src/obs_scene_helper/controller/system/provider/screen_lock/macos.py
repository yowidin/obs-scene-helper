from PySide6.QtCore import QObject, Signal


# noinspection PyPackageRequirements,PyUnresolvedReferences
class MacOSScreenLockProvider(QObject):
    screen_locked = Signal()
    screen_unlocked = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        from Foundation import NSDistributedNotificationCenter
        dnc = NSDistributedNotificationCenter.defaultCenter()
        dnc.addObserver_selector_name_object_(self, '_on_screen_locked', 'com.apple.screenIsLocked', None)
        dnc.addObserver_selector_name_object_(self, '_on_screen_unlocked', 'com.apple.screenIsUnlocked', None)

    def _on_screen_locked(self):
        self.screen_locked.emit()

    def _on_screen_unlocked(self):
        self.screen_unlocked.emit()
