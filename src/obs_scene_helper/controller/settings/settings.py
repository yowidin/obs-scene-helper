import json
from typing import Optional

from PySide6.QtCore import QObject, Signal, QSettings

from obs_scene_helper.model.settings.obs import OBS as OBS
from obs_scene_helper.model.settings.preset import PresetList


class Settings(QObject):
    ORG_NAME = 'yobasoft'
    APP_NAME = 'ObsSceneHelper'

    OBS_KEY = 'obs'
    PRESETS_KEY = 'presets'

    obs_changed = Signal()
    preset_list_changed = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.obs = None  # type: Optional[OBS]
        self.preset_list = None  # type: Optional[PresetList]

        self.settings = QSettings(Settings.ORG_NAME, Settings.APP_NAME)
        self._load_settings()

    def _on_obs_changed(self):
        self._save_settings()
        self.obs_changed.emit()

    def _on_presets_changed(self):
        self._save_settings()
        self.preset_list_changed.emit()

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

    def _save_settings(self, sync=True):
        self.settings.setValue(Settings.OBS_KEY, json.dumps(self.obs.to_dict()))
        self.settings.setValue(Settings.PRESETS_KEY, json.dumps(self.preset_list.to_dict()))

        if sync:
            self.settings.sync()
