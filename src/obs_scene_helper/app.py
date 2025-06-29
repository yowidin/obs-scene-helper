import sys
import platform
from typing import Optional

from PySide6.QtWidgets import QApplication

from obs_scene_helper.controller.settings.settings import Settings
from obs_scene_helper.controller.obs.connection import Connection
from obs_scene_helper.controller.obs.connection_doctor import ConnectionDoctor

from obs_scene_helper.controller.system.display_list import DisplayList

from obs_scene_helper.controller.actions.pause_on_screen_lock import PauseOnScreenLock
from obs_scene_helper.controller.actions.switch_profile_and_scene_collection import SwitchProfileAndSceneCollection
from obs_scene_helper.controller.actions.run_script_on_output_file_change import RunScriptOnOutputFileChange

from obs_scene_helper.controller.system.log import Log as LogController

from obs_scene_helper.view.tray_icon import TrayIcon
from obs_scene_helper.view.settings.obs import OBSSettingsDialog
from obs_scene_helper.view.settings.osh import OSHSettingsDialog
from obs_scene_helper.view.widgets.preset_list import PresetList
from obs_scene_helper.view.widgets.logs import Logs as LogsWidget


class OBSSceneHelperApp:
    def __init__(self):
        LogController.setup()

        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.display_list = DisplayList()

        self.settings = Settings(self.display_list)
        self.obs_connection = Connection(self.settings)
        self.connection_doctor = ConnectionDoctor(self.obs_connection, self.settings)

        self.tray_icon = TrayIcon(self.obs_connection)
        self.tray_icon.signals.quit_requested.connect(self._close_requested)
        self.tray_icon.signals.presets_list_requested.connect(self._presets_list_requested)
        self.tray_icon.signals.obs_settings_requested.connect(self._obs_settings_requested)
        self.tray_icon.signals.osh_settings_requested.connect(self._osh_settings_requested)
        self.tray_icon.signals.logs_requested.connect(self._logs_requested)

        self._setup_platform_specifics()

        self.pause_action = PauseOnScreenLock(self.obs_connection)
        self.display_switch_action = SwitchProfileAndSceneCollection(self.obs_connection, self.display_list,
                                                                     self.settings)
        self.display_switch_action.preset_activated.connect(lambda x: self.tray_icon.preset_activated(x))

        self.run_script_action = RunScriptOnOutputFileChange(self.obs_connection, self.settings)

        if sys.platform == 'darwin':
            from obs_scene_helper.controller.actions.workarounds.macos.fix_inputs_after_recording_resume import \
                FixInputsAfterRecordingResume
            self.fix_macos_inputs = FixInputsAfterRecordingResume(self.obs_connection, self.settings)

        # Launch the connection after all the components are initialized, ensuring that all signals are received
        # by all the components
        self.obs_connection.launch()

        self.presets = None  # type: Optional[PresetList]
        self.logs = None  # type: Optional[LogsWidget]

    def _make_preset_list_window(self) -> PresetList:
        self.presets = PresetList(self.settings, self.obs_connection)
        self.presets.destroyed.connect(self._handle_presets_window_destroyed)
        return self.presets

    def _make_logs_window(self) -> LogsWidget:
        self.logs = LogsWidget()
        self.logs.destroyed.connect(self._handle_logs_window_destroyed)
        return self.logs

    def _handle_presets_window_destroyed(self):
        self.presets = None

    def _handle_logs_window_destroyed(self):
        self.logs = None

    # noinspection PyPackageRequirements,PyUnresolvedReferences
    @staticmethod
    def _setup_platform_specifics():
        system = platform.system().lower()

        if system == "darwin":
            import AppKit
            info = AppKit.NSBundle.mainBundle().infoDictionary()
            info["LSBackgroundOnly"] = "1"

        elif system == "linux":
            pass

        elif system == "windows":
            pass

    def _close_requested(self):
        self.obs_connection.stop()
        self.tray_icon.hide()
        self.app.quit()

    def _presets_list_requested(self):
        if self.presets is None:
            self.presets = self._make_preset_list_window()
            self.presets.show()
            self.presets.raise_()
            self.presets.activateWindow()
        else:
            self.presets.close()

    def _obs_settings_requested(self):
        dialog = OBSSettingsDialog(self.settings)
        dialog.exec()

    def _osh_settings_requested(self):
        dialog = OSHSettingsDialog(self.settings)
        dialog.exec()

    def _logs_requested(self):
        if self.logs is None:
            self.logs = self._make_logs_window()
            self.logs.show()
            self.logs.raise_()
            self.logs.activateWindow()
        else:
            self.logs.close()

    @staticmethod
    def run():
        app = OBSSceneHelperApp()
        sys.exit(app.app.exec())


if __name__ == "__main__":
    OBSSceneHelperApp.run()
