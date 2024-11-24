from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QSpinBox, QHBoxLayout, QPushButton
from PySide6.QtWidgets import QDialogButtonBox, QMessageBox

from obs_scene_helper.controller.settings.settings import Settings


class OBSSettingsDialog(QDialog):
    def __init__(self, settings: Settings, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.settings = settings
        self.obs = settings.obs.copy(None)
        self.setWindowTitle("OBS Settings")

        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # Create input fields
        self.host_input = QLineEdit()
        self.host_input.textChanged.connect(self._host_changed)

        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.valueChanged.connect(self._port_changed)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.textChanged.connect(self._password_changed)

        password_layout = QHBoxLayout()
        password_layout.addWidget(self.password_input)
        self.toggle_password_btn = QPushButton("Show")
        self.toggle_password_btn.clicked.connect(self.toggle_password_visibility)
        password_layout.addWidget(self.toggle_password_btn)

        self.timeout_input = QSpinBox()
        self.timeout_input.setRange(1, 60)
        self.timeout_input.valueChanged.connect(self._timeout_changed)

        self.reconnect_delay_input = QSpinBox()
        self.reconnect_delay_input.setRange(1, 60)
        self.reconnect_delay_input.valueChanged.connect(self._reconnect_delay_changed)

        self.grace_period_input = QSpinBox()
        self.grace_period_input.setRange(1, 60)
        self.grace_period_input.valueChanged.connect(self._grace_period_changed)

        # Add fields to form layout
        form_layout.addRow("Host:", self.host_input)
        form_layout.addRow("Port:", self.port_input)
        form_layout.addRow("Password:", password_layout)
        form_layout.addRow("Timeout:", self.timeout_input)
        form_layout.addRow("Reconnect Delay:", self.reconnect_delay_input)
        form_layout.addRow("Grace Period:", self.grace_period_input)

        # Action buttons
        action_layout = QHBoxLayout()

        self.test_conn_btn = QPushButton("Test Connection")
        self.test_conn_btn.clicked.connect(self._test_connection)

        action_layout.addWidget(self.test_conn_btn)

        # Create button box
        # noinspection PyUnresolvedReferences
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        main_layout.addLayout(form_layout)
        main_layout.addLayout(action_layout)
        main_layout.addWidget(button_box)

        self._load_current_values()
        self._setup_tooltips()

        self.setFixedSize(self.sizeHint())

        # Avoid changing the button size when toggling between "show" and "hide"
        self.toggle_password_btn.setFixedSize(self.toggle_password_btn.sizeHint())

    def _load_current_values(self):
        self.host_input.setText(self.obs.host)
        self.port_input.setValue(self.obs.port)
        self.password_input.setText(self.obs.password)
        self.timeout_input.setValue(self.obs.timeout)
        self.reconnect_delay_input.setValue(self.obs.reconnect_delay)
        self.grace_period_input.setValue(self.obs.grace_period)

    def _setup_tooltips(self):
        self.toggle_password_btn.setToolTip("Show/Hide Password")

        self.host_input.setToolTip(
            "Enter the hostname or IP address of the OBS WebSocket server\n"
            "Use 'localhost' for a local OBS instance"
        )
        self.port_input.setToolTip(
            "Enter the port number for the OBS WebSocket server\n"
            "Default: 4444"
        )
        self.password_input.setToolTip(
            "Enter the password for the OBS WebSocket server\n"
            "Leave empty if no password is set"
        )
        self.timeout_input.setToolTip(
            "Maximum time to wait for responses from OBS (seconds)\n"
            "Increase this value if you experience timeout issues"
        )
        self.reconnect_delay_input.setToolTip(
            "Time to wait (seconds) before attempting to reconnect after a connection failure"
        )
        self.grace_period_input.setToolTip(
            "Time to wait before applying a new preset (in seconds)\n"
            "Should be a higher value if you expect multiple configuration changes\n"
            "to occur one after another (e.g.: Disconnecting multiple displays)"
        )

    def toggle_password_visibility(self):
        if self.password_input.echoMode() == QLineEdit.EchoMode.Password:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_password_btn.setText("Hide")
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_password_btn.setText("Show")

    def _on_obs_changed(self):
        if self.settings.obs.will_change_from(self.obs):
            self.setWindowTitle("OBS Settings *")
        else:
            self.setWindowTitle("OBS Settings")

    def _test_connection(self):
        from obs_scene_helper.controller.obs.event_client import EventClient
        try:
            test_client = EventClient(None, **self.obs.as_args())
            test_client.disconnect()
            QMessageBox.information(self, "Connection Test",
                                    f"Successfully connected to {self.obs.host}:{self.obs.port}")
        except Exception as e:
            QMessageBox.critical(self, "Connection Test Error", f'Error: {str(e)}')

    def _host_changed(self, value):
        self.obs.host = value
        self._on_obs_changed()

    def _port_changed(self, value):
        self.obs.port = value
        self._on_obs_changed()

    def _password_changed(self, value):
        self.obs.password = value
        self._on_obs_changed()

    def _timeout_changed(self, value):
        self.obs.timeout = value
        self._on_obs_changed()

    def _reconnect_delay_changed(self, value):
        self.obs.reconnect_delay = value
        self._on_obs_changed()

    def _grace_period_changed(self, value):
        self.obs.grace_period = value
        self._on_obs_changed()

    def accept(self):
        self.settings.obs.update(self.obs)
        super().accept()