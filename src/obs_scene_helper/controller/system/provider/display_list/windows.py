from typing import Callable

import sys
import os
import subprocess
import json

from PySide6.QtCore import QObject, Signal

import win32con
from win32gui import CreateWindowEx, WNDCLASS, RegisterClass, DefWindowProc, DestroyWindow
from win32api import GetModuleHandle

from obs_scene_helper.controller.system.log import Log


# On Windows 10 the Qt does not correctly react to display configuration changes, for example: switching from
# the "PC screen only" to the "Second screen only" doesn't generate any events. So we have to react to the low-level
# Windows API messages and get the display list manually by calling a dedicated function in another interpreter instance


class ScreenChangeObserver:
    """ Hidden window-based observer to capture WM_DISPLAYCHANGE messages. """

    def __init__(self, callback: Callable[[int, int, int], None]):
        self.callback = callback
        self.hwnd = self._create_hidden_window()

    def destroy(self):
        if self.hwnd is not None:
            DestroyWindow(self.hwnd)
            self.hwnd = None

    def _create_hidden_window(self):
        class_name = "OSHHiddenDisplayChangeObserver"
        hinstance = GetModuleHandle(None)

        wndclass = WNDCLASS()
        wndclass.lpfnWndProc = self._window_proc
        wndclass.lpszClassName = class_name
        wndclass.hInstance = hinstance
        RegisterClass(wndclass)

        hwnd = CreateWindowEx(0, class_name, None, win32con.WS_OVERLAPPED, win32con.CW_USEDEFAULT,
                              win32con.CW_USEDEFAULT, win32con.CW_USEDEFAULT, win32con.CW_USEDEFAULT, None, None,
                              hinstance, None)

        return hwnd

    def _window_proc(self, hwnd, msg, wparam, lparam):
        """
        Window procedure to handle messages.
        """
        if msg == win32con.WM_DISPLAYCHANGE:
            # Extract resolution and bit depth
            screen_width = lparam & 0xFFFF
            screen_height = (lparam >> 16) & 0xFFFF
            bpp = wparam
            self.callback(screen_width, screen_height, bpp)

        return DefWindowProc(hwnd, msg, wparam, lparam)


class WindowsProvider(QObject):
    LOG_NAME = 'wdl'

    changed = Signal(list)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.log = Log.child(self.LOG_NAME)

        self._screen_change_observer = ScreenChangeObserver(self._on_screen_configuration_changed)

        self._displays = []
        self._fetch_display_list()

        self.log.debug('Initialized')

    def _on_screen_configuration_changed(self, *_):
        self.log.debug(f'Screen configuration changed')
        self._fetch_display_list()

    @property
    def displays(self):
        return self._displays

    # When bundled as a standalone binary we cannot just delegate a function call to a new python interpreter instance,
    # we have to run another standalone binary to get the fresh display list :facepalm:
    @staticmethod
    def _is_running_from_exe():
        return getattr(sys, 'frozen', False)

    @staticmethod
    def _get_startup_info():
        # Avoid the terminal window popping up when getting a list of displays.
        # The terminal window popping up results in a resolution change and if the reason for getting the display list
        # was a screen resolution change then we get into an endless loop.
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        return si

    @staticmethod
    def _extra_run_flags() -> dict:
        return {
            'capture_output': True,
            'check': True,
            # 'creationflags': subprocess.CREATE_NO_WINDOW,
            # 'startupinfo': WindowsProvider._get_startup_info(),
        }

    @staticmethod
    def _get_display_list_standalone() -> str:
        our_dir = os.path.dirname(sys.executable)
        list_getter = os.path.join(our_dir, 'osh-display-list.exe')
        return subprocess.run([list_getter], text=True, **WindowsProvider._extra_run_flags()).stdout

    @staticmethod
    def _get_display_list_interpreted() -> str:
        code = 'from obs_scene_helper.controller.system.provider.display_list.windows import get_display_list\r\n' \
               'get_display_list()'

        return subprocess.run([sys.executable, "-c", code], text=True, **WindowsProvider._extra_run_flags()).stdout

    def _fetch_display_list(self):
        try:
            self.log.debug('Fetching display list')

            if self._is_running_from_exe():
                get_result = self._get_display_list_standalone()
            else:
                get_result = self._get_display_list_interpreted()

            displays_json = json.loads(get_result)
            new_list = [x['name'] for x in displays_json]
            self.log.debug(f'New temporary list: {new_list}')

            if sorted(self._displays) != sorted(new_list):
                self._displays = new_list
                self.changed.emit(self._displays)
                self.log.info(f'Display list changed')
            else:
                self.log.info(f'Display list not unchanged')

        except Exception as e:
            self.log.error(f"Error getting display list: {str(e)}")


def get_display_list():
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QScreen
    from typing import List
    import json

    app = QApplication([])
    screens = app.screens()  # type: List[QScreen]

    res = []
    for screen in screens:
        if len(screen.name()) == 0:
            continue

        res.append({
            'name': screen.name(),
            'model': screen.model(),
            'serial': screen.serialNumber(),
            'manufacturer': screen.manufacturer(),
        })

    print(json.dumps(res))


if __name__ == '__main__':
    get_display_list()
