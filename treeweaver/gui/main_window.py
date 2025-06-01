# This module will define the main application window and its layout.
import sys
import logging
import os
import tempfile
import functools # For partial function application

from PyQt6.QtWidgets import (
    QMainWindow, QApplication, QMenuBar, QMenu, QWidget, QLabel,
    QFileDialog, QMessageBox, QStatusBar
)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt

# Import GUI components
from .dialogs import SettingsDialog, RaxmlDialog # Added RaxmlDialog
from .sequence_panel import SequencePanel

# Import core functionalities
from treeweaver.core import (
    load_sequences, write_fasta, write_phylip, write_newick,
    write_sequences, SequenceData, parse_newick
)
from treeweaver.core.phylogenetics import create_phylip_with_internal_ids, map_raxml_tree_tips_to_original_ids
from treeweaver.utils import run_mafft, run_iqtree, run_modeltest_ng, run_raxml_ng # Added run_raxml_ng
from treeweaver.config import settings_manager

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    """Main application window for TreeWeaver."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("TreeWeaver v0.1")
        self.setGeometry(100, 100, 1200, 800)

        self.sequence_data: SequenceData | None = None
        self.tree_data = None
        self.best_fit_model: str | None = None

        self._createMenuBar()
        self._setupDockWidgets()
        self._setupStatusBar()

        placeholder_widget = QLabel("Tree Visualization Area")
        placeholder_widget.setStyleSheet(
            "QLabel { color: #cccccc; font-size: 16pt; qproperty-alignment: 'AlignCenter'; border: 1px dashed #555555; }"
        )
        self.setCentralWidget(placeholder_widget)

        logger.info("MainWindow initialized.")

    def _setupDockWidgets(self):
        self.sequence_panel = SequencePanel("Loaded Sequences", self)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.sequence_panel)

    def _setupStatusBar(self):
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.model_display_label = QLabel("Best-fit model: None")
        self.statusBar.addPermanentWidget(self.model_display_label)
        self.statusBar.showMessage("Ready", 3000)

    def _createMenuBar(self):
        menu_bar = QMenuBar(self)
        file_menu = menu_bar.addMenu("&File")
        # ... (File menu actions as before) ...
        import_seq_action = QAction("Import Sequences...", self)
        import_seq_action.setToolTip("Import sequences from FASTA, PHYLIP, FASTQ, or NEXUS files.")
        import_seq_action.triggered.connect(self._import_sequences)
        file_menu.addAction(import_seq_action)
        open_tree_action = QAction("Import Tree...", self)
        open_tree_action.setToolTip("Import a phylogenetic tree from a Newick or Nexus file.")
        # open_tree_action.triggered.connect(self._import_tree) # TODO
        file_menu.addAction(open_tree_action)
        file_menu.addSeparator()
        export_alignment_action = QAction("Export Alignment...", self)
        export_alignment_action.setToolTip("Export loaded sequences/alignment to a file.")
        export_alignment_action.triggered.connect(self._export_alignment)
        file_menu.addAction(export_alignment_action)
        export_tree_action = QAction("Export Tree...", self)
        export_tree_action.setToolTip("Export the current tree to a file (e.g., Newick).")
        export_tree_action.triggered.connect(self._export_tree)
        file_menu.addAction(export_tree_action)
        file_menu.addSeparator()
        settings_action = QAction("Settings...", self)
        settings_action.setToolTip("Configure application settings and external tool paths.")
        settings_action.triggered.connect(self._open_settings_dialog)
        file_menu.addAction(settings_action)
        file_menu.addSeparator()
        exit_action = QAction("Exit", self)
        exit_action.setToolTip("Exit the application.")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        edit_menu = menu_bar.addMenu("&Edit")
        # ... (Edit menu actions as before) ...
        undo_action = QAction("Undo", self)
        undo_action.setToolTip("Undo the last action (Not implemented).")
        edit_menu.addAction(undo_action)
        redo_action = QAction("Redo", self)
        redo_action.setToolTip("Redo the last undone action (Not implemented).")
        edit_menu.addAction(redo_action)

        view_menu = menu_bar.addMenu("&View")
        # ... (View menu actions as before) ...
        toggle_seq_panel_action = self.sequence_panel.toggleViewAction()
        toggle_seq_panel_action.setText("Toggle Sequence Panel")
        toggle_seq_panel_action.setToolTip("Show or hide the Loaded Sequences panel.")
        view_menu.addAction(toggle_seq_panel_action)

        tools_menu = menu_bar.addMenu("&Tools")
        run_mafft_action = QAction("Run MAFFT (Align Sequences)...", self)
        run_mafft_action.setToolTip("Align loaded sequences using MAFFT.")
        run_mafft_action.triggered.connect(self._run_mafft_alignment)
        tools_menu.addAction(run_mafft_action)
        tools_menu.addSeparator()
        run_iqtree_mf_action = QAction("Run IQ-TREE (ModelFinder)...", self)
        run_iqtree_mf_action.setToolTip("Find best-fit model using IQ-TREE's ModelFinder.")
        run_iqtree_mf_action.triggered.connect(functools.partial(self._run_model_selection, "iqtree"))
        tools_menu.addAction(run_iqtree_mf_action)
        run_modeltest_ng_action = QAction("Run ModelTest-NG...", self)
        run_modeltest_ng_action.setToolTip("Find best-fit model using ModelTest-NG.")
        run_modeltest_ng_action.triggered.connect(functools.partial(self._run_model_selection, "modeltestng"))
        tools_menu.addAction(run_modeltest_ng_action)
        tools_menu.addSeparator()
        # "Run IQ-TREE (Build Tree)..." action was here, now replaced/complemented by RAxML-NG
        run_raxml_ng_action = QAction("Run RAxML-NG (Tree Inference)...", self)
        run_raxml_ng_action.setToolTip("Infer phylogenetic tree using RAxML-NG.")
        run_raxml_ng_action.triggered.connect(self._run_raxml_ng_tree_inference)
        tools_menu.addAction(run_raxml_ng_action)

        help_menu = menu_bar.addMenu("&Help")
        # ... (Help menu actions as before) ...
        about_action = QAction("About TreeWeaver", self)
        about_action.setToolTip("Show information about TreeWeaver.")
        # about_action.triggered.connect(self._show_about_dialog) # TODO
        help_menu.addAction(about_action)

        self.setMenuBar(menu_bar)

    def _open_settings_dialog(self):
        logger.debug("Opening Settings dialog.")
        dialog = SettingsDialog(self)
        dialog.exec()

    def _import_sequences(self):
        file_types = "FASTA (*.fasta *.fa *.fna *.ffn *.faa *.frn);;PHYLIP (*.phy *.phylip);;FASTQ (*.fastq *.fq);;NEXUS (*.nex *.nexus);;All Files (*)"
        last_dir = settings_manager.get_setting("user_paths.last_import_dir", os.path.expanduser("~"))
        filepath, _ = QFileDialog.getOpenFileName(self, "Import Sequences", last_dir, file_types)
        if filepath:
            settings_manager.update_setting("user_paths.last_import_dir", os.path.dirname(filepath))
            logger.info(f"Attempting to load sequences from: {filepath}")
            loaded_data = load_sequences(filepath)
            if loaded_data and len(loaded_data.get_all_sequences()) > 0:
                self.sequence_data = loaded_data; self.tree_data = None # Clear old tree
                self.sequence_panel.update_sequences(self.sequence_data)
                QMessageBox.information(self, "Import Success", f"Loaded {len(self.sequence_data.get_all_sequences())} sequences.")
            elif loaded_data:
                QMessageBox.warning(self, "Import Issue", f"No sequences found in {os.path.basename(filepath)}.")
                self.sequence_data = None; self.tree_data = None; self.sequence_panel.clear_sequences()
            else:
                QMessageBox.critical(self, "Import Error", f"Could not load sequences from {os.path.basename(filepath)}.")
                self.sequence_data = None; self.tree_data = None; self.sequence_panel.clear_sequences()
        else: logger.info("Sequence import cancelled.")

    def _export_alignment(self):
        if not self.sequence_data or len(self.sequence_data.get_all_sequences()) == 0:
            QMessageBox.warning(self, "Export Error", "No sequences loaded to export."); return
        # ... (export alignment logic as before)
        file_types = "FASTA (*.fasta);;PHYLIP (*.phy);;NEXUS (*.nex *.nexus);;All Files (*)"
        last_dir = settings_manager.get_setting("user_paths.last_export_dir", os.path.expanduser("~"))
        default_filename = os.path.join(last_dir, "exported_alignment.fasta")
        filepath, selected_filter = QFileDialog.getSaveFileName(self, "Export Alignment", default_filename, file_types)
        if filepath:
            settings_manager.update_setting("user_paths.last_export_dir", os.path.dirname(filepath))
            fmt = "fasta"
            if "(*.fasta)" in selected_filter: fmt = "fasta"
            elif "(*.phy)" in selected_filter: fmt = "phylip"
            elif "(*.nex" in selected_filter or "*.nexus" in selected_filter: fmt = "nexus"
            success = write_sequences(self.sequence_data, filepath, fmt)
            if success: QMessageBox.information(self, "Export Success", f"Alignment exported to {os.path.basename(filepath)}.")
            else: QMessageBox.critical(self, "Export Error", f"Failed to export alignment to {os.path.basename(filepath)}.")
        else: logger.info("Alignment export cancelled.")


    def _export_tree(self):
        if not self.tree_data:
            QMessageBox.warning(self, "Export Error", "No tree loaded/generated to export."); return
        # ... (export tree logic as before)
        file_types = "Newick (*.nwk *.newick *.tre *.tree);;All Files (*)"
        last_dir = settings_manager.get_setting("user_paths.last_export_dir", os.path.expanduser("~"))
        default_filename = os.path.join(last_dir, "exported_tree.nwk")
        filepath, _ = QFileDialog.getSaveFileName(self, "Export Tree", default_filename, file_types)
        if filepath:
            settings_manager.update_setting("user_paths.last_export_dir", os.path.dirname(filepath))
            success = write_newick(self.tree_data, filepath)
            if success: QMessageBox.information(self, "Export Success", f"Tree exported to {os.path.basename(filepath)}.")
            else: QMessageBox.critical(self, "Export Error", f"Failed to export tree to {os.path.basename(filepath)}.")
        else: logger.info("Tree export cancelled.")


    def _run_mafft_alignment(self):
        if not self.sequence_data or len(self.sequence_data.get_all_sequences()) == 0:
            QMessageBox.warning(self, "MAFFT Error", "No sequences loaded to align."); return
        try:
            num_threads = int(settings_manager.get_setting("external_tool_options.mafft_threads", 1))
            if num_threads <= 0: num_threads = 1
        except ValueError: num_threads = 1; logger.warning("Invalid mafft_threads, defaulting to 1.")

        logger.info(f"Preparing MAFFT with {num_threads} threads.")
        with tempfile.TemporaryDirectory(prefix="tw_mafft_") as tmpdir:
            input_fp = os.path.join(tmpdir, "input.fasta")
            output_fp = os.path.join(tmpdir, "aligned.fasta")
            if not write_fasta(self.sequence_data, input_fp):
                QMessageBox.critical(self, "MAFFT Error", "Failed to write input for MAFFT."); return
            wait_msg = QMessageBox(QMessageBox.Icon.Information, "Processing...", "Running MAFFT. Please wait.", QMessageBox.StandardButton.NoButton, self)
            wait_msg.setModal(True); wait_msg.show(); QApplication.processEvents()
            success = run_mafft(input_fp, output_fp, num_threads=num_threads)
            wait_msg.close()
            if success and os.path.exists(output_fp):
                aligned_data = load_sequences(output_fp, file_format="fasta")
                if aligned_data and len(aligned_data.get_all_sequences()) > 0:
                    self.sequence_data = aligned_data; self.tree_data = None # Alignment changed, clear old tree
                    self.sequence_panel.update_sequences(self.sequence_data)
                    QMessageBox.information(self, "MAFFT Success", "Alignment complete.")
                else: QMessageBox.critical(self, "MAFFT Error", "Failed to load aligned sequences.")
            else: QMessageBox.critical(self, "MAFFT Error", "MAFFT failed. Check logs/settings.")

    def _run_model_selection(self, tool_name: str):
        if not self.sequence_data or len(self.sequence_data.get_all_sequences()) == 0:
            QMessageBox.warning(self, "Model Selection Error", "No sequences loaded for model selection."); return

        tool_key_map = {"iqtree": "iqtree", "modeltestng": "modeltest-ng"}
        tool_setting_key = tool_key_map[tool_name]
        threads_setting_key = f"external_tool_options.{tool_setting_key}_threads"
        try:
            num_threads = int(settings_manager.get_setting(threads_setting_key, 1))
            if num_threads <= 0: num_threads = 1
        except ValueError: num_threads = 1; logger.warning(f"Invalid {threads_setting_key}, defaulting to 1.")

        logger.info(f"Preparing for {tool_name} model selection with {num_threads} threads.")
        with tempfile.TemporaryDirectory(prefix=f"tw_{tool_name}_") as tmpdir:
            input_phylip_path = os.path.join(tmpdir, "input.phy")
            if not write_phylip(self.sequence_data, input_phylip_path): # Use core.write_phylip
                QMessageBox.critical(self, f"{tool_name} Error", f"Failed to write PHYLIP input for {tool_name}."); return
            output_prefix = os.path.join(tmpdir, f"{tool_name}_run")
            wait_msg = QMessageBox(QMessageBox.Icon.Information, "Processing...", f"Running {tool_name} model selection...", QMessageBox.StandardButton.NoButton, self)
            wait_msg.setModal(True); wait_msg.show(); QApplication.processEvents()
            success, model_result = False, None
            if tool_name == "iqtree":
                success, model_result = run_iqtree(alignment_path=input_phylip_path, prefix=output_prefix, threads=num_threads, run_model_finder_only=True)
            elif tool_name == "modeltestng":
                success, model_result = run_modeltest_ng(alignment_phylip_path=input_phylip_path, output_base_name=output_prefix, threads=num_threads, sequence_type="DNA") # Assuming DNA
            wait_msg.close()
            if success and model_result:
                if os.path.exists(model_result):
                    QMessageBox.warning(self, f"{tool_name} Info", f"{tool_name} ran, but model parsing failed. Report: {model_result}")
                    self.best_fit_model = None; self.model_display_label.setText("Best-fit model: Parsing failed")
                else:
                    self.best_fit_model = model_result
                    self.model_display_label.setText(f"Best-fit model: {self.best_fit_model}")
                    QMessageBox.information(self, f"{tool_name} Success", f"Model selection complete.\nBest model: {self.best_fit_model}")
            else:
                QMessageBox.critical(self, f"{tool_name} Error", f"{tool_name} failed. Check logs/config.")
                self.best_fit_model = None; self.model_display_label.setText("Best-fit model: Failed")

    def _run_raxml_ng_tree_inference(self):
        if not self.sequence_data or len(self.sequence_data.get_all_sequences()) == 0:
            QMessageBox.warning(self, "RAxML-NG Error", "No (aligned) sequences loaded for tree inference."); return

        current_model = self.best_fit_model if self.best_fit_model else "GTR+G" # Default if no model selected
        dialog = RaxmlDialog(current_model=current_model, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            params = dialog.get_parameters()
            model = params['model']
            bootstraps = params['bootstraps']
            prefix_base = params['prefix'] # This is just a name, not a path yet
            threads = params['threads']

            if not model:
                QMessageBox.critical(self, "RAxML-NG Error", "Substitution model cannot be empty."); return

            logger.info(f"Preparing RAxML-NG: Model={model}, BS={bootstraps}, PrefixBase={prefix_base}, Threads={threads}")

            with tempfile.TemporaryDirectory(prefix="tw_raxml_") as tmpdir:
                temp_phylip_path = os.path.join(tmpdir, "raxml_input.phy")
                # Use the new core function to write PHYLIP with internal IDs
                if not create_phylip_with_internal_ids(self.sequence_data, temp_phylip_path):
                    QMessageBox.critical(self, "RAxML-NG Error", "Failed to create PHYLIP input with internal IDs."); return

                # Define prefix for RAxML-NG output files *inside* the temp directory
                raxml_output_prefix = os.path.join(tmpdir, prefix_base)

                wait_msg = QMessageBox(QMessageBox.Icon.Information, "Processing...", "Running RAxML-NG tree inference...", QMessageBox.StandardButton.NoButton, self)
                wait_msg.setModal(True); wait_msg.show(); QApplication.processEvents()

                success, result_file = run_raxml_ng(
                    alignment_phylip_path=temp_phylip_path,
                    model=model,
                    prefix=raxml_output_prefix, # run_raxml_ng expects this to be a name it can append suffixes to
                    seed=12345, # Consider making seed configurable or random with logging
                    threads=threads,
                    bootstrap_replicates=bootstraps,
                    working_dir=tmpdir # Explicitly tell RAxML-NG where to run
                )
                wait_msg.close()

                if success and result_file and os.path.exists(result_file):
                    logger.info(f"RAxML-NG completed. Tree file generated: {result_file}")
                    raw_tree = parse_newick(result_file) # Use core.parse_newick
                    if raw_tree:
                        self.tree_data = map_raxml_tree_tips_to_original_ids(raw_tree, self.sequence_data)
                        QMessageBox.information(self, "RAxML-NG Success", "Tree inference completed successfully.")
                        logger.info("Tree ready for visualization (placeholder).")
                        # Here, you would trigger tree visualization update
                    else:
                        QMessageBox.critical(self, "RAxML-NG Error", f"Failed to parse output tree file: {result_file}")
                else:
                    QMessageBox.critical(self, "RAxML-NG Error", "RAxML-NG failed or output tree not found. Check logs.")
        else:
            logger.info("RAxML-NG parameter dialog cancelled.")


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    app = QApplication(sys.argv)
    dark_stylesheet_main = """
        QWidget { background-color: #2e2e2e; color: #e0e0e0; border: none; } QMainWindow { background-color: #2e2e2e; }
        QMenuBar { background-color: #383838; color: #e0e0e0; } QMenuBar::item { background-color: #383838; color: #e0e0e0; padding: 4px 8px; }
        QMenuBar::item::selected { background-color: #505050; } QMenu { background-color: #383838; color: #e0e0e0; border: 1px solid #505050; }
        QMenu::item::selected { background-color: #505050; } QPushButton { background-color: #505050; color: #e0e0e0; border: 1px solid #606060; padding: 6px 12px; border-radius: 3px; }
        QPushButton:hover { background-color: #606060; } QPushButton:pressed { background-color: #404040; } QDialog { background-color: #2e2e2e; border: 1px solid #505050; }
        QLabel { color: #e0e0e0; } QLineEdit { background-color: #383838; color: #e0e0e0; border: 1px solid #505050; padding: 4px; border-radius: 3px; }
        QDockWidget::title { background-color: #383838; padding: 5px; border: 1px solid #2e2e2e; text-align: center; }
        QListWidget { background-color: #383838; color: #e0e0e0; border: 1px solid #505050; padding: 5px; } QListWidget::item { padding: 5px; } QListWidget::item:selected { background-color: #505050; }
        QStatusBar { background-color: #383838; color: #e0e0e0; } QStatusBar QLabel { padding: 0 5px; }
    """
    app.setStyleSheet(dark_stylesheet_main)
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())
