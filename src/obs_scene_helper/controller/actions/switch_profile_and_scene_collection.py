import time
from enum import Enum
from typing import List

from PySide6.QtCore import QObject, QTimer

from obs_scene_helper.controller.obs.connection import Connection, RecordingState, ConnectionState
from obs_scene_helper.controller.system.display_list import DisplayList
from obs_scene_helper.controller.settings.settings import Settings


class SwitchProfileAndSceneCollection(QObject):
    """
    Change both the profile and the scene collection once a new display configuration is detected.
    """

    class State(Enum):
        Idle = 0
        StoppingRecording = 1
        ChangingProfile = 2
        ChangingSceneCollection = 3
        StartingRecording = 4

    def __init__(self, obs_connection: Connection, display_list: DisplayList, settings: Settings, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.state = SwitchProfileAndSceneCollection.State.Idle
        self.target_preset = None

        self.obs_connection = obs_connection
        self.obs_connection.recording_state_changed.connect(self._handle_record_state_change)
        self.obs_connection.connection_state_changed.connect(self._handle_connection_state_change)
        self.obs_connection.on_error.connect(self._handle_obs_error)
        self.obs_connection.active_scene_collection_changed.connect(self._handle_scene_collection_change)
        self.obs_connection.active_profile_changed.connect(self._handle_profile_change)

        self.display_list = display_list
        self.display_list.changed.connect(self._handle_display_list_change)

        self.settings = settings
        self.settings.preset_list_changed.connect(self._handle_preset_list_change)

        self.recheck_timer = QTimer(self)
        self.recheck_timer.setSingleShot(True)
        self.recheck_timer.timeout.connect(self._recheck_config_timer)

    def _transition_to_idle(self):
        self.state = SwitchProfileAndSceneCollection.State.Idle
        self.target_preset = None

    def _handle_record_state_change(self, new_state: RecordingState):
        if new_state == RecordingState.Stopped:
            return self._handle_recording_stopped()
        elif new_state == RecordingState.Active:
            return self._handle_recording_started()

    def _handle_connection_state_change(self, new_state: ConnectionState):
        if new_state == ConnectionState.Disconnected:
            self._transition_to_idle()
        elif new_state == ConnectionState.Connected:
            self._arm_recheck_timer()

    def _handle_obs_error(self, _: str):
        self._transition_to_idle()
        self._arm_recheck_timer()

    def _handle_recording_stopped(self):
        if self.state != SwitchProfileAndSceneCollection.State.StoppingRecording:
            return

        self.state = SwitchProfileAndSceneCollection.State.ChangingProfile

        if self.obs_connection.active_profile == self.target_preset.profile:
            self._handle_profile_change(self.obs_connection.active_profile)
            return

        # OBS Reports an old recording status even after generating a recording-stopped event.
        # Trying to change the profile right away will result in an error: "cannot change profile
        # while recording is active", so we have to sleep for some time here.
        time.sleep(1)

        self.obs_connection.set_current_profile(self.target_preset.profile)

    def _handle_recording_started(self):
        if self.state != SwitchProfileAndSceneCollection.State.StartingRecording:
            return

        self._transition_to_idle()

        # TODO: Fix some inputs not being active on Windows / Macos (e.g. different source is selected or the macOS
        #  capture requiring a restart)

    def _handle_scene_collection_change(self, _: str):
        if self.state != SwitchProfileAndSceneCollection.State.ChangingSceneCollection:
            return

        self.state = SwitchProfileAndSceneCollection.State.StartingRecording
        self.obs_connection.start_recording()

    def _handle_profile_change(self, _: str):
        if self.state != SwitchProfileAndSceneCollection.State.ChangingProfile:
            return

        self.state = SwitchProfileAndSceneCollection.State.ChangingSceneCollection

        if self.obs_connection.active_scene_collection == self.target_preset.scene_collection:
            self._handle_scene_collection_change(self.obs_connection.active_scene_collection)
            return

        self.obs_connection.set_current_scene_collection(self.target_preset.scene_collection)

    def _handle_display_list_change(self, _: List[str]):
        self._arm_recheck_timer()

    def _handle_preset_list_change(self):
        self._arm_recheck_timer()

    def _arm_recheck_timer(self):
        self.recheck_timer.start(self.settings.obs.grace_period * 1000)

    def _recheck_config_timer(self):
        target_preset = self.settings.preset_list.find_matching(self.display_list.displays)
        if target_preset is None:
            self._transition_to_idle()
            return

        self.target_preset = target_preset

        should_change_scene_collection = target_preset.scene_collection != self.obs_connection.active_scene_collection
        should_change_profile = target_preset.profile != self.obs_connection.active_profile
        if not should_change_profile and not should_change_scene_collection:
            # Desired preset already active
            return

        if should_change_profile:
            # Profiles cannot be changed while the recording is still active, so we have to stop it first
            self.state = SwitchProfileAndSceneCollection.State.StoppingRecording

            if self.obs_connection.recording_state == RecordingState.Stopped:
                self._handle_recording_stopped()
            else:
                self.obs_connection.stop_recording()

            return

        # The profile is the same, but the scene collection might be different
        if should_change_scene_collection:
            # Pretend we just finished changing the profile
            self.state = SwitchProfileAndSceneCollection.State.ChangingProfile
            self._handle_profile_change(self.obs_connection.active_profile)
            return

        # Both the profile and the scene collection are the same: pretend we just finished switching
        self.state = SwitchProfileAndSceneCollection.State.ChangingSceneCollection
        self._handle_scene_collection_change(self.obs_connection.active_scene_collection)
