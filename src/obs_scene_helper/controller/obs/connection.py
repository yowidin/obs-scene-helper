from enum import Enum
from typing import Optional, List

import logging
import sys

from PySide6.QtCore import QObject, QThread, Signal

import obsws_python as obs
from obsws_python.error import OBSSDKRequestError

from obs_scene_helper.controller.obs.event_client import EventClient
from obs_scene_helper.controller.obs.output_state import OutputState
from obs_scene_helper.controller.settings.settings import Settings


class ConnectionState(Enum):
    Connecting = 'Connecting'
    Connected = 'Connected'
    Error = 'Error'
    Disconnected = 'Disconnected'
    ShuttingDown = 'Shutting down'


class RecordingState(Enum):
    Starting = 'starting'
    Active = 'active'
    Paused = 'paused'
    Stopping = 'stopping'
    Stopped = 'stopped'


class LogHandler(logging.Handler):
    def __init__(self, on_new_record):
        logging.Handler.__init__(self)
        self.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.on_new_record = on_new_record

    def emit(self, record):
        msg = self.format(record)
        if self.on_new_record:
            self.on_new_record(msg)


class QtLogHandler(QObject):
    new_record = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.handler = LogHandler(on_new_record=lambda x: self.new_record.emit(x))
        self.handler.setLevel(logging.DEBUG)


