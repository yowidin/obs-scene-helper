from typing import Optional

from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPainter, QColor, QPixmap, QColorConstants, QPainterPath, QPen
from PySide6.QtCore import QTimer, Qt, QRect, QSize, QObject, Signal

from obs_scene_helper.controller.obs.connection import ConnectionState, Connection
from obs_scene_helper.controller.obs.recording import RecordingState
from obs_scene_helper.model.settings.preset import Preset


class SystemTraySignals(QObject):
    quit_requested = Signal()
    presets_list_requested = Signal()
    obs_settings_requested = Signal()
    osh_settings_requested = Signal()
    logs_requested = Signal()


class TrayIcon(QSystemTrayIcon):
    def __init__(self, obs_connection: Connection, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.signals = SystemTraySignals()

        self.obs_connection = obs_connection

        self.animation_frame = 0
        self.extra_message = None
        self.last_error = None
        self.last_preset = None  # type: Preset | None

        # Initialize animation timer
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._update_animation)

        # Create context menu
        self.menu = QMenu()
        self.menu.addAction("Presets", lambda: self.signals.presets_list_requested.emit())
        self.menu.addAction("OBS Settings", lambda: self.signals.obs_settings_requested.emit())
        self.menu.addSeparator()
        self.menu.addAction("Settings", lambda: self.signals.osh_settings_requested.emit())
        self.menu.addAction("Logs", lambda: self.signals.logs_requested.emit())
        self.menu.addSeparator()
        self.menu.addAction("Quit", lambda: self.signals.quit_requested.emit())
        self.setContextMenu(self.menu)

        # Initial icon setup
        self._update_icon()
        self.show()

        # Connect signals
        self.obs_connection.connection_state_changed.connect(self._connection_state_changed)
        self.obs_connection.recording.state_changed.connect(self._recording_state_changed)
        self.obs_connection.on_error.connect(self._on_error)

    def preset_activated(self, new_preset: Preset):
        self.last_preset = new_preset
        self._update_state()

    @property
    def _connection_state(self) -> ConnectionState:
        return self.obs_connection.connection_state

    @property
    def _recording_state(self) -> RecordingState:
        return self.obs_connection.recording.state

    def _connection_state_changed(self, state: ConnectionState, message: Optional[str]):
        self.extra_message = message
        if state == ConnectionState.Connected:
            self.last_error = None
        self._update_state()

    def _recording_state_changed(self, _: RecordingState):
        self.last_error = None
        self._update_state()

    def _on_error(self, error: str):
        self.last_error = error
        self._update_state()

    def _create_icon(self):
        # Create a 64x64 icon (scaled down automatically by the system)
        size = QSize(64, 64)
        icon_pixmap = QPixmap(size)
        icon_pixmap.fill(QColorConstants.Transparent)

        painter = QPainter(icon_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw the base circle
        painter.setPen(Qt.PenStyle.NoPen)
        if self._connection_state == ConnectionState.Connected:
            painter.setBrush(QColor(0, 0, 0))  # Black for connected
        else:
            painter.setBrush(QColor(128, 128, 128))  # Gray for disconnected

        outer_rect = QRect(2, 2, 60, 60)
        inner_rect = QRect(14, 14, 36, 36)

        painter.drawEllipse(outer_rect)

        def draw_animated_wheel():
            painter.save()
            painter.translate(32, 32)
            painter.rotate(self.animation_frame * 4.5)
            for i in range(8):
                painter.rotate(45)
                painter.drawEllipse(-8, -20, 4, 14)
            painter.restore()

        def draw_pause_bars():
            painter.drawRect(18, 16, 10, 32)
            painter.drawRect(36, 16, 10, 32)

        def draw_active_recording():
            painter.drawEllipse(inner_rect)

        def draw_stopped_recording():
            painter.drawRect(18, 18, 28, 28)

        def draw_question_mark():
            painter.save()
            path = QPainterPath()

            path.moveTo(22, 22)  # Start at the beginning of the top part
            path.arcTo(22, 14, 20, 20, 180, -270)  # curved top part
            path.lineTo(32, 38)  # stem down

            # Bottom dot
            path.moveTo(32, 50)
            path.addEllipse(30, 48, 4, 4)

            # Set pen for outline
            painter.setPen(QPen(QColorConstants.White, 4, Qt.PenStyle.SolidLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)

            painter.drawPath(path)
            painter.restore()

        # Draw recording status indicator
        if self._connection_state == ConnectionState.Connected:
            painter.setBrush(QColorConstants.White)

            if self._recording_state in [RecordingState.Starting, RecordingState.Stopping]:
                # Draw animated loading segments
                draw_animated_wheel()

            elif self._recording_state == RecordingState.Active:
                draw_active_recording()

            elif self._recording_state == RecordingState.Paused:
                draw_pause_bars()

            elif self._recording_state == RecordingState.Stopped:
                draw_stopped_recording()

            elif self._recording_state == RecordingState.Unknown:
                draw_question_mark()

        painter.end()
        return QIcon(icon_pixmap)

    def _update_animation(self):
        self.animation_frame = (self.animation_frame + 1) % 30
        self._update_icon()

    def _update_icon(self):
        self.setIcon(self._create_icon())

    def _update_state(self):
        def stop_animations():
            self.animation_timer.stop()
            self.animation_frame = 0

        if self._connection_state == ConnectionState.Connected and self._recording_state is not RecordingState.Unknown:
            # Handle animations
            if self._recording_state in [RecordingState.Starting, RecordingState.Stopping]:
                self.animation_timer.start(int(1000 / 30))  # 30 FPS
            else:
                stop_animations()
        else:
            stop_animations()

        self._update_icon()

        # Update tooltip
        tooltip = (
            f"OBS Scene Helper\n"
            f"Status: {self._connection_state.name}, recording is {self._recording_state.value}"
        )

        if self.last_preset is not None:
            tooltip += f"\nPreset: {self.last_preset.name}"
        if self.extra_message is not None and len(self.extra_message) > 0:
            tooltip += f"\nMessage: {self.extra_message}"
        if self.last_error is not None and len(self.last_error) > 0:
            tooltip += f"\n\nError: {self.last_error}"

        self.setToolTip(tooltip)
