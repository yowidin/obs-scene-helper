from PySide6.QtCore import QObject, Signal

import obsws_python as obs

from enum import Enum

from obs_scene_helper.controller.obs.connection import Connection, ConnectionState
from obs_scene_helper.controller.obs.output_state import OutputState
from obs_scene_helper.controller.system.log import Log


class RecordingState(Enum):
    Unknown = 'unknown'
    Starting = 'starting'
    Active = 'active'
    Paused = 'paused'
    Stopping = 'stopping'
    Stopped = 'stopped'


class Recording(QObject):
    LOG_NAME = 'obs.rec'

    state_changed = Signal(RecordingState)
    on_error = Signal(str)

    def __init__(self, connection: Connection):
        super().__init__()

        self._connection = connection
        self._connection.connection_state_changed.connect(self._connection_state_changed)

        self.state = RecordingState.Unknown

        self.log = Log.child(self.LOG_NAME)
        self.log.debug('Initialized')

    @property
    def _ws(self) -> obs.ReqClient | None:
        return self._connection.ws

    def _update_recording_state(self, new_state: RecordingState):
        self.log.info(f'Updating recoding state: {new_state}')
        self.state = new_state
        self.state_changed.emit(self.state)

    def _check_recording_status(self):
        self.log.debug(f'Checking recoding state')

        try:
            if self._ws is None:
                self.log.error(f'Cannot check recoding state: no connection')
                return

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
        except Exception as e:
            self.log.warning(f"Error checking recording status: {str(e)}")
            self.on_error.emit(str(e))

    def on_record_state_changed(self, event):
        output = OutputState(event.output_state)

        if output == OutputState.Starting:
            state = RecordingState.Starting
        elif output == OutputState.Started:
            state = RecordingState.Active
        elif output == OutputState.Stopping:
            state = RecordingState.Stopping
        elif output == OutputState.Stopped:
            state = RecordingState.Stopped
        elif output == OutputState.Paused:
            state = RecordingState.Paused
        elif output == OutputState.Resumed:
            state = RecordingState.Active
        else:
            state = RecordingState.Unknown

        self.log.info(f'Record state change: {output} ({state})')
        self._update_recording_state(state)

    def obs_callbacks(self) -> list:
        return [self.on_record_state_changed]

    def _connection_state_changed(self, state: ConnectionState, _: str | None):
        if state != ConnectionState.Connected:
            self.log.debug(f'Resetting recording state')
            self._update_recording_state(RecordingState.Unknown)
            return

        self._check_recording_status()

    def pause(self) -> bool:
        self.log.debug(f"Pause")

        try:
            if self.state != RecordingState.Active:
                self.log.info(f"Skipping pause: not active ({self.state.value})")
            else:
                self._ws.pause_record()

            return True
        except Exception as e:
            self.log.warning(f"Pause error: {str(e)}")
            self.on_error.emit(str(e))
            return False

    def resume(self) -> bool:
        self.log.debug(f"Resume")

        try:
            if self.state != RecordingState.Paused:
                self.log.info(f"Skipping resume: not paused ({self.state.value})")
            else:
                self._ws.resume_record()

            return True
        except Exception as e:
            self.log.warning(f"Resume error: {str(e)}")
            self.on_error.emit(str(e))
            return False

    def start(self) -> bool:
        self.log.debug(f"Starting")

        try:
            if self.state == RecordingState.Active:
                self.log.info(f"Skipping start: output already active")
                return True
            elif self.state == RecordingState.Paused:
                self.log.info(f"Skipping start: paused, resuming instead")
                return self.resume()

            self._ws.start_record()
            return True
        except Exception as e:
            self.log.warning(f"Start error: {str(e)}")
            self.on_error.emit(str(e))
            return False

    def stop(self) -> bool:
        self.log.debug(f"Stopping recording")

        try:
            if self.state not in [RecordingState.Paused, RecordingState.Active]:
                self.log.info(f"Skipping stop: output not active")
            else:
                self._ws.stop_record()

            return True
        except Exception as e:
            self.log.warning(f"Stop error: {str(e)}")
            self.on_error.emit(str(e))
            return False
