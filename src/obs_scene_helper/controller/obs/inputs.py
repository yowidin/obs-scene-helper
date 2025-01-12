from PySide6.QtCore import QObject, Signal

from obsws_python.error import OBSSDKRequestError
import obsws_python as obs

from obs_scene_helper.controller.obs.connection import Connection, ConnectionState
from obs_scene_helper.controller.system.log import Log

from dataclasses import dataclass


@dataclass
class Input:
    uuid: str
    name: str
    kind: str
    settings: dict

    def __lt__(self, other: 'Input'):
        return self.uuid < other.uuid


class Inputs(QObject):
    LOG_NAME = 'obs.inp'

    # Input list changed signal
    # warning: sometimes OBS doesn't report input list change events or even answers with an outdated list of
    # inputs on request (make sure to handle non-existent input errors correctly).
    list_changed = Signal()

    # Settings changed for input (input, old_settings).
    # The input itself will contain the new settings.
    settings_changed = Signal(Input, dict)

    # Input name changed (input, old_name).
    # The input itself will contain the new name.
    name_changed = Signal(Input, str)

    on_error = Signal(str)

    def __init__(self, connection: Connection):
        super().__init__()

        self._connection = connection
        self._connection.connection_state_changed.connect(self._connection_state_changed)

        self.list: list[Input] = []

        self.log = Log.child(self.LOG_NAME)
        self.log.debug('Initialized')

    @property
    def _ws(self) -> obs.ReqClient | None:
        return self._connection.ws

    def _by_uuid(self, uuid: str) -> Input | None:
        return next((entry for entry in self.list if entry.uuid == uuid), None)

    def _by_name(self, name: str) -> Input | None:
        return next((entry for entry in self.list if entry.name == name), None)

    def obs_callbacks(self) -> list:
        return [self.on_input_settings_changed, self.on_input_created, self.on_input_removed,
                self.on_input_name_changed]

    def _update_list(self, new_list: list[Input]):
        if sorted(new_list) != sorted(self.list):
            self.log.info(f'Inputs list changed: {self.list} -> {new_list}')
            self.list = new_list
            self.list_changed.emit()
        else:
            self.log.info(f'Inputs list unchanged: {self.list}')

    def _fetch(self):
        self.log.debug(f'Fetching inputs list')
        res = self._ws.get_input_list()

        self.log.debug(f'Inputs list fetched')
        inputs = res.inputs

        all_inputs = []
        for entry in inputs:
            uuid = entry['inputUuid']
            kind = entry['unversionedInputKind']
            name = entry['inputName']

            settings_res = self._ws.get_input_settings(name)
            settings = settings_res.input_settings

            all_inputs.append(Input(uuid, name, kind, settings))

        self._update_list(all_inputs)

    def _connection_state_changed(self, state: ConnectionState, _: str | None):
        if state != ConnectionState.Connected:
            self.log.debug(f'Resetting inputs list')
            self._update_list([])
            return

        self._fetch()

    def on_input_settings_changed(self, event):
        name = event.input_name
        uuid = event.input_uuid
        new_settings = event.input_settings

        existing = self._by_uuid(uuid)
        if existing is None:
            self.log.warning(f'Settings update for non-existent input: "{name}" / {uuid}. Re-fetching inputs.')
            self._fetch()
            return

        old_settings = existing.settings
        existing.settings = old_settings | new_settings

        self.settings_changed.emit(existing, old_settings)

    def on_input_created(self, event):
        uuid = event.input_uuid
        kind = event.unversioned_input_kind
        name = event.input_name

        default_settings = event.default_input_settings
        settings = event.input_settings
        all_settings = default_settings | settings

        self.list.append(Input(uuid, name, kind, all_settings))

        self.log.info(f'New input created: {self.list[-1]}')
        self.list_changed.emit()

    def on_input_removed(self, event):
        uuid = event.input_uuid
        name = event.input_name

        for i in range(len(self.list)):
            if self.list[i].uuid != uuid:
                continue

            self.log.info(f'Input removed: "{name}" / {uuid}')
            del self.list[i]
            self.list_changed.emit()
            return

        self.log.warning(f'Non-existent input removed: "{name}" / {uuid}. Re-fetching inputs.')
        self._fetch()

    def on_input_name_changed(self, event):
        uuid = event.input_uuid
        name = event.input_name
        old_name = event.old_input_name

        existing = self._by_uuid(uuid)
        if existing is None:
            self.log.warning(
                f'Name update for non-existent input: "{old_name}" -> "{name}" / {uuid}. Re-fetching inputs.')
            self._fetch()
            return

        existing.name = name

        self.name_changed.emit(existing, old_name)

    def press_properties_button(self, entry: Input, button_name: str) -> bool:
        try:
            self.log.debug(f'Pressing "{button_name}" for {entry.name}')
            self._ws.press_input_properties_button(entry.name, button_name)
            return True
        except OBSSDKRequestError as e:
            self.log.warning(f'Error pressing "{button_name}" for {entry.name}: {str(e)}')
            self.on_error.emit(str(e))
            return False

    def set_settings(self, entry: Input, settings: dict, overlay: bool = True) -> bool:
        """
        Update the input settings.
        :param entry: Input to update the settings for.
        :param settings: New settings.
        :param overlay: Whether the settings should be applied on top of existing ones (True) or reset to the default
                        settings, and then applied on top of them.
        :return: True in case of success, False otherwise.
        """
        try:
            self.log.debug(f'Updating settings for "{entry.name}": {settings}')
            self._ws.set_input_settings(entry.name, settings, overlay)
            return True
        except OBSSDKRequestError as e:
            self.log.warning(f'Error updating settings for "{entry.name}": {str(e)}')
            self.on_error.emit(str(e))
            return False
