from typing import List
import subprocess

from PySide6.QtCore import QObject, Signal

from obs_scene_helper.controller.system.script_launcher import ScriptLaunchResult as Result


class ScriptLauncher(QObject):
    script_done = Signal(Result)

    def __init__(self, command: List[str], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.command = command

    @staticmethod
    def _get_startup_info():
        # Avoid the terminal window popping up when getting a list of displays.
        # The terminal window popping up results in a resolution change, and if the reason for getting the display list
        # was a screen resolution change, then we get into an endless loop.
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        return si

    @staticmethod
    def extra_run_flags() -> dict:
        return {
            'creationflags': subprocess.CREATE_NO_WINDOW,
            'startupinfo': ScriptLauncher._get_startup_info(),
        }

    def launch(self):
        try:
            result = subprocess.run(
                self.command,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                **ScriptLauncher.extra_run_flags()
            )

            success = result.returncode == 0
            output = result.stdout

            self.script_done.emit(Result(success, output))
        except Exception as e:
            self.script_done.emit(Result(False, str(e)))
