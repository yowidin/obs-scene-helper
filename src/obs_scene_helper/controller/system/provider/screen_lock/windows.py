from typing import Callable

from PySide6.QtCore import QObject, Signal, QCoreApplication

import win32con
from win32gui import CreateWindowEx, WNDCLASS, RegisterClass, DefWindowProc, DestroyWindow, UnregisterClass
from win32api import GetModuleHandle

import win32ts
from win32ts import WTSRegisterSessionNotification, WTSUnRegisterSessionNotification

# window messages
WM_WTSSESSION_CHANGE = 0x2B1

# WM_WTSSESSION_CHANGE events (wparam)
WTS_SESSION_LOCK = 0x7
WTS_SESSION_UNLOCK = 0x8


class SessionChangeObserver:
    CLASS_NAME = "OSHSessionChangeObserver"

    """ Hidden window-based observer to capture WM_WTSSESSION_CHANGE messages. """

    def __init__(self, callback: Callable[[bool], None]):
        self.callback = callback

        self.hwnd, self.win_class = self._create_hidden_window()

        WTSRegisterSessionNotification(self.hwnd, win32ts.NOTIFY_FOR_THIS_SESSION)

    def destroy(self):
        if self.hwnd is not None:
            WTSUnRegisterSessionNotification(self.hwnd)

            DestroyWindow(self.hwnd)
            self.hwnd = None

        if self.win_class is not None:
            UnregisterClass(self.win_class, GetModuleHandle(None))
            self.win_class = None

    def _create_hidden_window(self):
        hinstance = GetModuleHandle(None)

        wndclass = WNDCLASS()
        wndclass.lpfnWndProc = self._window_proc
        wndclass.lpszClassName = self.CLASS_NAME
        wndclass.hInstance = hinstance
        win_class = RegisterClass(wndclass)

        hwnd = CreateWindowEx(0, self.CLASS_NAME, None, win32con.WS_OVERLAPPED, win32con.CW_USEDEFAULT,
                              win32con.CW_USEDEFAULT, win32con.CW_USEDEFAULT, win32con.CW_USEDEFAULT, None, None,
                              hinstance, None)

        return hwnd, win_class

    def _window_proc(self, hwnd, msg, wparam, lparam):
        if msg == WM_WTSSESSION_CHANGE:
            if wparam == WTS_SESSION_LOCK:
                self.callback(True)
            elif wparam == WTS_SESSION_UNLOCK:
                self.callback(False)

        return DefWindowProc(hwnd, msg, wparam, lparam)


class WindowsScreenLockProvider(QObject):
    screen_locked = Signal()
    screen_unlocked = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._session_change_observer = SessionChangeObserver(self._on_session_change)

        QCoreApplication.instance().aboutToQuit.connect(self._about_to_quit)

    def _about_to_quit(self):
        self._session_change_observer.destroy()

    def _on_session_change(self, locked: bool):
        if locked:
            self._on_screen_locked()
        else:
            self._on_screen_unlocked()

    def _on_screen_locked(self):
        self.screen_locked.emit()

    def _on_screen_unlocked(self):
        self.screen_unlocked.emit()
