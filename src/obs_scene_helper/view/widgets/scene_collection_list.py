from PySide6.QtWidgets import QComboBox

from obs_scene_helper.controller.obs.connection import Connection


class SceneCollectionList(QComboBox):
    def __init__(self, connection: Connection, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._connection = connection
        self._connection.scene_collections.list_changed.connect(self._update_scene_collections)

        self.addItems(connection.scene_collections.list)
        self.setCurrentText(connection.scene_collections.active)

    def _update_scene_collections(self):
        selection = self.currentText()

        self.clear()
        self.addItems(self._connection.scene_collections.list)

        if selection is not None and selection in self._connection.scene_collections.list:
            self.setCurrentIndex(self._connection.scene_collections.list.index(selection))
