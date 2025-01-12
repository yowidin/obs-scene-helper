from enum import Enum
from typing import Optional, List

import logging
import sys

from PySide6.QtCore import QObject, QThread, Signal

import obsws_python as obs
from obsws_python.error import OBSSDKRequestError

from obs_scene_helper.controller.obs.event_client import EventClient

from obs_scene_helper.controller.settings.settings import Settings

from obs_scene_helper.controller.system.log import Log


class ConnectionState(Enum):
    Connecting = 'Connecting'
    Connected = 'Connected'
    Error = 'Error'
    Disconnected = 'Disconnected'
    ShuttingDown = 'Shutting down'


class Connection(QObject):
    LOG_NAME = 'obsc'

    connection_state_changed = Signal(ConnectionState, str)  # Note: str is optional

    profile_list_changed = Signal()
    active_profile_changed = Signal(str)

    scene_collection_list_changed = Signal()
    active_scene_collection_changed = Signal(str)

    on_error = Signal(str)

    def __init__(self, settings: Settings, *args, **kwargs):
        from obs_scene_helper.controller.obs.recording import Recording

        super().__init__(*args, **kwargs)

        self._settings = settings
        self._settings.obs_changed.connect(self._handle_settings_change)
        self._thread = QThread()
        self.moveToThread(self._thread)

        self._thread.started.connect(self._started)

        self._ws = None  # type: Optional[obs.ReqClient]
        self._events = None  # type: Optional[EventClient]

        self.shutting_down = False

        self.profiles = []  # type: List[str]
        self.active_profile = None  # type: Optional[str]

        self.scene_collections = []  # type: List[str]
        self.active_scene_collection = None  # type: Optional[str]

        self.recording = Recording(self)
        self.recording.on_error.connect(self._on_recording_error)

        self.connection_state = ConnectionState.Disconnected  # type: ConnectionState

        self.log = Log.child(self.LOG_NAME)
        self.log.debug('Initialized')

    @property
    def ws(self) -> obs.ReqClient | None:
        return self._ws

    def _on_recording_error(self, error: str):
        self.on_error.emit(error)

    def launch(self):
        self._thread.start()

    ################################################################################
    # Profiles
    ################################################################################

    def _update_active_profile(self, name):
        if name != self.active_profile:
            self.log.info(f'Active profile change: {self.active_profile} -> {name}')
            self.active_profile = name
            self.active_profile_changed.emit(self.active_profile)
        else:
            self.log.info(f'Active profile unchanged: {name}')

    def _update_profile_list(self, new_profile_list):
        if sorted(new_profile_list) != sorted(self.profiles):
            self.log.info(f'Profile list change: {self.profiles} -> {new_profile_list}')
            self.profiles = new_profile_list
            self.profile_list_changed.emit()
        else:
            self.log.info(f'Profile list unchanged: {self.profiles}')

    # noinspection PyUnresolvedReferences
    def _fetch_profile_list(self):
        self.log.debug(f'Fetching profile list')
        res = self._ws.get_profile_list()

        self.log.debug(f'Profile list fetched')
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
            self.log.info(f'Active scene collection change: {self.active_scene_collection} -> {name}')
            self.active_scene_collection = name
            self.active_scene_collection_changed.emit(self.active_scene_collection)
        else:
            self.log.info(f'Active scene collection unchanged: {name}')

    def _update_scene_collection_list(self, new_scene_collection):
        if sorted(new_scene_collection) != sorted(self.scene_collections):
            self.log.info(f'Scene collection list change: {self.scene_collections} -> {new_scene_collection}')
            self.scene_collections = new_scene_collection
            self.scene_collection_list_changed.emit()
        else:
            self.log.info(f'Scene collection list unchanged: {self.profiles}')

    # noinspection PyUnresolvedReferences
    def _fetch_scene_collection_list(self):
        self.log.debug(f'Fetching scene collection list')
        res = self._ws.get_scene_collection_list()

        self.log.debug(f'Scene collection list fetched')
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
        self.log.debug(f'Updating connection state {new_state} ({message})')
        self.connection_state = new_state
        self.connection_state_changed.emit(self.connection_state, message)

    def _handle_settings_change(self):
        self._disconnect()
        self._update_connection_state(ConnectionState.Disconnected, "applying new settings")

    def _setup_logging(self):
        def update_logger(log):
            log.setLevel(logging.DEBUG)
            log.addHandler(Log.INSTANCE.handler)

        for log_name, log_obj in logging.Logger.manager.loggerDict.items():
            if log_name.startswith('obws'):
                update_logger(log_obj)

        if self._ws is not None:
            update_logger(self._ws.logger)

        if self._events is not None:
            # Note: we are not updating the events logger here because it already contains a change to use
            # a child logger
            # update_logger(self._events.logger)
            pass

    def _started(self):
        self.restart()

    def _on_event_client_disconnected(self):
        self._update_connection_state(ConnectionState.Disconnected, "connection lost")

    def _disconnect(self):
        self.log.info(f'Disconnecting')

        if self._ws is not None:
            self.log.info(f'Stopping request client')
            self._ws.base_client.ws.close()
            self._ws.disconnect()
            self._ws = None

        if self._events is not None:
            self.log.info(f'Stopping event client')
            self._events.base_client.ws.close()
            self._events.disconnect()
            self._events = None

    def stop(self):
        self.log.info(f'Shutting down')

        self.shutting_down = True
        self._update_connection_state(ConnectionState.ShuttingDown, "stop")

        self._disconnect()
        self._thread.quit()
        self._thread.wait()

        self._update_connection_state(ConnectionState.Disconnected, "shut down")

    def restart(self):
        self._update_connection_state(ConnectionState.Connecting, None)

        args = self._settings.obs.as_args()
        try:
            self.log.info(f'Restarting')

            self._ws = obs.ReqClient(**args)
            self._events = EventClient(on_disconnected=self._on_event_client_disconnected, **args)
            self._setup_logging()

            callbacks = [
                self.on_current_profile_changed,
                self.on_current_scene_collection_changed,

                self.on_scene_collection_list_changed,
                self.on_profile_list_changed,
            ]
            callbacks.extend(self.recording.obs_callbacks())

            # Register event callbacks
            self._events.callback.register(callbacks)

            self._update_connection_state(ConnectionState.Connected, None)

            self._fetch_profile_list()
            self._fetch_scene_collection_list()
        except Exception as e:
            self.log.warning(f'Connection error: {str(e)}')
            self._update_connection_state(ConnectionState.Error, str(e))
            self.on_error.emit(str(e))

    ################################################################################
    # API wrappers
    ################################################################################
    def restart_macos_captures(self):
        self.log.info(f'Restarting macOS captures')

        # On macOS the "screen capture" inputs get "broken" after locking the screen, but luckily OBS provides a button
        # for restarting the capture.
        # In this function we are iterating over all inputs, where this button is present and ask OBS to press it.
        if sys.platform != 'darwin':
            return

        resp = self._ws.get_input_list('screen_capture')
        for capture in resp.inputs:
            try:
                self.log.debug(f"Restarting {capture['inputName']}")
                self._ws.press_input_properties_button(capture['inputName'], "reactivate_capture")
            except OBSSDKRequestError as e:
                self.log.warning(f"Error restarting {capture['inputName']}: {str(e)}")
                self.on_error.emit(str(e))

    def set_current_profile(self, profile: str):
        self.log.debug(f"Setting current profile: {profile}")

        try:
            if profile not in self.profiles:
                self.log.error(f'Profile "{profile}" does not exist')
                self.on_error.emit(f'Profile "{profile}" does not exist')
                return

            if profile == self.active_profile:
                self.log.info(f'Skipping profile set: already active')
                return

            self.log.info(f'Waiting for record status')
            for i in range(30):
                status = self._ws.get_record_status()
                if status.output_active:
                    QThread.sleep(1000)
                    continue

            status = self._ws.get_record_status()
            if status.output_active:
                self.log.error('Profile cannot be changed while recording is active')
                self.on_error.emit('Profile cannot be changed while recording is active')
                return

            self._ws.set_current_profile(profile)
        except OBSSDKRequestError as e:
            self.log.warning(f"Profile set error: {str(e)}")
            self.on_error.emit(str(e))

    def set_current_scene_collection(self, scene_collection: str):
        self.log.debug(f"Setting current scene collection: {scene_collection}")

        try:
            if scene_collection not in self.scene_collections:
                self.log.error(f'Scene collection "{scene_collection}" does not exist')
                self.on_error.emit(f'Scene collection "{scene_collection}" does not exist')
                return

            if scene_collection == self.active_scene_collection:
                self.log.info(f'Skipping scene collection set: already active')
                return

            self._ws.set_current_scene_collection(scene_collection)
        except OBSSDKRequestError as e:
            self.log.warning(f"Scene collection set error: {str(e)}")
            self.on_error.emit(str(e))
