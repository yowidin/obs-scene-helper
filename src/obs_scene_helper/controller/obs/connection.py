from enum import Enum
from typing import Optional

import logging

from PySide6.QtCore import QObject, QThread, Signal

import obsws_python as obs

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
        from obs_scene_helper.controller.obs.inputs import Inputs

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
        self.recording.on_error.connect(lambda msg: self._on_connection_error(msg))

        self.profiles = Profiles(self)
        self.profiles.on_error.connect(lambda msg: self._on_connection_error(msg))

        self.scene_collections = SceneCollections(self)
        self.scene_collections.on_error.connect(lambda msg: self._on_connection_error(msg))

        self.inputs = Inputs(self)
        self.inputs.on_error.connect(lambda msg: self._on_connection_error(msg))

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

    def _on_connection_error(self, message: str):
        """
        Connection-related error handler: logs the error message and changes the connection state to "Error".
        The connection doctor class will restart the connection after a short delay.
        All the classes, tracking the internal OBS state will re-fetch their data upon a connection establishment and
        thus hopefully fix the underlying issue (if it was an issue on our side).
        :param message: Error message to be logged.
        :return: None.
        """
        self.log.warning(f'Connection error: {message}')
        self._update_connection_state(ConnectionState.Error, message)
        self.on_error.emit(str(message))

    def _disconnect(self):
        self.log.info(f'Disconnecting')

        def stop_client(client, name: str):
            if client is not None:
                try:
                    self.log.info(f'Stopping {name} client')
                    client.base_client.ws.close()
                    client.disconnect()
                except Exception as e:
                    self.log.warning(f'Error stopping {name} client: {str(e)}')
                    self.on_error.emit(str(e))

        stop_client(self._ws, 'request')
        stop_client(self._events, 'event')

        self._ws = None
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
            callbacks.extend(self.inputs.obs_callbacks())

            # Register event callbacks
            self._events.callback.register(callbacks)

            self._update_connection_state(ConnectionState.Connected, None)
        except Exception as e:
            self._on_connection_error(str(e))
