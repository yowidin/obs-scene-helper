from PySide6.QtWidgets import QComboBox

from obs_scene_helper.controller.obs.connection import Connection


class SceneCollectionList(QComboBox):
    def __init__(self, connection: Connection, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._connection = connection
        self._connection.scene_collection_list_changed.connect(self._update_scene_collections)

        self.addItems(connection.scene_collections)
        self.setCurrentText(connection.active_scene_collection)

    def _update_scene_collections(self):
        selection = self.currentText()

        self.clear()
        self.addItems(self._connection.scene_collections)

        if selection is not None and selection in self._connection.scene_collections:
            self.setCurrentIndex(self._connection.scene_collections.index(selection))
