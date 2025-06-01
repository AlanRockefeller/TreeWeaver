# This module will contain various dialog boxes used in the application.
import sys
import os
import re # For sequence validation
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QFileDialog, QGroupBox, QFormLayout, QMessageBox, QWidget, QTabWidget,
    QSpinBox, QDialogButtonBox, QCheckBox,
    QFontComboBox, QDoubleSpinBox,
    QTextEdit, QPlainTextEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QTextOption

from treeweaver.config import settings_manager
from treeweaver.core.help_manager import get_help_html # Import help content getter
import logging

logger = logging.getLogger(__name__)

class SettingsDialog(QDialog):
    """Dialog for managing application settings."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(600)
        self.current_settings = settings_manager.load_settings()
        main_layout = QVBoxLayout(self)
        tab_widget = QTabWidget(self)
        main_layout.addWidget(tab_widget)
        # --- External Tools Tab ---
        tools_tab = QWidget()
        tools_main_layout = QVBoxLayout(tools_tab)
        tools_paths_group_box = QGroupBox("External Tool Paths")
        tools_paths_layout = QFormLayout(); tools_paths_group_box.setLayout(tools_paths_layout)
        self.tool_path_edits = {}
        default_tool_paths = settings_manager.default_settings.get("external_tool_paths", {})
        for tool_name in default_tool_paths.keys():
            current_path = self.current_settings.get("external_tool_paths", {}).get(tool_name, "")
            path_edit = QLineEdit(current_path)
            path_edit.setPlaceholderText(f"Path to {tool_name} executable or command")
            self.tool_path_edits[tool_name] = path_edit
            browse_button = QPushButton("Browse...")
            browse_button.clicked.connect(lambda checked=False, tn=tool_name, pe=path_edit: self._browse_tool_path(tn, pe))
            row_layout = QHBoxLayout(); row_layout.addWidget(path_edit, 1); row_layout.addWidget(browse_button)
            tools_paths_layout.addRow(QLabel(f"{tool_name.replace('_', ' ').title()}:"), row_layout)
        tools_main_layout.addWidget(tools_paths_group_box)
        tool_options_group = QGroupBox("Thread Counts for External Tools")
        tool_options_layout = QFormLayout(); tool_options_group.setLayout(tool_options_layout)
        self.tool_option_edits = {}
        default_tool_options = settings_manager.default_settings.get("external_tool_options", {})
        for option_key, default_value in default_tool_options.items():
            current_value = self.current_settings.get("external_tool_options", {}).get(option_key, default_value)
            sb = QSpinBox(); sb.setMinimum(1); sb.setMaximum(os.cpu_count() or 64)
            try: sb.setValue(int(current_value))
            except ValueError: sb.setValue(int(default_value)); logger.warning(f"Invalid value for {option_key}")
            self.tool_option_edits[option_key] = sb
            tool_options_layout.addRow(QLabel(f"{option_key.replace('_', ' ').title()}:"), sb)
        tools_main_layout.addWidget(tool_options_group)
        tools_tab.setLayout(tools_main_layout)
        tab_widget.addTab(tools_tab, "External Tools")
        # --- Visualization Tab ---
        viz_tab = QWidget()
        viz_layout = QFormLayout(viz_tab)
        self.font_family_combo = QFontComboBox()
        current_font_family = settings_manager.get_setting("visualization.font_family", "Arial")
        self.font_family_combo.setCurrentFont(QFont(current_font_family))
        viz_layout.addRow(QLabel("Font Family (Tree):"), self.font_family_combo)
        self.font_size_spinbox = QSpinBox(); self.font_size_spinbox.setMinimum(6); self.font_size_spinbox.setMaximum(24)
        self.font_size_spinbox.setValue(settings_manager.get_setting("visualization.font_size", 8))
        viz_layout.addRow(QLabel("Font Size (Tree Labels):"), self.font_size_spinbox)
        self.line_thickness_spinbox = QDoubleSpinBox(); self.line_thickness_spinbox.setMinimum(0.5)
        self.line_thickness_spinbox.setMaximum(5.0); self.line_thickness_spinbox.setSingleStep(0.1)
        self.line_thickness_spinbox.setDecimals(1)
        self.line_thickness_spinbox.setValue(settings_manager.get_setting("visualization.line_thickness", 1.0))
        viz_layout.addRow(QLabel("Line Thickness (Tree Branches):"), self.line_thickness_spinbox)
        self.show_confidence_checkbox = QCheckBox("Show confidence values on tree")
        self.show_confidence_checkbox.setChecked(settings_manager.get_setting("visualization.show_confidence_values", True))
        viz_layout.addRow(self.show_confidence_checkbox)
        viz_tab.setLayout(viz_layout)
        tab_widget.addTab(viz_tab, "Visualization")
        # --- Dialog Buttons ---
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept_settings)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)
        self.setLayout(main_layout)

    def _browse_tool_path(self, tool_name, path_edit_widget):
        logger.debug(f"Browsing for tool: {tool_name}")
        current_path_text = path_edit_widget.text()
        start_dir = settings_manager.get_setting("user_paths.last_settings_tool_path_dir", os.path.expanduser("~"))
        if current_path_text and os.path.isdir(os.path.dirname(current_path_text)):
            start_dir = os.path.dirname(current_path_text)
        file_path, _ = QFileDialog.getOpenFileName(self, f"Select {tool_name.title()} Executable", start_dir)
        if file_path:
            path_edit_widget.setText(file_path)
            settings_manager.update_setting("user_paths.last_settings_tool_path_dir", os.path.dirname(file_path))

    def accept_settings(self):
        logger.debug("Attempting to save settings from dialog.")
        for tool_name, path_edit in self.tool_path_edits.items():
            self.current_settings.get("external_tool_paths", {})[tool_name] = path_edit.text()
        for option_key, spin_box in self.tool_option_edits.items():
            self.current_settings.get("external_tool_options", {})[option_key] = spin_box.value()
        vis_settings = self.current_settings.get("visualization", {})
        vis_settings["font_family"] = self.font_family_combo.currentFont().family()
        vis_settings["font_size"] = self.font_size_spinbox.value()
        vis_settings["line_thickness"] = self.line_thickness_spinbox.value()
        vis_settings["show_confidence_values"] = self.show_confidence_checkbox.isChecked()
        if settings_manager.save_settings(self.current_settings):
            logger.info("Settings saved successfully via dialog.")
            QMessageBox.information(self, "Settings Saved", "Your settings have been saved.")
            self.accept()
        else:
            logger.error("Failed to save settings via dialog.")
            QMessageBox.critical(self, "Error Saving Settings", "Could not save settings.")

class RaxmlDialog(QDialog):
    """Dialog for configuring RAxML-NG parameters."""
    def __init__(self, current_model: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("RAxML-NG Parameters")
        layout = QVBoxLayout(self); form_layout = QFormLayout()
        self.model_edit = QLineEdit(current_model)
        form_layout.addRow(QLabel("Substitution Model:"), self.model_edit)
        self.bootstrap_spinbox = QSpinBox(); self.bootstrap_spinbox.setMinimum(0)
        self.bootstrap_spinbox.setMaximum(10000); self.bootstrap_spinbox.setValue(100)
        form_layout.addRow(QLabel("Bootstrap Replicates:"), self.bootstrap_spinbox)
        self.prefix_edit = QLineEdit("TreeWeaver_RAxML")
        form_layout.addRow(QLabel("Output Prefix:"), self.prefix_edit)
        self.threads_spinbox = QSpinBox(); self.threads_spinbox.setMinimum(1)
        self.threads_spinbox.setMaximum(os.cpu_count() or 64)
        default_threads = settings_manager.get_setting("external_tool_options.raxmlng_threads", 1)
        try: self.threads_spinbox.setValue(int(default_threads))
        except ValueError: self.threads_spinbox.setValue(1); logger.warning(f"Invalid raxmlng_threads value")
        form_layout.addRow(QLabel("Number of Threads:"), self.threads_spinbox)
        layout.addLayout(form_layout)
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept); self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
    def get_parameters(self) -> dict:
        return {"model": self.model_edit.text(), "bootstraps": self.bootstrap_spinbox.value(),
                "prefix": self.prefix_edit.text(), "threads": self.threads_spinbox.value()}

class SequenceEditDialog(QDialog):
    """Dialog for editing a sequence ID and its string data."""
    # Basic valid sequence characters (DNA/RNA/Protein + ambiguity/gaps)
    # More specific validation (e.g. DNA only) could be added if sequence type is known.
    VALID_SEQ_CHARS_REGEX = re.compile(r"^[ACGTUNRYWSMKBDHVNacgtunrywmksbdhvn\-\?]+$")

    def __init__(self, sequence_id: str, sequence_string: str, existing_ids: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Edit Sequence: {sequence_id}")
        self.original_id = sequence_id
        # All other existing IDs, excluding the current one being edited
        self.other_existing_ids = [ex_id for ex_id in existing_ids if ex_id != self.original_id]

        self.new_id: str = sequence_id
        self.new_seq_str: str = sequence_string

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.id_edit = QLineEdit(sequence_id)
        form_layout.addRow(QLabel("Sequence ID:"), self.id_edit)

        self.seq_edit = QPlainTextEdit(sequence_string)
        self.seq_edit.setWordWrapMode(QTextOption.WrapMode.WrapAnywhere) # Or NoWrap
        monospace_font = QFont("monospace")
        if sys.platform == "darwin": monospace_font.setPointSize(12) # Adjust for macOS if needed
        else: monospace_font.setPointSize(10)
        self.seq_edit.setFont(monospace_font)
        self.seq_edit.setMinimumHeight(200) # Ensure enough space for sequence
        form_layout.addRow(QLabel("Sequence Data:"), self.seq_edit)

        layout.addLayout(form_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.validate_and_accept) # Connect to custom validation
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
        self.setMinimumWidth(500) # Ensure dialog is wide enough

    def validate_and_accept(self):
        """Validates data before accepting the dialog."""
        new_id_val = self.id_edit.text().strip()
        new_seq_val = self.seq_edit.toPlainText().strip().upper() # Standardize to upper for validation & storage

        if not new_id_val:
            QMessageBox.warning(self, "Validation Error", "Sequence ID cannot be empty.")
            return

        if new_id_val != self.original_id and new_id_val in self.other_existing_ids:
            QMessageBox.warning(self, "Validation Error", f"Sequence ID '{new_id_val}' already exists.")
            return

        if not self.VALID_SEQ_CHARS_REGEX.match(new_seq_val) and new_seq_val: # Allow empty seq? For now, no.
            QMessageBox.warning(self, "Validation Error",
                                "Sequence data contains invalid characters.\n"
                                "Allowed: A,C,G,T,U,N,R,Y,W,S,M,K,B,D,H,V, and gap characters like -,?.")
            return
        if not new_seq_val: # Sequence cannot be empty
             QMessageBox.warning(self, "Validation Error", "Sequence data cannot be empty.")
             return


        # If all validations pass
        self.new_id = new_id_val
        self.new_seq_str = new_seq_val
        super().accept() # Call the original accept method

    def get_validated_data(self) -> tuple[str, str]:
        """
        Returns the validated new ID and sequence string.
        This should be called only after the dialog has been accepted.
        """
        return self.new_id, self.new_seq_str

if __name__ == '__main__':
    app = QApplication(sys.argv)
    logging.basicConfig(level=logging.DEBUG)

    # Test SequenceEditDialog
    existing_ids_test = ["existing_seq1", "another_id", "test_seq_to_edit"]
    seq_edit_dialog = SequenceEditDialog("test_seq_to_edit", "ATGCGTN-?", existing_ids_test)
    if seq_edit_dialog.exec() == QDialog.DialogCode.Accepted:
        new_id, new_seq = seq_edit_dialog.get_validated_data()
        logger.info(f"Sequence Edit Dialog Accepted. New ID: {new_id}, New Seq: {new_seq[:30]}...")
    else:
        logger.info("Sequence Edit Dialog Cancelled.")
    # sys.exit() # Keep this commented unless testing only this dialog.

class HelpDialog(QDialog):
    """Dialog to display help content."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("TreeWeaver Help")
        self.setMinimumSize(800, 600) # Set a reasonable default size

        layout = QVBoxLayout(self)

        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True) # For any http links in MD

        try:
            html_content = get_help_html()
            self.text_browser.setHtml(html_content)
        except Exception as e:
            logger.error(f"Failed to load or set HTML for HelpDialog: {e}", exc_info=True)
            self.text_browser.setPlainText(f"Error loading help content: {e}\n\nPlease check logs.")

        layout.addWidget(self.text_browser)

        # Close button
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.button_box.accepted.connect(self.accept) # QDialogButtonBox.Close emits accepted
        self.button_box.rejected.connect(self.reject) # Should not be needed if only Close
        layout.addWidget(self.button_box)

        self.setLayout(layout)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    logging.basicConfig(level=logging.DEBUG)

    # Test HelpDialog
    help_dialog = HelpDialog()
    help_dialog.exec() # Use exec for modal dialog test

    # Test SequenceEditDialog
    # existing_ids_test = ["existing_seq1", "another_id", "test_seq_to_edit"]
    # seq_edit_dialog = SequenceEditDialog("test_seq_to_edit", "ATGCGTN-?", existing_ids_test)
    # if seq_edit_dialog.exec() == QDialog.DialogCode.Accepted:
    #     new_id, new_seq = seq_edit_dialog.get_validated_data()
    #     logger.info(f"Sequence Edit Dialog Accepted. New ID: {new_id}, New Seq: {new_seq[:30]}...")
    # else:
    #     logger.info("Sequence Edit Dialog Cancelled.")

    sys.exit() # Exit after HelpDialog test for this example
