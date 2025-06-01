# This module defines the panel for displaying loaded sequence information.

import logging
from PyQt6.QtWidgets import QDockWidget, QListWidget, QVBoxLayout, QWidget, QLabel, QListWidgetItem
from PyQt6.QtCore import Qt

# Assuming treeweaver.core.data_structures.SequenceData is available
# We need to handle the case where treeweaver.core might not be in the path
# if running this file directly for testing, but for application runs, it should be.
try:
    from treeweaver.core import SequenceData, SequenceRecord # Use SequenceRecord for type hint
except ImportError:
    # Fallback for direct testing or if imports are tricky during development phases
    # This allows the class to be defined, but it won't function correctly without SequenceData
    logging.warning("Could not import SequenceData from treeweaver.core. SequencePanel may not work as expected.")
    SequenceData = None # type: ignore
    SequenceRecord = None # type: ignore


logger = logging.getLogger(__name__)

class SequencePanel(QDockWidget):
    """
    A dockable widget that displays a list of loaded sequences.
    """
    def __init__(self, title: str = "Loaded Sequences", parent: QWidget = None):
        super().__init__(title, parent)
        self.setObjectName("SequencePanelDock") # Important for saving/restoring dock widget state

        self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)

        # Main widget for the dock
        self._main_widget = QWidget()
        self._layout = QVBoxLayout(self._main_widget)

        self._list_widget = QListWidget()
        self._list_widget.setObjectName("SequenceListWidget")
        # self._list_widget.itemDoubleClicked.connect(self._on_item_double_clicked) # Example future connection

        self._layout.addWidget(self._list_widget)
        self.setWidget(self._main_widget) # Set the QWidget as the content of the QDockWidget

        logger.info("SequencePanel initialized.")

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
