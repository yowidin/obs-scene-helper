from enum import Enum

from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit
from PySide6.QtWidgets import QDialogButtonBox, QMessageBox

from obs_scene_helper.controller.settings.settings import Settings
from obs_scene_helper.controller.obs.connection import Connection

from obs_scene_helper.model.settings.preset import Preset
from obs_scene_helper.view.widgets.editable_list_widget import EditableListWidget
from obs_scene_helper.view.widgets.profile_list import ProfileList
from obs_scene_helper.view.widgets.scene_collection_list import SceneCollectionList


class AddEditPresetDialog(QDialog):
    class Action(Enum):
        Add = 0
        Edit = 1

    def __init__(self, original: Preset, settings: Settings, connection: Connection,
                 action: 'AddEditPresetDialog.Action', *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.original = original
        self.settings = settings
        self.action = action

        self.updated = self.original.copy()
        if self.action == AddEditPresetDialog.Action.Add:
            self.updated.name = f'Preset {len(self.settings.preset_list.presets)}'

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("[required]")
        self.name_input.textChanged.connect(self._name_changed)

        self.profile_input = ProfileList(connection)
        self.profile_input.currentTextChanged.connect(self._profile_changed)

        self.scene_collection_input = SceneCollectionList(connection)
        self.scene_collection_input.currentTextChanged.connect(self._scene_collection_changed)

        self.display_list_input = EditableListWidget(self.updated.displays, settings.all_displays.all_displays)
        self.display_list_input.item_added.connect(self._display_list_changed)
        self.display_list_input.item_removed.connect(self._display_list_changed)
        self.display_list_input.item_changed.connect(self._display_list_changed)

        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        form_layout.addRow("Name:", self.name_input)
        form_layout.addRow("Profile:", self.profile_input)
        form_layout.addRow("Scene Collection:", self.scene_collection_input)
        form_layout.addRow("Displays:", self.display_list_input)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        main_layout.addLayout(form_layout)
        main_layout.addWidget(button_box)

        self._load_current_values()
        self._setup_tooltips()

        self.setFixedSize(self.sizeHint())

        self.settings.all_displays_changed.connect(self._on_all_display_list_changed)

        self._update_title()

    def _on_all_display_list_changed(self):
        self.display_list_input.set_all_options(self.settings.all_displays.all_displays)

    def _update_title(self):
        prefix = 'Edit' if self.action == AddEditPresetDialog.Action.Edit else 'Add'
        title = f"{prefix} Preset"
        if self.original.will_change_from(self.updated):
            title += ' *'
        self.setWindowTitle(title)

    def _name_changed(self, value):
        self.updated.name = value
        self._update_title()

    def _profile_changed(self, value):
        self.updated.profile = value
        self._update_title()

    def _scene_collection_changed(self, value):
        self.updated.scene_collection = value
        self._update_title()

    def _display_list_changed(self, *_, **__):
        self.updated.displays = self.display_list_input.items
        self._update_title()

    def _load_current_values(self):
        self.name_input.setText(self.updated.name)
        self.profile_input.setCurrentText(self.updated.profile)
        self.scene_collection_input.setCurrentText(self.updated.scene_collection)
        self.display_list_input.set_all_options(self.settings.all_displays.all_displays)

        # Put values back into the updated object, ensuring that we have some reasonable defaults
        self.updated.profile = self.profile_input.currentText()
        self.updated.scene_collection = self.scene_collection_input.currentText()

    def _setup_tooltips(self):
        self.name_input.setToolTip("Enter the name of the preset (required)")
        self.profile_input.setToolTip("Select the profile to be set when the preset is activated")
        self.scene_collection_input.setToolTip("Select the scene collection to be set when the preset is activated")
        self.display_list_input.setToolTip(
            "Configure the display set, required for the preset action (cannot be empty)\n"
            "The display set should be unique enough to distinguish between the presets"
        )

    def _validate_and_submit(self):
        text = self.name_input.text().strip()

        if not text:
            QMessageBox.warning(self, "Validation Error", "Preset name cannot be empty.")
            self.name_input.setFocus()
            return False

        if len(self.display_list_input.items) == 0:
            QMessageBox.warning(self, "Validation Error", "Display list cannot be empty.")
            return False

        return True

    def accept(self):
        if not self._validate_and_submit():
            return

        try:
            if self.action == AddEditPresetDialog.Action.Edit:
                self.settings.preset_list.update(self.original, self.updated)
            else:
                self.settings.preset_list.add(self.updated)

            super().accept()
        except RuntimeError as e:
            action = 'adding' if self.action == AddEditPresetDialog.Action.Add else 'editing'
            QMessageBox.warning(self, "Preset Error", f"Error {action} a preset: {str(e)}")
