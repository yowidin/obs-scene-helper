from enum import Enum
from typing import List

from PySide6.QtCore import QObject, QTimer, QThread, Signal

from obs_scene_helper.controller.obs.connection import Connection, ConnectionState
from obs_scene_helper.controller.obs.recording import RecordingState

from obs_scene_helper.controller.system.display_list import DisplayList
from obs_scene_helper.controller.settings.settings import Settings
from obs_scene_helper.model.settings.preset import Preset

from obs_scene_helper.controller.system.log import Log


class SwitchProfileAndSceneCollection(QObject):
    """
    Change both the profile and the scene collection once a new display configuration is detected.
    """
    LOG_NAME = 'spasc'

    preset_activated = Signal(Preset)

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
        self.obs_connection.recording.state_changed.connect(self._handle_record_state_change)
        self.obs_connection.connection_state_changed.connect(self._handle_connection_state_change)
        self.obs_connection.on_error.connect(self._handle_obs_error)
        self.obs_connection.scene_collections.active_changed.connect(self._handle_scene_collection_change)
        self.obs_connection.profiles.active_changed.connect(self._handle_profile_change)

        self.display_list = display_list
        self.display_list.changed.connect(self._handle_display_list_change)

        self.settings = settings
        self.settings.preset_list_changed.connect(self._handle_preset_list_change)

        self.recheck_timer = QTimer(self)
        self.recheck_timer.setSingleShot(True)
        self.recheck_timer.timeout.connect(self._recheck_config_timer)

        self.log = Log.child(self.LOG_NAME)
        self.log.debug('Initialized')

    def _transition_to_idle(self):
        self.state = SwitchProfileAndSceneCollection.State.Idle
        self.target_preset = None
        self.log.debug('Transition to IDLE')

    def _handle_record_state_change(self, new_state: RecordingState):
        self.log.debug(f'Record state change: {new_state}')

        if new_state == RecordingState.Stopped:
            return self._handle_recording_stopped()
        elif new_state == RecordingState.Active:
            return self._handle_recording_started()
        elif new_state == RecordingState.Unknown:
            return self._transition_to_idle()

    def _handle_connection_state_change(self, new_state: ConnectionState):
        self.log.debug(f'Connection state change: {new_state}')

        if new_state == ConnectionState.Disconnected:
            self._transition_to_idle()
        elif new_state == ConnectionState.Connected:
            self._arm_recheck_timer()

    def _handle_obs_error(self, _: str):
        self._transition_to_idle()
        self._arm_recheck_timer()

    def _handle_recording_stopped(self):
        self.log.debug(f'Recording stopped: {self.state}')

        if self.state != SwitchProfileAndSceneCollection.State.StoppingRecording:
            self.log.info(f"Skipping: wasn't waiting for a stop")
            return

        self.state = SwitchProfileAndSceneCollection.State.ChangingProfile
        self.log.debug(f"Transition to {self.state}")

        if self.obs_connection.profiles.active == self.target_preset.profile:
            self.log.info(f"Target profile already active: {self.target_preset.profile}")
            self._handle_profile_change(self.obs_connection.profiles.active)
            return

        # OBS Reports an old recording status even after generating a recording-stopped event.
        # Trying to change the profile right away will result in an error: "cannot change profile
        # while recording is active", so we have to sleep for some time here.
        QThread.sleep(5)

        self.log.info(f"Switching profile: {self.target_preset.profile}")
        if not self.obs_connection.profiles.set_active(self.target_preset.profile):
            self._transition_to_idle()

    def _handle_recording_started(self):
        self.log.debug(f'Recording started: {self.state}')

        if self.state != SwitchProfileAndSceneCollection.State.StartingRecording:
            self.log.info(f"Skipping: wasn't waiting for a start")
            return

        activated_preset = self.target_preset

        self._transition_to_idle()

        self.log.info(f'Activated preset: {activated_preset}')
        self.preset_activated.emit(activated_preset)

        # TODO: Fix some inputs not being active on Windows / Macos (e.g. different source is selected or the macOS
        #  capture requiring a restart)

    def _handle_scene_collection_change(self, _: str):
        self.log.debug(f'Scene collection changed')

        if self.state != SwitchProfileAndSceneCollection.State.ChangingSceneCollection:
            self.log.info(f"Skipping: wasn't waiting for a scene collection change")
            return

        self.state = SwitchProfileAndSceneCollection.State.StartingRecording
        self.log.debug(f"Transition to {self.state}")

        if self.obs_connection.recording.state == RecordingState.Active:
            self.log.info(f"Recording state already active")
            self._handle_recording_started()
            return

        self.log.info(f"Starting recording")
        if not self.obs_connection.recording.start():
            self._transition_to_idle()

    def _handle_profile_change(self, _: str):
        self.log.debug(f'Profile change')

        if self.state != SwitchProfileAndSceneCollection.State.ChangingProfile:
            self.log.info(f"Skipping: wasn't waiting for a profile change")
            return

        self.state = SwitchProfileAndSceneCollection.State.ChangingSceneCollection
        self.log.debug(f"Transition to {self.state}")

        if self.obs_connection.scene_collections.active == self.target_preset.scene_collection:
            self.log.info(f"Target scene collection already active: {self.target_preset.scene_collection}")
            self._handle_scene_collection_change(self.obs_connection.scene_collections.active)
            return

        self.log.info(f"Switching scene collection: {self.target_preset.scene_collection}")
        if not self.obs_connection.scene_collections.set_active(self.target_preset.scene_collection):
            self._transition_to_idle()

    def _handle_display_list_change(self, _: List[str]):
        self.log.debug(f"Handling display list change")
        self._arm_recheck_timer()

    def _handle_preset_list_change(self):
        self.log.debug(f"Handling preset list change")
        self._arm_recheck_timer()

    def _arm_recheck_timer(self):
        self.recheck_timer.start(self.settings.obs.grace_period * 1000)

    def _recheck_config_timer(self):
        self.log.debug(f"Checking configuration")

        target_preset = self.settings.preset_list.find_matching(self.display_list.displays)
        if target_preset is None:
            self.log.info(f"No matching target preset found")
            self._transition_to_idle()
            return

        self.target_preset = target_preset
        self.log.info(f"Target preset: {self.target_preset}")

        should_change_scene_collection = target_preset.scene_collection != self.obs_connection.scene_collections.active
        should_change_profile = target_preset.profile != self.obs_connection.profiles.active
        if not should_change_profile and not should_change_scene_collection:
            # Desired preset already active
            self.log.info(f"Target preset already active: {self.target_preset}")
            self.preset_activated.emit(self.target_preset)
            return

        if should_change_profile:
            # Profiles cannot be changed while the recording is still active, so we have to stop it first
            self.state = SwitchProfileAndSceneCollection.State.StoppingRecording
            self.log.debug(f"Transition to {self.state}")

            if self.obs_connection.recording.state == RecordingState.Stopped:
                self.log.info(f"Recording already stopped")
                self._handle_recording_stopped()
            else:
                self.log.info(f"Stopping recording")
                if not self.obs_connection.recording.stop():
                    self._transition_to_idle()

            return

        self.log.info(f"Target profile already active")

        # The profile is the same, but the scene collection might be different
        if should_change_scene_collection:
            # Pretend we just finished changing the profile
            self.state = SwitchProfileAndSceneCollection.State.ChangingProfile
            self.log.debug(f"Transition to {self.state}, simulating profile change")
            self._handle_profile_change(self.obs_connection.profiles.active)
            return

        # Both the profile and the scene collection are the same: pretend we just finished switching
        self.state = SwitchProfileAndSceneCollection.State.ChangingSceneCollection
        self.log.debug(f"Transition to {self.state}, simulation scene collection change")
        self._handle_scene_collection_change(self.obs_connection.scene_collections.active)
