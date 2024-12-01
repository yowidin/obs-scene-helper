from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout
from PySide6.QtWidgets import QPushButton

from obs_scene_helper.controller.obs.connection import Connection
from obs_scene_helper.controller.settings.settings import Settings

from obs_scene_helper.model.settings.preset import Preset

from obs_scene_helper.view.settings.preset import AddEditPresetDialog
from obs_scene_helper.view.widgets.named_list import NamedList
from obs_scene_helper.view.widgets.app_window import AppWindow


class PresetList(AppWindow):
    def __init__(self, settings: Settings, obs_connection: Connection):
        super().__init__("Presets List")

        self.settings = settings
        self.settings.preset_list_changed.connect(self._update_presets_list)

        self.obs_connection = obs_connection

        self.presets_widget = NamedList('Presets', self.settings.preset_list.presets)
        self.presets_widget.list_widget.clicked.connect(self._update_button_states)
        self.presets_widget.list_widget.doubleClicked.connect(self._edit_preset)

        vertical = QVBoxLayout()

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

        vertical.addWidget(self.presets_widget)
        vertical.addLayout(horizontal)

        self.setLayout(vertical)

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
