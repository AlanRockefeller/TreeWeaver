#!/usr/bin/env python3
# Main script to launch the TreeWeaver application.

import sys
import argparse
import logging
import json # For pretty printing settings in debug

# Import necessary PyQt6 components
from PyQt6.QtWidgets import QApplication

# Import key components from the treeweaver package
from treeweaver import settings_manager # Centralized settings
from treeweaver.gui import MainWindow     # Main GUI window
# Note: treeweaver.gui.main_window.py also imports settings_manager, which is fine.

# Get a logger for this main script
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="TreeWeaver Phylogenetic Analysis Tool")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging and features.")
    args = parser.parse_args()

    # --- Early settings load ---
    # The settings_manager is already initialized when imported.
    # We can update its internal debug_mode based on CLI argument if desired,
    # or let CLI override specific behaviors without changing the stored setting.
    # For now, let CLI --debug primarily control log level.
    # The stored 'debug_mode' setting could be for other debug features toggled in GUI.

    # --- Configure logging ---
    # Use the debug flag from args to set the logging level for the application
    log_level = logging.DEBUG if args.debug else logging.ERROR

    # Configure the root logger
    # Using basicConfig is fine for simple apps. For more complex scenarios,
    # you might configure handlers and formatters directly.
    logging.basicConfig(stream=sys.stdout,
                        level=log_level, # Set level for all loggers unless they override
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    if args.debug:
        logger.info("Debug mode enabled via command line.")
        # Update the stored setting if you want --debug to also set the persistent debug_mode
        # settings_manager.update_setting('debug_mode', True)
        # settings_manager.save_settings() # And save it
        # logger.debug("Persisted debug_mode setting updated to True due to --debug flag.")

        # Log the loaded settings in debug mode
        logger.debug("Initial loaded settings:\n%s", json.dumps(settings_manager.settings, indent=2))

    # Application startup messages
    logger.info("TreeWeaver Application starting...")
    # Example: logger.error("This is a test error message.") # Test error logging

    app = QApplication(sys.argv)

    # Apply a basic dark theme (can be refined later)
    # This stylesheet is more comprehensive and centralized here.
    # Stylesheet components:
    # QWidget: General styling for all widgets (background, text color)
    # QMainWindow: Specific styling for the main window itself
    # QMenuBar: Specific styling for the menu bar
    # QMenu: Specific styling for menus
    # QToolBar: Styling for toolbars
    # QPushButton: Styling for buttons
    # QDialog: Styling for dialogs (important for SettingsDialog)
    # QLabel: Styling for labels
    # QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox: Styling for text input fields
    # QTreeView, QListView, QTableView: Styling for item views
    # QHeaderView: Styling for headers in item views (e.g., table headers)
    # QScrollBar: Styling for scrollbars
    # QStatusBar: Styling for the status bar
    # QTabWidget, QTabBar: Styling for tabbed interfaces
    # QGroupBox: Styling for group boxes
    dark_stylesheet = """
        QWidget {
            background-color: #2e2e2e; /* Slightly different base */
            color: #e0e0e0; /* Brighter text for better readability */
            border: none;
        }
        QMainWindow {
            background-color: #2e2e2e;
        }
        QMenuBar {
            background-color: #383838; /* Darker menubar */
            color: #e0e0e0;
        }
        QMenuBar::item {
            background-color: #383838;
            color: #e0e0e0;
            padding: 4px 8px; /* Add some padding */
        }
        QMenuBar::item::selected {
            background-color: #505050;
        }
        QMenu {
            background-color: #383838;
            color: #e0e0e0;
            border: 1px solid #505050;
        }
        QMenu::item::selected {
            background-color: #505050;
        }
        QToolBar {
            background-color: #383838;
            border: none;
        }
        QPushButton {
            background-color: #505050;
            color: #e0e0e0;
            border: 1px solid #606060;
            padding: 6px 12px; /* More padding */
            min-width: 70px;
            border-radius: 3px; /* Rounded corners */
        }
        QPushButton:hover {
            background-color: #606060;
        }
        QPushButton:pressed {
            background-color: #404040;
        }
        QDialog {
            background-color: #2e2e2e;
            border: 1px solid #505050; /* Dialog border */
        }
        QLabel {
            color: #e0e0e0;
        }
        QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox {
            background-color: #383838;
            color: #e0e0e0;
            border: 1px solid #505050;
            padding: 4px; /* More padding */
            border-radius: 3px;
        }
        QTreeView, QListView, QTableView {
            background-color: #383838;
            color: #e0e0e0;
            border: 1px solid #505050;
            gridline-color: #505050;
        }
        QHeaderView::section {
            background-color: #383838;
            color: #e0e0e0;
            padding: 5px; /* More padding */
            border: 1px solid #505050;
        }
        QScrollBar:vertical {
            background: #383838;
            width: 14px; /* Wider scrollbar */
            margin: 0px 0px 0px 0px;
            border: 1px solid #505050;
        }
        QScrollBar::handle:vertical {
            background: #505050;
            min-height: 25px; /* Taller handle */
            border-radius: 7px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        QScrollBar:horizontal {
            background: #383838;
            height: 14px;
            margin: 0px 0px 0px 0px;
            border: 1px solid #505050;
        }
        QScrollBar::handle:horizontal {
            background: #505050;
            min-width: 25px;
            border-radius: 7px;
        }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 0px;
        }
        QStatusBar {
            background-color: #383838;
            color: #e0e0e0;
        }
        QTabWidget::pane {
            border: 1px solid #505050; /* Border around tab content */
        }
        QTabBar::tab {
            background: #383838;
            color: #e0e0e0;
            padding: 8px 15px; /* More padding for tabs */
            border: 1px solid #505050;
            border-bottom: none;
            border-top-left-radius: 4px; /* Rounded top corners */
            border-top-right-radius: 4px;
        }
        QTabBar::tab:selected, QTabBar::tab:hover {
            background: #505050;
        }
        QTabBar::tab:!selected {
            margin-top: 2px;
        }
        QGroupBox {
            border: 1px solid #505050;
            margin-top: 10px; /* Space for title */
            padding: 10px;
            border-radius: 3px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left; /* position at the top left */
            padding: 0 5px 0 5px;
            background-color: #2e2e2e; /* Make title background same as main widget */
            color: #e0e0e0;
        }
    """
    app.setStyleSheet(dark_stylesheet)

    # Initialize and show the main window
    main_window = MainWindow()
    main_window.show()

    logger.info("Application event loop started.")
    exit_code = app.exec()
    logger.info(f"Application exited with code {exit_code}.")
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
