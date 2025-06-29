from PySide6.QtCore import QObject, Signal

from obs_scene_helper.controller.obs.connection import Connection, ConnectionState
from obs_scene_helper.controller.obs.output_state import OutputState
from obs_scene_helper.controller.system.log import Log


class OutputFile(QObject):
    LOG_NAME = 'obs.op'

    changed = Signal(str)

    def __init__(self, connection: Connection):
        super().__init__()

        self._connection = connection
        self._connection.connection_state_changed.connect(self._connection_state_changed)

        self.file = None

        self.log = Log.child(self.LOG_NAME)
        self.log.debug('Initialized')

    def on_record_state_changed(self, event):
        output = OutputState(event.output_state)
        if output == OutputState.Started:
            self._update_output_file(event.output_path)

    def on_record_file_changed(self, event):
        self._update_output_file(event.new_output_path)

    def _update_output_file(self, path: str | None):
        self.log.info(f'Output file change: {path}')

        self.file = path
        if self.file is not None:
            self.changed.emit(path)

    def _connection_state_changed(self, state: ConnectionState, _: str | None):
        if state != ConnectionState.Connected:
            self._update_output_file(None)

    def obs_callbacks(self) -> list:
        return [self.on_record_state_changed, self.on_record_file_changed]
