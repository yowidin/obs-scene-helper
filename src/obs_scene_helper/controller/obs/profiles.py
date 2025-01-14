from PySide6.QtCore import QObject, Signal

import obsws_python as obs

from obs_scene_helper.controller.obs.connection import Connection, ConnectionState
from obs_scene_helper.controller.obs.recording import RecordingState
from obs_scene_helper.controller.system.log import Log


class Profiles(QObject):
    LOG_NAME = 'obs.prof'

    list_changed = Signal()
    active_changed = Signal(str)

    on_error = Signal(str)

    def __init__(self, connection: Connection):
        super().__init__()

        self._connection = connection
        self._connection.connection_state_changed.connect(self._connection_state_changed)

        self.list: list[str] = []
        self.active: str | None = None

        self.log = Log.child(self.LOG_NAME)
        self.log.debug('Initialized')

    @property
    def _ws(self) -> obs.ReqClient | None:
        return self._connection.ws

    def obs_callbacks(self) -> list:
        return [self.on_profile_list_changed, self.on_current_profile_changed]

    def _update_active(self, profile: str | None):
        if profile != self.active:
            self.log.info(f'Active profile changed: {self.active} -> {profile}')
            self.active = profile
            self.active_changed.emit(self.active)
        else:
            self.log.info(f'Active profile unchanged: {profile}')

    def _update_list(self, new_list: list[str]):
        if sorted(new_list) != sorted(self.list):
            self.log.info(f'Profile list changed: {self.list} -> {new_list}')
            self.list = new_list
            self.list_changed.emit()
        else:
            self.log.info(f'Profile list unchanged: {self.list}')

    # noinspection PyUnresolvedReferences
    def _fetch(self):
        try:
            self.log.debug(f'Fetching profile list')
            res = self._ws.get_profile_list()

            self.log.debug(f'Profile list fetched')
            self._update_list(res.profiles)
            self._update_active(res.current_profile_name)
        except Exception as e:
            self.log.warning(f"Error fetching profile list: {str(e)}")
            self.on_error.emit(str(e))

    def on_current_profile_changed(self, event):
        self._update_active(event.profile_name)

    def on_profile_list_changed(self, _):
        # Ignore the event payload, just fetch the new list together with the active profile
        self._fetch()

    def _connection_state_changed(self, state: ConnectionState, _: str | None):
        if state != ConnectionState.Connected:
            self.log.debug(f'Resetting profiles')
            self._update_list([])
            self._update_active(None)
            return

        self._fetch()

    def set_active(self, profile: str) -> bool:
        self.log.debug(f"Setting active profile: {profile}")

        try:
            if profile not in self.list:
                self.log.error(f'Profile "{profile}" does not exist')
                self.on_error.emit(f'Profile "{profile}" does not exist')
                return False

            if profile == self.active:
                self.log.info(f'Skipping profile set: already active')
                return True

            if self._connection.recording.state != RecordingState.Stopped:
                self.log.error('Profile cannot be changed while recording is active')
                self.on_error.emit('Profile cannot be changed while recording is active')
                return False

            self._ws.set_current_profile(profile)
            return True
        except Exception as e:
            self.log.warning(f"Profile set error: {str(e)}")
            self.on_error.emit(str(e))
            return False
