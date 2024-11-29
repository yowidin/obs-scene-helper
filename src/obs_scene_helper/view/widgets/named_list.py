from typing import Any, Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget
from PySide6.QtCore import Signal


class NamedList(QWidget):
    selection_changed = Signal(object)

    def __init__(self, title: str, items: list[Any], *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.layout = QVBoxLayout(self)
        self.items = items

        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold;")
        self.layout.addWidget(title_label)

        self.list_widget = QListWidget()
        self.layout.addWidget(self.list_widget)

        self._update_items()

        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)

    def _update_items(self):
        self.list_widget.clear()
        self.list_widget.addItems([str(x) for x in self.items])

    def _on_selection_changed(self):
        self.selection_changed.emit(self.selected_item)

    @property
    def selected_item(self) -> Optional[object]:
        idx = self.selected_index
        if idx is None:
            return None

        return self.items[idx]

    @property
    def selected_index(self) -> Optional[int]:
        idx = self.list_widget.currentRow()
        if idx < 0 or len(self.items) == 0:
            return None

        return idx

    def set_items(self, items: list[Any]):
        self.items = items
        self._update_items()
