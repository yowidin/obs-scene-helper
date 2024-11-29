from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListView, QStyledItemDelegate, QComboBox
from PySide6.QtWidgets import QStyleOptionViewItem, QStyleFactory
from PySide6.QtCore import Qt, QAbstractListModel, Signal, QModelIndex

from typing import Optional, List


class EditableListModel(QAbstractListModel):
    def __init__(self, items: Optional[List[str]] = None, available_options: Optional[List[str]] = None):
        super().__init__()

        self._items = items if items is not None else []
        self._all_options = set(available_options if available_options is not None else [])
        self._update_available_options()

    def _update_available_options(self):
        used_options = set(self._items)
        self._available_options = list(self._all_options - used_options)
        self._available_options.sort()

    def rowCount(self, parent=QModelIndex()):
        return len(self._items)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        if not (0 <= index.row() < len(self._items)):
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            return self._items[index.row()]

        return None

    def setData(self, index: QModelIndex, value, role=Qt.ItemDataRole.EditRole):
        if not index.isValid():
            return None

        if not (0 <= index.row() < len(self._items)):
            return None

        if role != Qt.ItemDataRole.EditRole:
            return False

        old_value = self._items[index.row()]

        if old_value != value:
            self._items[index.row()] = value
            self._update_available_options()
            self.dataChanged.emit(index, index, [role])

        return True

    def flags(self, index: QModelIndex):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags

        return Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def add_item(self, item: str):
        if item not in self._available_options:
            return False

        self.beginInsertRows(QModelIndex(), len(self._items), len(self._items))
        self._items.append(item)
        self._update_available_options()
        self.endInsertRows()
        return True

    def remove_item(self, index):
        if not (0 <= index < len(self._items)):
            return

        self.beginRemoveRows(QModelIndex(), index, index)
        self._items.pop(index)
        self._update_available_options()
        self.endRemoveRows()

    def update_item(self, index, value):
        if not (0 <= index < len(self._items)):
            return

        self.setData(super().index(index, 0), value)

    @property
    def available_options(self):
        return self._available_options

    @property
    def items(self):
        return self._items

    def set_all_options(self, options):
        self._all_options = set(options)
        self._update_available_options()

    def has_available_options(self):
        return len(self._available_options) > 0


class ComboBoxDelegate(QStyledItemDelegate):
    def __init__(self, on_value_change, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.on_value_change = on_value_change

    def _handle_value_change(self, value):
        if self.on_value_change is not None:
            self.on_value_change(value)

    def createEditor(self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex):
        editor = QComboBox(parent)

        # macOS renders the ComboBox with extra shadows and a colorful selection. We don't want this
        editor.setStyle(QStyleFactory.create("Fusion"))

        # noinspection PyTypeChecker
        model = index.model()  # type: EditableListModel

        current_value = index.data(Qt.ItemDataRole.DisplayRole)
        options = [current_value] + [opt for opt in model.available_options if opt != current_value]
        editor.addItems(options)
        editor.setEditable(False)
        editor.currentTextChanged.connect(self._handle_value_change)

        return editor

    def setEditorData(self, editor: QComboBox, index: QModelIndex):
        value = index.data(Qt.ItemDataRole.DisplayRole)
        idx = editor.findText(value)
        if idx >= 0:
            editor.setCurrentIndex(idx)

    def setModelData(self, editor: QComboBox, model: EditableListModel, index: QModelIndex):
        value = editor.currentText()
        model.setData(index, value, Qt.ItemDataRole.EditRole)


class EditableListWidget(QWidget):
    item_added = Signal()
    item_removed = Signal()
    item_changed = Signal()
    no_options_available = Signal()

    def __init__(self, items: Optional[List[str]] = None, available_options: Optional[List[str]] = None, *args,
                 **kwargs):
        super().__init__(*args, **kwargs)

        self.model = EditableListModel(items, available_options)
        self.model.dataChanged.connect(lambda x: self.item_changed.emit())
        self.view = QListView()
        self.view.setModel(self.model)

        self.delegate = ComboBoxDelegate(self._handle_value_change)
        self.view.setItemDelegate(self.delegate)

        self.view.doubleClicked.connect(self.view.edit)
        self.view.setHorizontalScrollMode(QListView.ScrollMode.ScrollPerPixel)
        self.view.setVerticalScrollMode(QListView.ScrollMode.ScrollPerPixel)
        self.view.clicked.connect(lambda x: self._update_button_states())
        self.view.setSpacing(2)

        self.add_button = QPushButton("Add")
        self.remove_button = QPushButton("Remove")
        self.edit_button = QPushButton("Edit")

        self.add_button.clicked.connect(self.add_item)
        self.remove_button.clicked.connect(self.remove_selected_item)
        self.edit_button.clicked.connect(self.edit_selected_item)

        self._update_button_states()

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.remove_button)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.view)
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    def _update_button_states(self):
        has_selection = len(self.view.selectedIndexes()) != 0
        has_options = self.model.has_available_options()

        self.add_button.setEnabled(has_options)
        self.remove_button.setEnabled(has_selection)
        self.edit_button.setEnabled(has_selection)

    def _handle_value_change(self, value):
        indexes = self.view.selectedIndexes()
        if indexes:
            index = indexes[0].row()
            self.model.update_item(index, value)

        self.item_changed.emit()

    def add_item(self):
        available = self.model.available_options
        if available:
            current_editor = self.view.indexWidget(self.view.currentIndex())
            if current_editor:
                self.delegate.closeEditor.emit(current_editor)

            if self.model.add_item(available[0]):
                self.item_added.emit()
                self._update_button_states()
        else:
            self.no_options_available.emit()

    def remove_selected_item(self):
        indexes = self.view.selectedIndexes()
        if indexes:
            index = indexes[0].row()
            self.model.remove_item(index)
            self.item_removed.emit()
            self._update_button_states()

    def edit_selected_item(self):
        indexes = self.view.selectedIndexes()
        if indexes:
            self.view.edit(indexes[0])

    def set_all_options(self, options):
        self.model.set_all_options(options)
        self._update_button_states()

    @property
    def items(self):
        return self.model.items

    @property
    def available_options(self):
        return self.model.available_options
