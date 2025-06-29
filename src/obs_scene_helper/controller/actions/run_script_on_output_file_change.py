import shlex

from PySide6.QtCore import QObject

from obs_scene_helper.controller.obs.connection import Connection
from obs_scene_helper.controller.settings.settings import Settings
from obs_scene_helper.controller.system.log import Log
from obs_scene_helper.controller.system.script_launcher import ScriptLauncher, ScriptLaunchResult


class RunScriptOnOutputFileChange(QObject):
    """
    Run a user-specified script every time a new recording file is started.
    """

    LOG_NAME = 'rsoofc'

    def __init__(self, obs_connection: Connection, settings: Settings, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.settings = settings

        self.obs_connection = obs_connection
        self.obs_connection.output_file.changed.connect(self._handle_output_file_change)

        self.launcher = ScriptLauncher()
        self.launcher.script_done.connect(self._script_done)

        self.log = Log.child(self.LOG_NAME)
        self.log.debug('Initialized')

    def _script_done(self, result: ScriptLaunchResult):
        if not result.success:
            self.log.error(f'Script failed: {result.logs}')
        else:
            self.log.debug(f'Script done: {result.logs}')

    def _handle_output_file_change(self, new_path: str):
        self.log.debug(f'New recording file: {new_path}')

        unescaped_script = self.settings.osh.output_file_change_script
        if len(unescaped_script) == 0:
            self.log.debug(f'No script assigned, skipping')
            return

        full_cmd = shlex.split(unescaped_script) + [new_path]
        self.launcher.launch(full_cmd)
