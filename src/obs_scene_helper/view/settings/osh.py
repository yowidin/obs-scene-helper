from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QSpinBox, QHBoxLayout, QPushButton
from PySide6.QtWidgets import QDialogButtonBox, QFileDialog

from obs_scene_helper.controller.settings.settings import Settings

import os


class OSHSettingsDialog(QDialog):
    def __init__(self, settings: Settings, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.settings = settings
        self.osh = settings.osh.copy(None)
        self.setWindowTitle("OSH Settings")

        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # Set up inputs
        self.input_fix_delay = QSpinBox()
        self.input_fix_delay.setRange(10, 60)
        self.input_fix_delay.valueChanged.connect(self._input_fix_delay_changed)
        form_layout.addRow("Input fix delay:", self.input_fix_delay)

        on_change_script_layout = QHBoxLayout()
        self.output_file_change_script = QLineEdit()
        self.output_file_change_script.textChanged.connect(self._output_file_change_script_changed)
        on_change_script_layout.addWidget(self.output_file_change_script)

        select_script_button = QPushButton("...")
        select_script_button.pressed.connect(self._select_file_change_script)
        on_change_script_layout.addWidget(select_script_button)

        form_layout.addRow("Output file change script:", on_change_script_layout)

        # Dialog buttons
        button_box = QDialogButtonBox()

        button_box.addButton(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(self.accept)

        button_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        button_box.rejected.connect(self.reject)

        # Final layout
        main_layout.addLayout(form_layout)
        main_layout.addWidget(button_box)

        self._load_current_values()
        self._setup_tooltips()

        self.setFixedSize(self.sizeHint())

    def _load_current_values(self):
        self.input_fix_delay.setValue(self.osh.macos.fix_inputs_after_recording_resume_delay)
        self.output_file_change_script.setText(self.osh.output_file_change_script)

    def _setup_tooltips(self):
        self.input_fix_delay.setToolTip(
            "Time to wait before fiddling with macOS inputs after\n"
            "the recording has resumed (in seconds)."
        )

        current_script = 'None' if not self.osh.output_file_change_script else self.osh.output_file_change_script
        self.output_file_change_script.setToolTip(
            "A script to be called every time a new recording\n"
            "file is started (e.g., recording start or file split).\n"
            "\n"
            "The script will be called with a single string argument,\n"
            "containing a full path to the new recording file.\n"
            "\n"
            f"Current script: {current_script}"
        )

    def _select_file_change_script(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select script", "", "All Files (*)")
        if not file_path:
            return

        self.output_file_change_script.setText(file_path)

    def _on_osh_changed(self):
        if self.settings.osh.will_change_from(self.osh):
            self.setWindowTitle("OSH Settings *")
            self._setup_tooltips()
        else:
            self.setWindowTitle("OSH Settings")

    def _input_fix_delay_changed(self, value):
        self.osh.macos.fix_inputs_after_recording_resume_delay = value
        self._on_osh_changed()

    def _output_file_change_script_changed(self, value):
        self.osh.output_file_change_script = value
        self._on_osh_changed()

    def accept(self):
        self.settings.osh.update(self.osh)
        super().accept()
