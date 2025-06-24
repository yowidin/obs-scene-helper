from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QSpinBox, QHBoxLayout, QPushButton
from PySide6.QtWidgets import QDialogButtonBox, QMessageBox

from obs_scene_helper.controller.settings.settings import Settings


class OSHSettingsDialog(QDialog):
    def __init__(self, settings: Settings, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.settings = settings
        self.osh = settings.osh.copy(None)
        self.setWindowTitle("OSH Settings")

        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # Create input fields
        self.input_fix_delay = QSpinBox()
        self.input_fix_delay.setRange(10, 60)
        self.input_fix_delay.valueChanged.connect(self._input_fix_delay_changed)

        # Add fields to form layout
        form_layout.addRow("Input fix delay:", self.input_fix_delay)

        # Action buttons
        action_layout = QHBoxLayout()

        # Create button box
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        main_layout.addLayout(form_layout)
        main_layout.addLayout(action_layout)
        main_layout.addWidget(button_box)

        self._load_current_values()
        self._setup_tooltips()

        self.setFixedSize(self.sizeHint())

    def _load_current_values(self):
        self.input_fix_delay.setValue(self.osh.macos.fix_inputs_after_recording_resume_delay)

    def _setup_tooltips(self):
        self.input_fix_delay.setToolTip(
            "Time to wait before fiddling with macOS inputs after\n"
            "the recording has resumed (in seconds)"
        )

    def _on_osh_changed(self):
        if self.settings.osh.will_change_from(self.osh):
            self.setWindowTitle("OSH Settings *")
        else:
            self.setWindowTitle("OSH Settings")

    def _input_fix_delay_changed(self, value):
        self.osh.macos.fix_inputs_after_recording_resume_delay = value
        self._on_osh_changed()

    def accept(self):
        self.settings.osh.update(self.osh)
        super().accept()
