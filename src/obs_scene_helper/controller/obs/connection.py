from enum import Enum
from typing import Optional, List

import logging

from PySide6.QtCore import QObject, QThread, Signal

import obsws_python as obs

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

    connection_state_changed = Signal(ConnectionState, str)
    recording_state_changed = Signal(RecordingState)

    profile_list_changed = Signal()
    active_profile_changed = Signal(str)

    scene_collection_list_changed = Signal()
    active_scene_collection_changed = Signal(str)

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
        self._thread.start()

        self._ws = None  # type: Optional[obs.ReqClient]
        self._events = None  # type: Optional[EventClient]

        self.shutting_down = False

        self.profiles = []  # type: List[str]
        self.active_profile = None  # type: Optional[str]

        self.scene_collections = []  # type: List[str]
        self.active_scene_collection = None  # type: Optional[str]

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

    def _handle_settings_change(self):
        self._disconnect()
        self.connection_state_changed.emit(ConnectionState.Disconnected, "applying new settings")

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
        self.connection_state_changed.emit(ConnectionState.Disconnected, "connection lost")

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
        self.connection_state_changed.emit(ConnectionState.ShuttingDown, 'stop')

        self._disconnect()
        self._thread.quit()
        self._thread.wait()

        self.connection_state_changed.emit(ConnectionState.Disconnected, 'shut down')

    ################################################################################
    # Recording State
    ################################################################################

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

        self.recording_state_changed.emit(status)

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
            self.recording_state_changed.emit(status)

    def restart(self):
        self.connection_state_changed.emit(ConnectionState.Connecting, None)
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

            self.connection_state_changed.emit(ConnectionState.Connected, None)

            self._check_recording_status()
            self._fetch_profile_list()
            self._fetch_scene_collection_list()
        except Exception as e:
            self.connection_state_changed.emit(ConnectionState.Error, str(e))