class Connection(QObject):
    NO_LOGS = False

    connection_state_changed = Signal(ConnectionState, str)  # Note: str is optional
    recording_state_changed = Signal(RecordingState)

    profile_list_changed = Signal()
    active_profile_changed = Signal(str)

    scene_collection_list_changed = Signal()
    active_scene_collection_changed = Signal(str)

    on_error = Signal(str)

    def __init__(self, settings: Settings, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Suppress logging
        if Connection.NO_LOGS:
            Connection._disable_external_logs()

        self._settings = settings
        self._settings.obs_changed.connect(self._handle_settings_change)
        self._thread = QThread()
        self.moveToThread(self._thread)

        self.log_handler = QtLogHandler()

        self._thread.started.connect(self._started)

        self._ws = None  # type: Optional[obs.ReqClient]
        self._events = None  # type: Optional[EventClient]

        self.shutting_down = False

        self.profiles = []  # type: List[str]
        self.active_profile = None  # type: Optional[str]

        self.scene_collections = []  # type: List[str]
        self.active_scene_collection = None  # type: Optional[str]

        self.recording_state = None  # type: Optional[RecordingState]
        self.connection_state = ConnectionState.Disconnected  # type: ConnectionState

    def launch(self):
        self._thread.start()

    @staticmethod
    def _disable_external_logs():
        import logging
        import sys

        logging.getLogger('obws_python').disabled = True
        sys.stderr = None

    ################################################################################
    # Profiles
    ################################################################################

    def _update_active_profile(self, name):
        if name != self.active_profile:
            self.active_profile = name
            self.active_profile_changed.emit(self.active_profile)

    def _update_profile_list(self, new_profile_list):
        if sorted(new_profile_list) != sorted(self.profiles):
            self.profiles = new_profile_list
            self.profile_list_changed.emit()

    # noinspection PyUnresolvedReferences
    def _fetch_profile_list(self):
        res = self._ws.get_profile_list()
        self._update_profile_list(res.profiles)
        self._update_active_profile(res.current_profile_name)

    def on_current_profile_changed(self, event):
        self._update_active_profile(event.profile_name)

    def on_profile_list_changed(self, event):
        self._update_profile_list(event.profiles)

    ################################################################################
    # Scene Collections
    ################################################################################

    def _update_active_scene_collection(self, name):
        if name != self.active_scene_collection:
            self.active_scene_collection = name
            self.active_scene_collection_changed.emit(self.active_scene_collection)

    def _update_scene_collection_list(self, new_scene_collection):
        if sorted(new_scene_collection) != sorted(self.scene_collections):
            self.scene_collections = new_scene_collection
            self.scene_collection_list_changed.emit()

    # noinspection PyUnresolvedReferences
    def _fetch_scene_collection_list(self):
        res = self._ws.get_scene_collection_list()
        self._update_scene_collection_list(res.scene_collections)
        self._update_active_scene_collection(res.current_scene_collection_name)

    def on_current_scene_collection_changed(self, _):
        # Somehow, we are not getting notified about scene collection list changes
        self._fetch_scene_collection_list()
        # self._update_active_scene_collection(event.scene_collection_name)

    def on_scene_collection_list_changed(self, event):
        self._update_scene_collection_list(event.scene_collections)

    ################################################################################
    # Connection State
    ################################################################################
    def _update_connection_state(self, new_state: ConnectionState, message: Optional[str]):
        if new_state != ConnectionState.Connected:
            self.recording_state = None

        self.connection_state = new_state
        self.connection_state_changed.emit(self.connection_state, message)

    def _handle_settings_change(self):
        self._disconnect()
        self._update_connection_state(ConnectionState.Disconnected, "applying new settings")

    def _setup_logging(self):
        def update_logger(log):
            log.setLevel(logging.DEBUG)
            log.addHandler(self.log_handler.handler)

        for log_name, log_obj in logging.Logger.manager.loggerDict.items():
            if log_name.startswith('obws'):
                update_logger(log_obj)

        if self._ws is not None:
            update_logger(self._ws.logger)

        if self._events is not None:
            update_logger(self._events.logger)

    def _started(self):
        self.restart()

    def _on_event_client_disconnected(self):
        self._update_connection_state(ConnectionState.Disconnected, "connection lost")

    def _disconnect(self):
        if self._ws is not None:
            self._ws.base_client.ws.close()
            self._ws.disconnect()
            self._ws = None

        if self._events is not None:
            self._events.base_client.ws.close()
            self._events.disconnect()
            self._events = None

    def stop(self):
        self.shutting_down = True
        self._update_connection_state(ConnectionState.ShuttingDown, "stop")

        self._disconnect()
        self._thread.quit()
        self._thread.wait()

        self._update_connection_state(ConnectionState.Disconnected, "shut down")

    ################################################################################
    # Recording State
    ################################################################################

    def _update_recording_state(self, new_state: RecordingState):
        self.recording_state = new_state
        self.recording_state_changed.emit(self.recording_state)

    def _check_recording_status(self):
        status = self._ws.get_record_status()

        # Note: we cannot detect intermediate states with a request
        if not status.output_active:
            status = RecordingState.Stopped
        else:
            if status.output_paused:
                status = RecordingState.Paused
            else:
                status = RecordingState.Active

        self._update_recording_state(status)

    def on_record_state_changed(self, event):
        state = OutputState(event.output_state)
        if state == OutputState.Starting:
            status = RecordingState.Starting
        elif state == OutputState.Started:
            status = RecordingState.Active
        elif state == OutputState.Stopping:
            status = RecordingState.Stopping
        elif state == OutputState.Stopped:
            status = RecordingState.Stopped
        elif state == OutputState.Paused:
            status = RecordingState.Paused
        elif state == OutputState.Resumed:
            status = RecordingState.Active
        else:
            status = None

        if status is not None:
            self._update_recording_state(status)

    def restart(self):
        self._update_connection_state(ConnectionState.Connecting, None)

        args = self._settings.obs.as_args()
        try:
            self._ws = obs.ReqClient(**args)
            self._events = EventClient(on_disconnected=self._on_event_client_disconnected, **args)
            self._setup_logging()

            # Register event callbacks
            self._events.callback.register((
                self.on_record_state_changed,

                self.on_current_profile_changed,
                self.on_current_scene_collection_changed,

                self.on_scene_collection_list_changed,
                self.on_profile_list_changed,
            ))

            self._update_connection_state(ConnectionState.Connected, None)

            self._check_recording_status()
            self._fetch_profile_list()
            self._fetch_scene_collection_list()
        except Exception as e:
            self._update_connection_state(ConnectionState.Error, str(e))
            self.on_error.emit(str(e))

    ################################################################################
    # API wrappers
    ################################################################################
    def restart_macos_captures(self):
        # On macOS the "screen capture" inputs get "broken" after locking the screen, but luckily OBS provides a button
        # for restarting the capture.
        # In this function we are iterating over all inputs, where this button is present and ask OBS to press it.
        if sys.platform != 'darwin':
            return

        resp = self._ws.get_input_list('screen_capture')
        for capture in resp.inputs:
            try:
                self._ws.press_input_properties_button(capture['inputName'], "reactivate_capture")
            except OBSSDKRequestError as e:
                self.on_error.emit(str(e))

    def pause_recording(self):
        try:
            status = self._ws.get_record_status()
            if not status.output_active:
                return

            if status.output_paused:
                return

            self._ws.pause_record()
        except OBSSDKRequestError as e:
            self.on_error.emit(str(e))

    def resume_recording(self):
        try:
            status = self._ws.get_record_status()
            if not status.output_active:
                return

            if not status.output_paused:
                return

            self._ws.resume_record()
        except OBSSDKRequestError as e:
            self.on_error.emit(str(e))

    def start_recording(self):
        try:
            status = self._ws.get_record_status()
            if status.output_active:
                return

            self._ws.start_record()
        except OBSSDKRequestError as e:
            self.on_error.emit(str(e))

    def stop_recording(self):
        try:
            status = self._ws.get_record_status()
            if not status.output_active:
                return

            self._ws.stop_record()
        except OBSSDKRequestError as e:
            self.on_error.emit(str(e))

    def set_current_profile(self, profile: str):
        try:
            if profile not in self.profiles:
                self.on_error.emit(f'Profile "{profile}" does not exist')
                return

            if profile == self.active_profile:
                return

            for i in range(10):
                status = self._ws.get_record_status()
                if status.output_active:
                    QThread.sleep(1000)
                    continue

            status = self._ws.get_record_status()
            if status.output_active:
                self.on_error.emit('Profile cannot be changed while recording is active')
                return

            self._ws.set_current_profile(profile)
        except OBSSDKRequestError as e:
            self.on_error.emit(str(e))

    def set_current_scene_collection(self, scene_collection: str):
        try:
            if scene_collection not in self.scene_collections:
                self.on_error.emit(f'Scene collection "{scene_collection}" does not exist')
                return

            if scene_collection == self.active_scene_collection:
                return

            self._ws.set_current_scene_collection(scene_collection)
        except OBSSDKRequestError as e:
            self.on_error.emit(str(e))
