from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLineEdit, QTableView, QHeaderView
from PySide6.QtWidgets import QPushButton

from PySide6.QtCore import Qt, QSortFilterProxyModel, QSize

from obs_scene_helper.controller.system.log import Log
from obs_scene_helper.model.log.table import Column, Table as LogTable

from obs_scene_helper.view.widgets.app_window import AppWindow


class LogFilterProxyModel(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self.search_text: str = ""

    def filterAcceptsRow(self, source_row, source_parent):
        # noinspection PyTypeChecker
        source_model = self.sourceModel()  # type: LogTable

        if len(self.search_text) != 0:
            message_index = source_model.index(source_row, source_model.index_from_column(Column.Message))
            message = source_model.data(message_index)
            if self.search_text.lower() not in message.lower():
                return False

        return True

    def set_search_text(self, text: str):
        self.search_text = text
        self.invalidateFilter()


class AutoScrollTableView(QTableView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.auto_scroll = True

    def rowsInserted(self, parent, start: int, end: int):
        super().rowsInserted(parent, start, end)
        if self.auto_scroll:
            self.scrollToBottom()


class Logs(AppWindow):
    def __init__(self):
        super().__init__("Logs")

        layout = QVBoxLayout()

        # Filtering
        filter_layout = QHBoxLayout()

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search logs...")

        clear_filters_button = QPushButton("Clear Filters")
        clear_logs_button = QPushButton("Clear All Logs")

        filter_layout.addWidget(self.search_box)
        filter_layout.addWidget(clear_filters_button)
        filter_layout.addWidget(clear_logs_button)

        # Logs Table
        self.table = AutoScrollTableView()
        self.model = Log.INSTANCE.model
        self.proxy_model = LogFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)

        self.table.setModel(self.proxy_model)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)

        horizontal_header = self.table.horizontalHeader()
        horizontal_header.setSectionResizeMode(self.model.index_from_column(Column.Time),
                                               QHeaderView.ResizeMode.ResizeToContents)
        horizontal_header.setSectionResizeMode(self.model.index_from_column(Column.Message),
                                               QHeaderView.ResizeMode.Stretch)

        self.table.setSortingEnabled(True)
        self.table.sortByColumn(self.model.index_from_column(Column.Time), Qt.SortOrder.AscendingOrder)
        self.table.setMouseTracking(True)

        layout.addLayout(filter_layout)
        layout.addWidget(self.table)

        self.setLayout(layout)

        self.setMinimumSize(QSize(800, 600))

        self.search_box.textChanged.connect(self._on_search_text_changed)
        clear_filters_button.clicked.connect(self._clear_filters)
        clear_logs_button.clicked.connect(self.model.clear_logs)

    def _on_search_text_changed(self, text: str):
        self.proxy_model.set_search_text(text)

    def _clear_filters(self):
        self.search_box.clear()
