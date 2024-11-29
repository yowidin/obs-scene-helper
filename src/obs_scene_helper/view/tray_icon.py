from typing import Optional

from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPainter, QColor, QPixmap, QColorConstants
from PySide6.QtCore import QTimer, Qt, QRect, QSize, QObject, Signal

from obs_scene_helper.controller.obs.connection import ConnectionState, RecordingState, Connection


class SystemTraySignals(QObject):
    quit_requested = Signal()


class TrayIcon(QSystemTrayIcon):
    def __init__(self, connection: Connection, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.signals = SystemTraySignals()

        self.connection = connection

        self.animation_frame = 0
        self.current_state = ConnectionState.Disconnected  # type: ConnectionState
        self.recording_state = RecordingState.Stopped  # type: RecordingState
        self.extra_message = None

        # Initialize animation timer
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._update_animation)

        # Create context menu
        self.menu = QMenu()
        self.menu.addAction("Exit", self.quit_app)
        self.setContextMenu(self.menu)

        # Initial icon setup
        self._update_icon()
        self.show()

        # Connect signals
        self.connection.connection_state_changed.connect(self._connection_state_changed)
        self.connection.recording_state_changed.connect(self._recording_state_changed)

    def _connection_state_changed(self, state: ConnectionState, message: Optional[str]):
        self.current_state = state
        self.extra_message = message
        if state != ConnectionState.Connected:
            self.recording_state = None

        self._update_state()

    def _recording_state_changed(self, state: RecordingState):
        self.recording_state = state
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
        if self.current_state == ConnectionState.Connected:
            painter.setBrush(QColor(0, 0, 0))  # Black for connected
        else:
            painter.setBrush(QColor(128, 128, 128))  # Gray for disconnected

        outer_rect = QRect(4, 4, 56, 56)
        painter.drawEllipse(outer_rect)

        # Draw recording status indicator
        if self.current_state == ConnectionState.Connected:
            painter.setBrush(QColorConstants.White)
            inner_rect = QRect(16, 16, 32, 32)

            if self.recording_state in [RecordingState.Starting, RecordingState.Stopping]:
                # Draw animated loading segments
                painter.save()
                painter.translate(32, 32)
                painter.rotate(self.animation_frame * 4.5)
                for i in range(8):
                    painter.rotate(45)
                    painter.drawRect(-2, -16, 4, 8)
                painter.restore()

            elif self.recording_state == RecordingState.Active:
                # Draw recording circle
                painter.drawEllipse(inner_rect)

            elif self.recording_state == RecordingState.Paused:
                # Draw pause bars
                painter.drawRect(24, 16, 6, 32)
                painter.drawRect(34, 16, 6, 32)

            elif self.recording_state == RecordingState.Stopped:
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
        if self.current_state == ConnectionState.Connected and self.recording_state is not None:
            # Handle animations
            if self.recording_state in [RecordingState.Starting, RecordingState.Stopping]:
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
                  f"Status: {self.current_state.name}"
        if self.recording_state is not None:
            tooltip += f", recording is {self.recording_state.value}"
        if self.extra_message is not None and len(self.extra_message) > 0:
            tooltip += f"\nMessage: {self.extra_message}"
        self.setToolTip(tooltip)

    def quit_app(self):
        self.signals.quit_requested.emit()
