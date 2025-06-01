# This module defines the panel for displaying loaded sequence information.

import logging
from PyQt6.QtWidgets import QDockWidget, QListWidget, QVBoxLayout, QWidget, QLabel, QListWidgetItem, QMenu
from PyQt6.QtCore import Qt, pyqtSignal, QPoint

try:
    from treeweaver.core import SequenceData, SequenceRecord
except ImportError:
    logging.warning("Could not import SequenceData from treeweaver.core. SequencePanel may not work as expected.")
    SequenceData = None # type: ignore
    SequenceRecord = None # type: ignore

logger = logging.getLogger(__name__)

class SequencePanel(QDockWidget):
    """
    A dockable widget that displays a list of loaded sequences.
    Emits a signal when an edit is requested for a sequence.
    """
    edit_sequence_requested = pyqtSignal(str) # Signal to emit the ID of the sequence to edit

    def __init__(self, title: str = "Loaded Sequences", parent: QWidget = None):
        super().__init__(title, parent)
        self.setObjectName("SequencePanelDock")
        self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)

        self._main_widget = QWidget()
        self._layout = QVBoxLayout(self._main_widget)

        self._list_widget = QListWidget()
        self._list_widget.setObjectName("SequenceListWidget")

        # Context Menu for editing
        self._list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list_widget.customContextMenuRequested.connect(self._show_context_menu)

        # self._list_widget.itemDoubleClicked.connect(self._handle_double_click) # Alternative edit trigger

        self._layout.addWidget(self._list_widget)
        self.setWidget(self._main_widget)

        logger.info("SequencePanel initialized with context menu.")

    # def _handle_double_click(self, item: QListWidgetItem):
    #     """Handles double-click on a list item to trigger edit."""
    #     if item:
    #         seq_id = item.data(Qt.ItemDataRole.UserRole)
    #         if seq_id:
    #             self.edit_sequence_requested.emit(seq_id)

    def _show_context_menu(self, point: QPoint):
        """Shows a context menu for the clicked list item."""
        item = self._list_widget.itemAt(point)
        if item:
            seq_id = item.data(Qt.ItemDataRole.UserRole)
            if not seq_id:
                logger.warning("No sequence ID found for the selected list item.")
                return

            menu = QMenu()
            edit_action = menu.addAction("Edit Sequence...")
            # remove_action = menu.addAction("Remove Sequence") # Future: Implement remove

            action = menu.exec(self._list_widget.mapToGlobal(point))

            if action == edit_action:
                self.edit_sequence_requested.emit(seq_id)
            # elif action == remove_action:
            #     # self.remove_sequence_requested.emit(seq_id) # Need another signal
            #     logger.debug(f"Remove requested for {seq_id} (not implemented yet)")
            #     pass


    def update_sequences(self, sequence_data: SequenceData) -> None:
        """
        Populates the list widget with sequences from the SequenceData object.

        Args:
            sequence_data: A SequenceData object containing the sequences to display.
        """
        self.clear_sequences()
        if not SequenceData: # Check if the import failed
            logger.error("SequenceData type not available. Cannot update sequences.")
            return

        if not sequence_data:
            logger.warning("update_sequences called with None sequence_data.")
            return

        logger.debug(f"Updating sequence panel with {len(sequence_data.get_all_sequences())} sequences.")
        for seq_record in sequence_data.get_all_sequences():
            display_text = f"{seq_record.id} ({seq_record.length}bp)"
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, seq_record.id) # Store original ID for later use
            item.setToolTip(f"ID: {seq_record.id}\nLength: {seq_record.length}bp\nDescription: {seq_record.description}")
            self._list_widget.addItem(item)

        if self._list_widget.count() > 0:
            logger.info(f"Sequence panel updated. Displaying {self._list_widget.count()} sequences.")
        else:
            logger.info("Sequence panel updated, but no sequences to display.")


    def clear_sequences(self) -> None:
        """Clears all items from the sequence list widget."""
        self._list_widget.clear()
        logger.info("Sequence panel cleared.")

    def get_selected_sequence_id(self) -> str | None:
        """
        Returns the original ID of the currently selected sequence.
        Returns None if no item is selected.
        """
        current_item = self._list_widget.currentItem()
        if current_item:
            return current_item.data(Qt.ItemDataRole.UserRole)
        return None

    # Example of a slot that could be connected
    # def _on_item_double_clicked(self, item: QListWidgetItem):
    #     seq_id = item.data(Qt.ItemDataRole.UserRole)
    #     logger.debug(f"Item double-clicked: {seq_id}")
        # Here you could emit a signal or call a method in MainWindow to show details for this sequence


if __name__ == '__main__':
    # Example usage for testing the panel independently
    from PyQt6.QtWidgets import QApplication, QMainWindow
    import sys

    # Mock SequenceData and SequenceRecord for testing if core is not available
    if SequenceData is None:
        class MockSequenceRecord:
            def __init__(self, id, sequence, description=""):
                self.id = id
                self.sequence = sequence
                self.length = len(sequence)
                self.description = description

        class MockSequenceData:
            def __init__(self):
                self.sequences = []
            def add_sequence(self, id, seq, desc=""):
                self.sequences.append(MockSequenceRecord(id, seq, desc))
            def get_all_sequences(self):
                return self.sequences

        SequenceData = MockSequenceData # type: ignore
        SequenceRecord = MockSequenceRecord # type: ignore


    logging.basicConfig(level=logging.DEBUG)
    app = QApplication(sys.argv)

    # Apply a basic dark theme for testing consistency
    dark_stylesheet_test = """
        QMainWindow { background-color: #2b2b2b; }
        QDockWidget { background-color: #2b2b2b; color: #ffffff; }
        QDockWidget::title { background-color: #3c3c3c; padding: 4px; border: 1px solid #2b2b2b; }
        QListWidget { background-color: #3c3c3c; color: #ffffff; border: 1px solid #555555; }
        QListWidget::item { padding: 5px; }
        QListWidget::item:selected { background-color: #555555; }
    """
    app.setStyleSheet(dark_stylesheet_test)

    main_win = QMainWindow()
    main_win.setWindowTitle("Sequence Panel Test")
    main_win.setGeometry(100, 100, 800, 600)

    sequence_panel = SequencePanel(parent=main_win)
    main_win.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, sequence_panel)

    # Create some dummy sequence data
    test_seq_data = SequenceData() # type: ignore
    test_seq_data.add_sequence("SeqA_human_cytochrome_b_gene_partial_cds_mitochondrion", "ATGCGTATGCGTATGCGTATGCGT", "Human cytochrome B") # type: ignore
    test_seq_data.add_sequence("SeqB_mouse", "GATTACAGATTACAGATTACA", "Mouse sequence") # type: ignore
    test_seq_data.add_sequence("SeqC_plant", "CGTACGTAGCTAGCTACG", "Plant sequence") # type: ignore

    sequence_panel.update_sequences(test_seq_data) # type: ignore

    main_win.show()
    sys.exit(app.exec())
