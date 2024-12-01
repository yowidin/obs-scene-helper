import sys
import platform
from typing import Optional

from PySide6.QtWidgets import QApplication

from obs_scene_helper.controller.settings.settings import Settings
from obs_scene_helper.controller.obs.connection import Connection
from obs_scene_helper.controller.obs.connection_doctor import ConnectionDoctor
from obs_scene_helper.controller.system.display_list import DisplayList

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

        self.presets = None  # type: Optional[PresetList]

    def _make_preset_list_window(self) -> PresetList:
        self.presets = PresetList(self.settings, self.obs_connection)
        self.presets.destroyed.connect(self._handle_presets_window_destroyed)
        return self.presets

    def _handle_presets_window_destroyed(self):
        self.presets = None

    def _setup_platform_specifics(self):
        system = platform.system().lower()

        if system == "darwin":
            self.app.setProperty("HIDING_DOCK_ICON", 1)

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
        elif self.presets.isVisible():
            self.presets.hide()
        else:
            self.presets.show()
            self.presets.raise_()
            self.presets.activateWindow()

    def _obs_settings_requested(self):
        dialog = OBSSettingsDialog(self.settings)
        dialog.exec()

    @staticmethod
    def run():
        app = OBSSceneHelperApp()
        sys.exit(app.app.exec())


if __name__ == "__main__":
    OBSSceneHelperApp.run()
