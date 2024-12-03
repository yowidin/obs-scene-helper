from typing import Optional

from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPainter, QColor, QPixmap, QColorConstants
from PySide6.QtCore import QTimer, Qt, QRect, QSize, QObject, Signal

from obs_scene_helper.controller.obs.connection import ConnectionState, RecordingState, Connection


class SystemTraySignals(QObject):
    quit_requested = Signal()
    presets_list_requested = Signal()
    obs_settings_requested = Signal()


class TrayIcon(QSystemTrayIcon):
    def __init__(self, obs_connection: Connection, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.signals = SystemTraySignals()

        self.obs_connection = obs_connection

        self.animation_frame = 0
        self.extra_message = None
        self.last_error = None

        # Initialize animation timer
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._update_animation)

        # Create context menu
        self.menu = QMenu()
        self.menu.addAction("Presets", lambda: self.signals.presets_list_requested.emit())
        self.menu.addAction("OBS Settings", lambda: self.signals.obs_settings_requested.emit())
        self.menu.addSeparator()
        self.menu.addAction("Quit", lambda: self.signals.quit_requested.emit())
        self.setContextMenu(self.menu)

        # Initial icon setup
        self._update_icon()
        self.show()

        # Connect signals
        self.obs_connection.connection_state_changed.connect(self._connection_state_changed)
        self.obs_connection.recording_state_changed.connect(self._recording_state_changed)
        self.obs_connection.on_error.connect(self._on_error)

    @property
    def _connection_state(self) -> ConnectionState:
        return self.obs_connection.connection_state

    @property
    def _recording_state(self) -> Optional[RecordingState]:
        return self.obs_connection.recording_state

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

        outer_rect = QRect(4, 4, 56, 56)
        painter.drawEllipse(outer_rect)

        # Draw recording status indicator
        if self._connection_state == ConnectionState.Connected:
            painter.setBrush(QColorConstants.White)
            inner_rect = QRect(16, 16, 32, 32)

            if self._recording_state in [RecordingState.Starting, RecordingState.Stopping]:
                # Draw animated loading segments
                painter.save()
                painter.translate(32, 32)
                painter.rotate(self.animation_frame * 4.5)
                for i in range(8):
                    painter.rotate(45)
                    painter.drawRect(-2, -16, 4, 8)
                painter.restore()

            elif self._recording_state == RecordingState.Active:
                # Draw recording circle
                painter.drawEllipse(inner_rect)

            elif self._recording_state == RecordingState.Paused:
                # Draw pause bars
                painter.drawRect(24, 16, 6, 32)
                painter.drawRect(34, 16, 6, 32)

            elif self._recording_state == RecordingState.Stopped:
                # Draw stop square
                painter.drawRect(inner_rect)

        painter.end()
        return QIcon(icon_pixmap)

    def _update_animation(self):
        self.animation_frame = (self.animation_frame + 1) % 30
        self._update_icon()

    def _update_icon(self):
        self.setIcon(self._create_icon())

    def _update_state(self):
        if self._connection_state == ConnectionState.Connected and self._recording_state is not None:
            # Handle animations
            if self._recording_state in [RecordingState.Starting, RecordingState.Stopping]:
                self.animation_timer.start(int(1000 / 30))  # 30 FPS
            else:
                self.animation_timer.stop()
                self.animation_frame = 0
        else:
            self.animation_timer.stop()
            self.animation_frame = 0

        self._update_icon()

        # Update tooltip
        tooltip = f"OBS Scene Helper\n" \
                  f"Status: {self._connection_state.name}"
        if self._recording_state is not None:
            tooltip += f", recording is {self._recording_state.value}"
        if self.extra_message is not None and len(self.extra_message) > 0:
            tooltip += f"\nMessage: {self.extra_message}"
        if self.last_error is not None and len(self.last_error) > 0:
            tooltip += f"\n\nError: {self.last_error}"
        self.setToolTip(tooltip)
