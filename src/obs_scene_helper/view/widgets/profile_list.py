from PySide6.QtWidgets import QComboBox

from obs_scene_helper.controller.obs.connection import Connection


class ProfileList(QComboBox):
    def __init__(self, connection: Connection, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._connection = connection
        self._connection.profile_list_changed.connect(self._update_profiles)

        self.addItems(connection.profiles)
        self.setCurrentText(self._connection.active_profile)

    def _update_profiles(self):
        selection = self.currentText()

        self.clear()
        self.addItems(self._connection.profiles)

        if selection is not None and selection in self._connection.profiles:
            self.setCurrentIndex(self._connection.profiles.index(selection))
