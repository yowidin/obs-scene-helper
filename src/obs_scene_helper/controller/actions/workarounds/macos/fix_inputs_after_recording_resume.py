from PySide6.QtCore import QObject, QTimer

from obs_scene_helper.controller.obs.connection import Connection
from obs_scene_helper.controller.obs.recording import RecordingState
from obs_scene_helper.controller.obs.inputs import Input

from obs_scene_helper.controller.system.log import Log


class FixInputsAfterRecordingResume(QObject):
    """
    On macOS the "screen capture" inputs are broken after locking and unlocking the screen.
    Fiddling with input options restarts the capture and thus fixes it.

    The previous approach of using the "restart capture" didn't work because the button was not always active.
    """

    LOG_NAME = 'fiarr'

    # Delay before starting the fixes (in seconds)
    FIX_INPUTS_DELAY = 5

    def __init__(self, connection: Connection):
        super().__init__()

        self._connection = connection
        self._connection.recording.state_changed.connect(self._handle_record_state_change)
        self._connection.inputs.settings_changed.connect(self._handle_input_settings_change)
        self._connection.inputs.list_changed.connect(self._handle_input_list_change)
        self._previous_state = RecordingState.Unknown

        self._unfixed_inputs: list[Input] = []

        self._start_fixing_timer = QTimer(self)
        self._start_fixing_timer.setSingleShot(True)
        self._start_fixing_timer.timeout.connect(self._fix_captures)

        self._log = Log.child(self.LOG_NAME)
        self._log.debug('Initialized')

    @property
    def _fixing(self):
        return len(self._unfixed_inputs) != 0

    def _show_cursor_for_entry(self, entry: Input, show: bool):
        if not self._connection.inputs.set_settings(entry, {'show_cursor': show}):
            self._log.warning(f'Error changing settings for "{entry.name}", canceling fix')
            self._cancel()

    def _start_fixing_next_input(self, start: bool = False):
        if len(self._unfixed_inputs) == 0:
            if start:
                self._log.info('Nothing to fix')
            else:
                self._log.info('All inputs fixed')
            return

        # First - turn off the cursor
        first = self._unfixed_inputs[0]
        self._log.debug(f'Fixing input for "{first.name}": off')
        self._show_cursor_for_entry(first, False)

    def _fix_captures(self):
        self._log.debug('Recording resumed after a pause, fixing MacOS inputs')

        self._unfixed_inputs = []
        for entry in self._connection.inputs.list:
            if entry.kind == 'screen_capture':
                self._unfixed_inputs.append(entry)

        self._start_fixing_next_input(True)

    def _schedule_fix(self):
        self._start_fixing_timer.start(self.FIX_INPUTS_DELAY * 1000)

    def _cancel(self):
        self._log.debug('Canceling MacOS input fixes')
        self._start_fixing_timer.stop()

        if not self._fixing:
            return

        self._unfixed_inputs = []

    def _handle_record_state_change(self, new_state: RecordingState):
        last_state = self._previous_state
        self._previous_state = new_state

        if last_state == RecordingState.Paused and new_state == RecordingState.Active:
            return self._schedule_fix()
        else:
            return self._cancel()

    def _handle_input_settings_change(self, entry: Input, _):
        if not self._fixing:
            self._log.debug(f'Skipping input change event for "{entry.name}": not fixing')
            return

        first = self._unfixed_inputs[0]
        if first.settings.get('show_cursor', True):
            self._log.debug(f'Fixed input for "{first.name}"')
            del self._unfixed_inputs[0]
            self._start_fixing_next_input()
        else:
            # The cursor is turned off, turn it back on
            self._log.debug(f'Fixing input for "{first.name}": on')
            self._show_cursor_for_entry(first, True)

    def _handle_input_list_change(self):
        if not self._fixing:
            self._log.debug(f'Skipping input list change: not fixing')
            return

        self._log.warning('Input list changed while trying to fix, restarting.')
        self._cancel()
        self._schedule_fix()
