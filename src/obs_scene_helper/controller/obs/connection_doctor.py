from PySide6.QtCore import QObject, QTimer

from obs_scene_helper.controller.obs.connection import Connection, ConnectionState
from obs_scene_helper.controller.settings.settings import Settings


class ConnectionDoctor(QObject):
    def __init__(self, connection: Connection, settings: Settings, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.connection = connection
        self.connection.connection_state_changed.connect(self._connection_state_changed)

        self.settings = settings

        self.reconnect_timer = QTimer(self)
        self.reconnect_timer.timeout.connect(self._reconnect)

    def _reconnect(self):
        self.connection.restart()

    def _connection_state_changed(self, new_state: ConnectionState, _):
        if new_state in [ConnectionState.Disconnected, ConnectionState.Error]:
            if not self.connection.shutting_down:
                self.reconnect_timer.start(self.settings.obs.reconnect_delay * 1000)
        else:
            self.reconnect_timer.stop()
