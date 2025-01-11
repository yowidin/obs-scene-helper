from PySide6.QtWidgets import QComboBox

from obs_scene_helper.controller.obs.connection import Connection


class ProfileList(QComboBox):
    def __init__(self, connection: Connection, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._connection = connection
        self._connection.profiles.list_changed.connect(self._update_profiles)

        self.addItems(connection.profiles.list)
        self.setCurrentText(self._connection.profiles.active)

    def _update_profiles(self):
        selection = self.currentText()

        self.clear()
        self.addItems(self._connection.profiles.list)

        if selection is not None and selection in self._connection.profiles.list:
            self.setCurrentIndex(self._connection.profiles.list.index(selection))
