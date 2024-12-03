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

from obs_scene_helper.view.tray_icon import TrayIcon
from obs_scene_helper.view.settings.obs import OBSSettingsDialog
from obs_scene_helper.view.widgets.preset_list import PresetList


class OBSSceneHelperApp:
    def __init__(self):
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

        self._setup_platform_specifics()

        self.pause_action = PauseOnScreenLock(self.obs_connection)
        self.display_switch_action = SwitchProfileAndSceneCollection(self.obs_connection, self.display_list,
                                                                     self.settings)

        # Launch the connection after all the components are initialized, ensuring that all signals are received
        # by all the components
        self.obs_connection.launch()

        self.presets = None  # type: Optional[PresetList]

    def _make_preset_list_window(self) -> PresetList:
        self.presets = PresetList(self.settings, self.obs_connection)
        self.presets.destroyed.connect(self._handle_presets_window_destroyed)
        return self.presets

    def _handle_presets_window_destroyed(self):
        self.presets = None

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

    @staticmethod
    def run():
        app = OBSSceneHelperApp()
        sys.exit(app.app.exec())


if __name__ == "__main__":
    OBSSceneHelperApp.run()
