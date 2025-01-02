from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor

from typing import Optional
from datetime import datetime
from collections import deque

from enum import Enum

import logging


class Column(Enum):
    Time = 0
    Logger = 1
    Severity = 2
    Message = 3


class Table(QAbstractTableModel):
    DEFAULT_MAX_ENTRIES = 100000
    TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

    HEADERS = [Column.Time, Column.Logger, Column.Severity, Column.Message]

    SEVERITY_COLORS = {
        logging.DEBUG: QColor("#F1F8E9"),
        logging.INFO: QColor("#EEEEFF"),
        logging.WARNING: QColor("#FFF3E0"),
        logging.ERROR: QColor("#FFEBEE"),
        logging.CRITICAL: QColor("#FF3030"),
    }

    def __init__(self, max_entries: Optional[int] = None):
        super().__init__()
        max_entries = max_entries if max_entries is not None else Table.DEFAULT_MAX_ENTRIES
        self._logs = deque(maxlen=max_entries)

    def column_from_index(self, index: int) -> Column:
        return self.HEADERS[index]

    def index_from_column(self, column: Column) -> int:
        assert column in self.HEADERS
        return self.HEADERS.index(column)

    def rowCount(self, parent: Optional[QModelIndex] = None):
        # Note from Qt documentation:
        # When implementing a table based model, rowCount() should return 0 when the parent is valid.
        if parent is not None and parent.isValid():
            return 0

        return len(self._logs)

    def columnCount(self, parent: Optional[QModelIndex] = None):
        # Note from Qt documentation:
        # When implementing a table based model, columnCount() should return 0 when the parent is valid.
        if parent is not None and parent.isValid():
            return 0

        return len(self.HEADERS)

    @staticmethod
    def _format_item_timestamp(timestamp: float):
        return datetime.fromtimestamp(timestamp).strftime(Table.TIMESTAMP_FORMAT)

    def _get_display_role_for_item(self, entry: logging.LogRecord, column: Column) -> Optional[str]:
        if column == Column.Time:
            return self._format_item_timestamp(entry.created)
        elif column == Column.Logger:
            return entry.name
        elif column == Column.Severity:
            return entry.levelname.lower()
        elif column == Column.Message:
            return entry.msg
        else:
            return None

    def _get_background_role_for_item(self, entry: logging.LogRecord) -> QColor:
        return self.SEVERITY_COLORS.get(entry.levelno, QColor("#FFFFFF"))

    def _get_tooltip_role_for_item(self, entry: logging.LogRecord) -> str:
        details = (
            f"Timestamp: {self._format_item_timestamp(entry.created)}\n"
            f"Module:    {entry.module}\n"
            f"Full path: {entry.pathname}\n"
            f"Message:   {entry.msg}"
        )

        # TODO: maybe add something like exceptions information or callstack
        return details

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        log_entry: logging.LogRecord = self._logs[index.row()]
        column = Column(index.column())

        if role == Qt.ItemDataRole.DisplayRole:
            return self._get_display_role_for_item(log_entry, column)
        elif role == Qt.ItemDataRole.BackgroundRole:
            return self._get_background_role_for_item(log_entry)
        elif role == Qt.ItemDataRole.ToolTipRole:
            return self._get_tooltip_role_for_item(log_entry)

        return None

    def headerData(self, section: int, orientation: Qt.Orientation,
                   role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.HEADERS[section].name
        return None

    def add_record(self, record: logging.LogRecord):
        if len(self._logs) == self._logs.maxlen:
            self.beginRemoveRows(self.index(0, 0), 0, 0)
            self._logs.popleft()
            self.endRemoveRows()

        self.beginInsertRows(self.index(self.rowCount(), 0), self.rowCount(), self.rowCount())
        self._logs.append(record)
        self.endInsertRows()

    def clear_logs(self):
        self.beginResetModel()
        self._logs.clear()
        self.endResetModel()
