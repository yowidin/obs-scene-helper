from dataclasses import dataclass
from sys import platform
from typing import List

from PySide6.QtCore import QObject, Signal, QThread

from obs_scene_helper.controller.system.log import Log


@dataclass
class ScriptLaunchResult:
    success: bool
    logs: str


class ScriptLauncher(QObject):
    LOG_NAME = 'scrlau'

    script_done = Signal(ScriptLaunchResult)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.log = Log.child(self.LOG_NAME)
        self.log.debug('Initialized')
        self.runner = None
        self.thread = None

    @staticmethod
    def _get_launcher(command: List[str]):
        if platform == 'win32':
            from obs_scene_helper.controller.system.provider.script_launcher.windows import ScriptLauncher as WinSL
            result = WinSL(command)
        else:
            from obs_scene_helper.controller.system.provider.script_launcher.default import ScriptLauncher as DefSL
            result = DefSL(command)

        return result

    def _script_done(self, result: ScriptLaunchResult):
        self.thread.quit()
        self.runner.deleteLater()
        self.runner = None
        self.script_done.emit(result)

    def _thread_done(self):
        self.thread.deleteLater()
        self.thread = None

    def launch(self, command: List[str]):
        command_txt = " ".join(command)
        if self.runner is not None:
            self.log.warning(f'Skipping command, already running: {command_txt}')
            return

        self.log.info(f'Running command: {command_txt}')
        self.runner = self._get_launcher(command)

        self.thread = QThread()
        self.thread.started.connect(self.runner.launch)
        self.thread.finished.connect(self._thread_done)

        self.runner.moveToThread(self.thread)
        self.runner.script_done.connect(self._script_done)

        self.thread.start()
