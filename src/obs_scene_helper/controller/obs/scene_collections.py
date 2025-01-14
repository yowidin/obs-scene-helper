from PySide6.QtCore import QObject, Signal

import obsws_python as obs

from obs_scene_helper.controller.obs.connection import Connection, ConnectionState
from obs_scene_helper.controller.system.log import Log


class SceneCollections(QObject):
    LOG_NAME = 'obs.scs'

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
        return [self.on_current_scene_collection_changed, self.on_scene_collection_list_changed]

    def _update_active(self, name: str | None):
        if name != self.active:
            self.log.info(f'Active scene collection changed: {self.active} -> {name}')
            self.active = name
            self.active_changed.emit(self.active)
        else:
            self.log.info(f'Active scene collection unchanged: {name}')

    def _update_list(self, new_list: list[str]):
        if sorted(new_list) != sorted(self.list):
            self.log.info(f'Scene collections list changed: {self.list} -> {new_list}')
            self.list = new_list
            self.list_changed.emit()
        else:
            self.log.info(f'Scene collections list unchanged: {self.list}')

    # noinspection PyUnresolvedReferences
    def _fetch(self):
        try:
            self.log.debug(f'Fetching scene collection list')
            res = self._ws.get_scene_collection_list()

            self.log.debug(f'Scene collection list fetched')
            self._update_list(res.scene_collections)
            self._update_active(res.current_scene_collection_name)
        except Exception as e:
            self.log.warning(f"Error fetching scene collection list: {str(e)}")
            self.on_error.emit(str(e))

    def on_current_scene_collection_changed(self, _):
        # Somehow, we are not getting notified about scene collection list changes
        self._fetch()
        # self._update_active(event.scene_collection_name)

    def on_scene_collection_list_changed(self, event):
        self._update_list(event.scene_collections)

    def _connection_state_changed(self, state: ConnectionState, _: str | None):
        if state != ConnectionState.Connected:
            self.log.debug(f'Resetting scene collections')
            self._update_list([])
            self._update_active(None)
            return

        self._fetch()

    def set_active(self, scene_collection: str) -> bool:
        self.log.debug(f"Setting current scene collection: {scene_collection}")

        try:
            if scene_collection not in self.list:
                self.log.error(f'Scene collection "{scene_collection}" does not exist')
                self.on_error.emit(f'Scene collection "{scene_collection}" does not exist')
                return False

            if scene_collection == self.active:
                self.log.info(f'Skipping scene collection set: already active')
            else:
                self._ws.set_current_scene_collection(scene_collection)

            return True
        except Exception as e:
            self.log.warning(f"Scene collection set error: {str(e)}")
            self.on_error.emit(str(e))
            return False
