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

    on_error = Signal(str)

    def __init__(self, settings: Settings, *args, **kwargs):
        from obs_scene_helper.controller.obs.recording import Recording
        from obs_scene_helper.controller.obs.profiles import Profiles
        from obs_scene_helper.controller.obs.scene_collections import SceneCollections

        super().__init__(*args, **kwargs)

        self._settings = settings
        self._settings.obs_changed.connect(self._handle_settings_change)
        self._thread = QThread()
        self.moveToThread(self._thread)

        self._thread.started.connect(self._started)

        self._ws = None  # type: Optional[obs.ReqClient]
        self._events = None  # type: Optional[EventClient]

        self.shutting_down = False

        self.recording = Recording(self)
        self.recording.on_error.connect(lambda msg: self.on_error.emit(msg))

        self.profiles = Profiles(self)
        self.profiles.on_error.connect(lambda msg: self.on_error.emit(msg))

        self.scene_collections = SceneCollections(self)
        self.scene_collections.on_error.connect(lambda msg: self.on_error.emit(msg))

        self.connection_state = ConnectionState.Disconnected  # type: ConnectionState

        self.log = Log.child(self.LOG_NAME)
        self.log.debug('Initialized')

    @property
    def ws(self) -> obs.ReqClient | None:
        return self._ws

    def launch(self):
        self._thread.start()

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

            callbacks = []
            callbacks.extend(self.recording.obs_callbacks())
            callbacks.extend(self.profiles.obs_callbacks())
            callbacks.extend(self.scene_collections.obs_callbacks())

            # Register event callbacks
            self._events.callback.register(callbacks)

            self._update_connection_state(ConnectionState.Connected, None)
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

