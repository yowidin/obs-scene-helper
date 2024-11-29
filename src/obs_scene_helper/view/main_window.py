from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout
from PySide6.QtWidgets import QPushButton

from obs_scene_helper.controller.obs.connection import Connection
from obs_scene_helper.controller.obs.connection_doctor import ConnectionDoctor
from obs_scene_helper.controller.settings.settings import Settings
from obs_scene_helper.controller.system.display_list import DisplayList

from obs_scene_helper.model.settings.preset import Preset

from obs_scene_helper.view.settings.obs import OBSSettingsDialog
from obs_scene_helper.view.settings.preset import AddEditPresetDialog
from obs_scene_helper.view.tray_icon import TrayIcon
from obs_scene_helper.view.widgets.named_list import NamedList


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.display_list = DisplayList()

        self.settings = Settings(self.display_list)
        self.settings.preset_list_changed.connect(self._update_presets_list)

        self.setWindowTitle("OBS Scene Helper")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        vertical = QVBoxLayout(central_widget)

        self.presets_widget = NamedList('Presets', self.settings.preset_list.presets)
        self.presets_widget.list_widget.clicked.connect(self._update_button_states)
        self.presets_widget.list_widget.doubleClicked.connect(self._edit_preset)
        self.settings_button = QPushButton('Settings')
        self.settings_button.clicked.connect(self.show_settings)

        presets_layout = QVBoxLayout()

        horizontal = QHBoxLayout()
        self.add_button = QPushButton('Add')
        self.add_button.clicked.connect(self._add_preset)

        self.edit_button = QPushButton('Edit')
        self.edit_button.clicked.connect(self._edit_preset)

        self.remove_button = QPushButton('Remove')
        self.remove_button.clicked.connect(self._remove_preset)

        horizontal.addWidget(self.add_button)
        horizontal.addWidget(self.edit_button)
        horizontal.addWidget(self.remove_button)

        presets_layout.addWidget(self.presets_widget)
        presets_layout.addLayout(horizontal)

        vertical.addLayout(presets_layout)
        vertical.addWidget(self.settings_button)

        self.obs_connection = Connection(self.settings)
        self.connection_doctor = ConnectionDoctor(self.obs_connection, self.settings)

        self.tray_icon = TrayIcon(self.obs_connection)
        self.tray_icon.signals.quit_requested.connect(self._close_requested)

        self._load_current_values()
        self._update_button_states()

        self.setFixedSize(self.sizeHint())

    def _update_button_states(self):
        has_selection = len(self.presets_widget.list_widget.selectedIndexes()) != 0

        self.edit_button.setEnabled(has_selection)
        self.remove_button.setEnabled(has_selection)

    def _load_current_values(self):
        self.presets_widget.set_items(self.settings.preset_list.presets)

    def _update_presets_list(self):
        self.presets_widget.set_items(self.settings.preset_list.presets)
        self._update_button_states()

    def _close_requested(self):
        self.close()

    def show_settings(self):
        dialog = OBSSettingsDialog(self.settings)
        dialog.exec()

    def _add_preset(self):
        dialog = AddEditPresetDialog(Preset.make(), self.settings, self.obs_connection, AddEditPresetDialog.Action.Add)
        dialog.exec()

    def _edit_preset(self):
        indexes = self.presets_widget.list_widget.selectedIndexes()
        if indexes:
            index = indexes[0].row()
            preset = self.settings.preset_list.presets[index]
            dialog = AddEditPresetDialog(preset, self.settings, self.obs_connection, AddEditPresetDialog.Action.Edit)
            dialog.exec()

    def _remove_preset(self):
        indexes = self.presets_widget.list_widget.selectedIndexes()
        if indexes:
            index = indexes[0].row()
            preset = self.settings.preset_list.presets[index]
            self.settings.preset_list.remove(preset)

    def closeEvent(self, event):
        self.obs_connection.stop()
        self.tray_icon.hide()
        super().closeEvent(event)
