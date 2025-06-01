# This module will contain various dialog boxes used in the application.
import sys
import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QFileDialog, QGroupBox, QFormLayout, QMessageBox, QWidget, QTabWidget,
    QSpinBox, QDialogButtonBox, QCheckBox # Added QSpinBox, QDialogButtonBox, QCheckBox
)
from PyQt6.QtCore import Qt

# Import the settings manager
from treeweaver.config import settings_manager
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

        # External Tools Tab
        tools_tab = QWidget()
        tools_layout = QFormLayout(tools_tab)
        tools_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.tool_path_edits = {}
        tools_group_box = QGroupBox("External Tool Paths")
        tools_group_layout = QFormLayout()
        tools_group_box.setLayout(tools_group_layout)
        default_tool_paths = settings_manager.default_settings.get("external_tool_paths", {})
        for tool_name in default_tool_paths.keys():
            current_path = self.current_settings.get("external_tool_paths", {}).get(tool_name, "")
            path_edit = QLineEdit(current_path)
            path_edit.setPlaceholderText(f"Path to {tool_name} executable")
            self.tool_path_edits[tool_name] = path_edit
            browse_button = QPushButton("Browse...")
            browse_button.clicked.connect(lambda checked=False, tn=tool_name, pe=path_edit: self._browse_tool_path(tn, pe))
            row_layout = QHBoxLayout()
            row_layout.addWidget(path_edit)
            row_layout.addWidget(browse_button)
            tools_group_layout.addRow(QLabel(f"{tool_name.replace('_', ' ').title()}:"), row_layout)
        tools_layout.addWidget(tools_group_box)
        tab_widget.addTab(tools_tab, "External Tools")

        # Visualization Tab
        viz_tab = QWidget()
        viz_layout = QFormLayout(viz_tab)
        viz_layout.addRow(QLabel("Visualization settings (e.g., font, colors) will go here."))
        tab_widget.addTab(viz_tab, "Visualization")

        # Tool Options Tab (for threads etc)
        tool_options_tab = QWidget()
        tool_options_layout = QFormLayout(tool_options_tab)
        self.tool_option_edits = {}

        tool_options_group = QGroupBox("Thread Counts for External Tools")
        tool_options_group_layout = QFormLayout()
        tool_options_group.setLayout(tool_options_group_layout)

        default_tool_options = settings_manager.default_settings.get("external_tool_options", {})
        for option_key, default_value in default_tool_options.items():
            current_value = self.current_settings.get("external_tool_options", {}).get(option_key, default_value)
            sb = QSpinBox()
            sb.setMinimum(1)
            sb.setMaximum(os.cpu_count() or 32) # Sensible max, fallback if cpu_count is None
            sb.setValue(int(current_value))
            self.tool_option_edits[option_key] = sb
            tool_options_group_layout.addRow(QLabel(f"{option_key.replace('_', ' ').title()}:"), sb)

        tool_options_layout.addWidget(tool_options_group)
        tab_widget.addTab(tool_options_tab, "Tool Options")


        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.accept_settings)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addStretch(1)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

    def _browse_tool_path(self, tool_name, path_edit_widget):
        logger.debug(f"Browsing for tool: {tool_name}")
        current_path = path_edit_widget.text()
        # Use last browsed path for tools, or home dir
        start_dir = settings_manager.get_setting("user_paths.last_settings_tool_path_dir", os.path.expanduser("~"))
        if current_path and os.path.isdir(os.path.dirname(current_path)): # If current path is valid dir
            start_dir = os.path.dirname(current_path)

        file_path, _ = QFileDialog.getOpenFileName(self, f"Select {tool_name.title()} Executable", start_dir)
        if file_path:
            logger.info(f"Selected '{file_path}' for tool '{tool_name}'")
            path_edit_widget.setText(file_path)
            settings_manager.update_setting("user_paths.last_settings_tool_path_dir", os.path.dirname(file_path))
            # No immediate save of settings_manager here, happens on overall dialog save.

    def accept_settings(self):
        logger.debug("Attempting to save settings from dialog.")
        for tool_name, path_edit in self.tool_path_edits.items():
            self.current_settings.get("external_tool_paths", {})[tool_name] = path_edit.text()

        for option_key, spin_box in self.tool_option_edits.items():
            self.current_settings.get("external_tool_options", {})[option_key] = spin_box.value()

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

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.model_edit = QLineEdit(current_model)
        form_layout.addRow(QLabel("Substitution Model:"), self.model_edit)

        self.bootstrap_spinbox = QSpinBox()
        self.bootstrap_spinbox.setMinimum(0)
        self.bootstrap_spinbox.setMaximum(10000)
        self.bootstrap_spinbox.setValue(100) # Default bootstraps
        form_layout.addRow(QLabel("Bootstrap Replicates:"), self.bootstrap_spinbox)

        self.prefix_edit = QLineEdit("TreeWeaver_RAxML")
        form_layout.addRow(QLabel("Output Prefix:"), self.prefix_edit)

        self.threads_spinbox = QSpinBox()
        self.threads_spinbox.setMinimum(1)
        self.threads_spinbox.setMaximum(os.cpu_count() or 32)
        default_threads = settings_manager.get_setting("external_tool_options.raxmlng_threads", 1)
        try:
            self.threads_spinbox.setValue(int(default_threads))
        except ValueError:
            self.threads_spinbox.setValue(1)
            logger.warning(f"Invalid raxmlng_threads value '{default_threads}', defaulting to 1.")
        form_layout.addRow(QLabel("Number of Threads:"), self.threads_spinbox)

        layout.addLayout(form_layout)

        # OK and Cancel buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def get_parameters(self) -> dict:
        """Returns a dictionary of the chosen RAxML-NG parameters."""
        return {
            "model": self.model_edit.text(),
            "bootstraps": self.bootstrap_spinbox.value(),
            "prefix": self.prefix_edit.text(),
            "threads": self.threads_spinbox.value()
        }


if __name__ == '__main__':
    # This is for testing the Dialogs independently
    app = QApplication(sys.argv)
    logging.basicConfig(level=logging.DEBUG)

    # Apply a basic dark theme for testing consistency (same as SettingsDialog test)
    dark_stylesheet = """ ... """ # Assuming stylesheet is defined
    # app.setStyleSheet(dark_stylesheet) # Apply if needed

    # Test SettingsDialog
    settings_dialog = SettingsDialog()
    # settings_dialog.show() # Use show() for non-modal or exec() for modal

    # Test RaxmlDialog
    raxml_dialog = RaxmlDialog(current_model="GTR+G")
    if raxml_dialog.exec() == QDialog.DialogCode.Accepted:
        params = raxml_dialog.get_parameters()
        logger.info(f"RAxML Dialog Accepted. Parameters: {params}")
    else:
        logger.info("RAxML Dialog Cancelled.")

    # sys.exit(app.exec()) # Only one app.exec() if testing multiple dialogs
    # For individual testing, uncomment one dialog test and its exec() call.
    # For now, just running RaxmlDialog test
    sys.exit() # Exit after RaxmlDialog test for this example
