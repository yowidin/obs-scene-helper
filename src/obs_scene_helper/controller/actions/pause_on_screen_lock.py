from enum import Enum

from PySide6.QtCore import QObject

from obs_scene_helper.controller.obs.connection import Connection
from obs_scene_helper.controller.obs.recording import RecordingState
from obs_scene_helper.controller.system.screen_lock import ScreenLock

from obs_scene_helper.controller.system.log import Log


class PauseOnScreenLock(QObject):
    """
    - Pause the recording on a screen-locked event
    - Resume the recording on a screen-unlocked event
    """

    LOG_NAME = 'posl'

    class State(Enum):
        Idle = 0
        WaitingForPauseEvent = 1
        WaitingForResumeEvent = 2

    def __init__(self, obs_connection: Connection, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.state = PauseOnScreenLock.State.Idle

        self.obs_connection = obs_connection
        self.obs_connection.recording.state_changed.connect(self._handle_record_state_change)

        self.screen_lock = ScreenLock()
        self.screen_lock.screen_locked.connect(self._handle_screen_locked)
        self.screen_lock.screen_unlocked.connect(self._handle_screen_unlocked)

        self.log = Log.child(self.LOG_NAME)
        self.log.debug('Initialized')

    def _handle_record_state_change(self, new_state: RecordingState):
        self.log.debug(f'Handling record state change: {self.state} -> {new_state}')

        if self.state == PauseOnScreenLock.State.WaitingForPauseEvent and new_state == RecordingState.Paused:
            return self._pause_done()

        if self.state == PauseOnScreenLock.State.WaitingForResumeEvent and new_state == RecordingState.Active:
            return self._resume_done()

        if self.state != PauseOnScreenLock.State.Idle and new_state in [RecordingState.Stopped,
                                                                        RecordingState.Starting,
                                                                        RecordingState.Stopping,
                                                                        RecordingState.Unknown]:
            self.log.debug(f'Inconsistent state: {self.state}')
            self.state = PauseOnScreenLock.State.Idle

    def _pause_done(self):
        # Nothing to do here
        self.state = PauseOnScreenLock.State.Idle
        self.log.info('Pause done')

    def _resume_done(self):
        self.state = PauseOnScreenLock.State.Idle
        self.log.info('Resume done')

    def _handle_screen_locked(self):
        self.log.debug('Handling screen lock event')

        if self.obs_connection.recording.state == RecordingState.Paused:
            self.log.info('Screen lock: already paused')
            return

        self.log.info('Requesting pause')
        self.state = PauseOnScreenLock.State.WaitingForPauseEvent
        if not self.obs_connection.recording.pause():
            self.state = PauseOnScreenLock.State.Idle

    def _handle_screen_unlocked(self):
        self.log.debug('Handling screen unlock event')

        if self.obs_connection.recording.state == RecordingState.Active:
            self.log.info('Screen lock: already resumed')
            return

        self.log.info('Requesting resumption')
        self.state = PauseOnScreenLock.State.WaitingForResumeEvent
        if not self.obs_connection.recording.resume():
            self.state = PauseOnScreenLock.State.Idle
