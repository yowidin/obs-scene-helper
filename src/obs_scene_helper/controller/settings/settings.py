import json
from typing import Optional, List

from PySide6.QtCore import QObject, Signal, QSettings

from obs_scene_helper.controller.system.display_list import DisplayList

from obs_scene_helper.model.settings.obs import OBS as OBS
from obs_scene_helper.model.settings.preset import PresetList
from obs_scene_helper.model.settings.all_displays import AllDisplays


class Settings(QObject):
    ORG_NAME = 'yobasoft'
    APP_NAME = 'ObsSceneHelper'

    OBS_KEY = 'obs'
    PRESETS_KEY = 'presets'
    ALL_DISPLAYS_KEY = 'all_displays'

    obs_changed = Signal()
    preset_list_changed = Signal()
    all_displays_changed = Signal()

    def __init__(self, display_list: DisplayList, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.display_list = display_list
        self.display_list.changed.connect(self._on_current_display_list_changed)

        self.obs = None  # type: Optional[OBS]
        self.preset_list = None  # type: Optional[PresetList]
        self.all_displays = None  # type: Optional[AllDisplays]

        self.settings = QSettings(Settings.ORG_NAME, Settings.APP_NAME)
        self._load_settings()

        self.all_displays.update(self.display_list.displays)

    def _on_current_display_list_changed(self, displays: List[str]):
        self.all_displays.update(displays)

    def _on_obs_changed(self):
        self._save_settings()
        self.obs_changed.emit()

    def _on_presets_changed(self):
        self._save_settings()
        self.preset_list_changed.emit()

    def _on_all_displays_changed(self):
        self._save_settings()
        self.all_displays_changed.emit()

    def _load_settings(self):
        # noinspection PyTypeChecker
        obs_str = self.settings.value(Settings.OBS_KEY, None)  # type: Optional[str]
        if obs_str is None:
            self.obs = OBS.make_default(self._on_obs_changed)
        else:
            self.obs = OBS.from_dict(json.loads(obs_str), self._on_obs_changed)

        # noinspection PyTypeChecker
        preset_list_str = self.settings.value(Settings.PRESETS_KEY, None)  # type: Optional[str]
        if preset_list_str is None:
            self.preset_list = PresetList([], self._on_presets_changed)
        else:
            self.preset_list = PresetList.from_dict(json.loads(preset_list_str), self._on_presets_changed)

        # noinspection PyTypeChecker
        all_displays_str = self.settings.value(Settings.ALL_DISPLAYS_KEY, None)  # type: Optional[str]
        if all_displays_str is None:
            self.all_displays = AllDisplays([], self._on_all_displays_changed)
        else:
            self.all_displays = AllDisplays.from_dict(json.loads(all_displays_str), self._on_all_displays_changed)

    def _save_settings(self, sync=True):
        self.settings.setValue(Settings.OBS_KEY, json.dumps(self.obs.to_dict()))
        self.settings.setValue(Settings.PRESETS_KEY, json.dumps(self.preset_list.to_dict()))
        self.settings.setValue(Settings.ALL_DISPLAYS_KEY, json.dumps(self.all_displays.to_dict()))

        if sync:
            self.settings.sync()
