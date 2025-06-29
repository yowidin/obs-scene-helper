from typing import List
import subprocess

from PySide6.QtCore import QObject, Signal

from obs_scene_helper.controller.system.script_launcher import ScriptLaunchResult as Result


class ScriptLauncher(QObject):
    script_done = Signal(Result)

    def __init__(self, command: List[str], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.command = command

    def launch(self):
        try:
            result = subprocess.run(
                self.command,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )

            success = result.returncode == 0
            output = result.stdout

            self.script_done.emit(Result(success, output))
        except Exception as e:
            self.script_done.emit(Result(False, str(e)))
