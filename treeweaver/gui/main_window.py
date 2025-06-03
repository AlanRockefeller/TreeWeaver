# This module will define the main application window and its layout.
import sys
import logging
import os 
import tempfile 
import functools 
from pathlib import Path # For path operations

from PyQt6.QtWidgets import (
    QMainWindow, QApplication, QMenuBar, QMenu, QWidget, QLabel, 
    QFileDialog, QMessageBox, QStatusBar, QDialog # For dialog.exec comparison
)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt

from .dialogs import SettingsDialog, RaxmlDialog, SequenceEditDialog, HelpDialog
from .sequence_panel import SequencePanel
from .tree_canvas import TreeCanvas 

from treeweaver.core import (
    load_sequences, write_fasta, write_phylip, write_newick, 
    write_sequences, SequenceData, parse_newick
)
from treeweaver.core.phylogenetics import create_phylip_with_internal_ids, map_raxml_tree_tips_to_original_ids
from treeweaver.utils import run_mafft, run_iqtree, run_modeltest_ng, run_raxml_ng
from treeweaver.config import settings_manager

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("TreeWeaver v0.1")
        self.setGeometry(100, 100, 1200, 800)

        self.sequence_data: SequenceData | None = None
        self.tree_data = None 
        self.best_fit_model: str | None = None 
        self.deletion_mode_active = False 

        self._createMenuBar()
        self._setupDockWidgets()
        self._setupStatusBar() 

        self.tree_canvas = TreeCanvas(self)
        self.setCentralWidget(self.tree_canvas)
        logger.info("TreeCanvas set as central widget.")
        logger.info("MainWindow initialized.")

    def _setupDockWidgets(self):
        self.sequence_panel = SequencePanel("Loaded Sequences", self)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.sequence_panel)
        self.sequence_panel.edit_sequence_requested.connect(self._handle_edit_sequence_request)
        if hasattr(self, 'tree_canvas') and self.tree_canvas is not None:
             self.tree_canvas.delete_clade_requested.connect(self._handle_delete_clade_request)

    def _setupStatusBar(self):
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.model_display_label = QLabel("Best-fit model: None")
        self.statusBar.addPermanentWidget(self.model_display_label)
        self.statusBar.showMessage("Ready", 3000)

    def _createMenuBar(self):
        menu_bar = QMenuBar(self)
        # File Menu
        file_menu = menu_bar.addMenu("&File")
        import_seq_action = QAction("Import Sequences...", self)
        import_seq_action.setToolTip("Import sequences from FASTA, PHYLIP, FASTQ, or NEXUS files.")
        import_seq_action.triggered.connect(self._import_sequences)
        file_menu.addAction(import_seq_action)
        file_menu.addSeparator()
        export_menu = file_menu.addMenu("Export")
        self.export_alignment_action = QAction("Export Alignment...", self)
        self.export_alignment_action.setToolTip("Export loaded sequences/alignment to various formats.")
        self.export_alignment_action.triggered.connect(self._export_alignment)
        export_menu.addAction(self.export_alignment_action)
        self.export_newick_action = QAction("Export Tree (Newick)...", self)
        self.export_newick_action.setToolTip("Export the current tree in Newick format.")
        self.export_newick_action.triggered.connect(self._export_tree_newick)
        export_menu.addAction(self.export_newick_action)
        self.export_tree_image_action = QAction("Export Tree as Image...", self)
        self.export_tree_image_action.setToolTip("Export the displayed tree as PNG, SVG, JPG, or PDF.")
        self.export_tree_image_action.triggered.connect(self._export_tree_image)
        export_menu.addAction(self.export_tree_image_action)
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

        # Edit Menu
        edit_menu = menu_bar.addMenu("&Edit")
        undo_action = QAction("Undo", self); undo_action.setToolTip("Undo the last action (Not implemented).")
        edit_menu.addAction(undo_action)
        redo_action = QAction("Redo", self); redo_action.setToolTip("Redo the last undone action (Not implemented).")
        edit_menu.addAction(redo_action)
        edit_menu.addSeparator()
        self.deletion_mode_action = QAction("Enable Deletion Mode", self, checkable=True)
        self.deletion_mode_action.setToolTip("Toggle deletion mode for tree nodes/sequences.")
        self.deletion_mode_action.triggered.connect(self._toggle_deletion_mode)
        edit_menu.addAction(self.deletion_mode_action)

        # View Menu
        view_menu = menu_bar.addMenu("&View")
        toggle_seq_panel_action = self.sequence_panel.toggleViewAction()
        toggle_seq_panel_action.setText("Toggle Sequence Panel")
        toggle_seq_panel_action.setToolTip("Show or hide the Loaded Sequences panel.")
        view_menu.addAction(toggle_seq_panel_action)

        # Tools Menu
        tools_menu = menu_bar.addMenu("&Tools")
        run_mafft_action = QAction("Run MAFFT...", self); run_mafft_action.setToolTip("Align loaded sequences using MAFFT.")
        run_mafft_action.triggered.connect(self._run_mafft_alignment); tools_menu.addAction(run_mafft_action)
        tools_menu.addSeparator()
        run_iqtree_mf_action = QAction("Run IQ-TREE (ModelFinder)...", self); run_iqtree_mf_action.setToolTip("Find best-fit model using IQ-TREE.")
        run_iqtree_mf_action.triggered.connect(functools.partial(self._run_model_selection, "iqtree")); tools_menu.addAction(run_iqtree_mf_action)
        run_modeltest_ng_action = QAction("Run ModelTest-NG...", self); run_modeltest_ng_action.setToolTip("Find best-fit model using ModelTest-NG.")
        run_modeltest_ng_action.triggered.connect(functools.partial(self._run_model_selection, "modeltestng")); tools_menu.addAction(run_modeltest_ng_action)
        tools_menu.addSeparator()
        run_raxml_ng_action = QAction("Run RAxML-NG (Tree Inference)...", self); run_raxml_ng_action.setToolTip("Infer tree using RAxML-NG.")
        run_raxml_ng_action.triggered.connect(self._run_raxml_ng_tree_inference); tools_menu.addAction(run_raxml_ng_action)
        
        # Help Menu
        help_menu = menu_bar.addMenu("&Help")
        help_content_action = QAction("Help Content...", self)
        help_content_action.setToolTip("Show detailed help documentation.")
        help_content_action.triggered.connect(self._show_help_dialog)
        help_menu.addAction(help_content_action)
        help_menu.addSeparator()
        about_action = QAction("About TreeWeaver", self)
        about_action.setToolTip("Show information about TreeWeaver.")
        # about_action.triggered.connect(self._show_about_dialog) # TODO: Implement this
        help_menu.addAction(about_action)
        self.setMenuBar(menu_bar)

    def _show_help_dialog(self):
        logger.debug("Showing Help dialog.")
        dialog = HelpDialog(self)
        dialog.exec()

    def _open_settings_dialog(self):
        logger.debug("Opening Settings dialog.")
        dialog = SettingsDialog(self) 
        if dialog.exec() == QDialog.DialogCode.Accepted: # Use QDialog.DialogCode.Accepted
            logger.info("Settings dialog accepted.")
            if self.tree_data and self.tree_canvas:
                logger.info("Redrawing tree with new visualization settings.")
                self.tree_canvas.draw_tree(self.tree_data)
        else: logger.info("Settings dialog cancelled.")

    def _import_sequences(self):
        file_types = "FASTA (*.fasta *.fa *.fna *.ffn *.faa *.frn);;PHYLIP (*.phy *.phylip);;FASTQ (*.fastq *.fq);;NEXUS (*.nex *.nexus);;All Files (*)"
        last_dir = settings_manager.get_setting("user_paths.last_import_dir", str(Path.home()))
        filepath, _ = QFileDialog.getOpenFileName(self, "Import Sequences", last_dir, file_types)
        if filepath:
            settings_manager.update_setting("user_paths.last_import_dir", str(Path(filepath).parent))
            # Use try-except for file loading robustness
            try:
                loaded_data = load_sequences(filepath) 
                if loaded_data and len(loaded_data.get_all_sequences()) > 0:
                    self.sequence_data = loaded_data; self.tree_data = None; self.best_fit_model = None
                    self.model_display_label.setText("Best-fit model: None")
                    self.tree_canvas.clear_tree(); self.sequence_panel.update_sequences(self.sequence_data)
                    QMessageBox.information(self, "Import Success", f"Loaded {len(self.sequence_data.get_all_sequences())} sequences.")
                elif loaded_data: QMessageBox.warning(self, "Import Issue", f"No sequences found in {os.path.basename(filepath)}.")
                else: QMessageBox.critical(self, "Import Error", f"Could not load sequences from {os.path.basename(filepath)} (file might be empty or wrong format).")
            except Exception as e:
                logger.error(f"Error during sequence import from {filepath}: {e}", exc_info=True)
                QMessageBox.critical(self, "Import Error", f"An unexpected error occurred while loading {os.path.basename(filepath)}: {e}")
        else: logger.info("Sequence import cancelled.")

    def _export_alignment(self):
        if not self.sequence_data or len(self.sequence_data.get_all_sequences()) == 0:
            QMessageBox.warning(self, "Export Error", "No sequences loaded to export."); return
        file_types = "FASTA (*.fasta *.fa);;PHYLIP (*.phy *.phylip);;NEXUS (*.nex *.nexus);;All Files (*)"
        last_dir = settings_manager.get_setting("user_paths.last_export_dir", str(Path.home()))
        default_filename = os.path.join(last_dir, "exported_alignment.fasta")
        filepath, selected_filter = QFileDialog.getSaveFileName(self, "Export Alignment", default_filename, file_types)
        if filepath:
            settings_manager.update_setting("user_paths.last_export_dir", str(Path(filepath).parent))
            fmt = "fasta" 
            if "fasta" in selected_filter.lower(): fmt = "fasta"
            elif "phylip" in selected_filter.lower(): fmt = "phylip"
            elif "nexus" in selected_filter.lower(): fmt = "nexus"
            elif Path(filepath).suffix.lower() in [".phy", ".phylip"]: fmt = "phylip"
            elif Path(filepath).suffix.lower() in [".nex", ".nexus"]: fmt = "nexus"
            try:
                if write_sequences(self.sequence_data, filepath, fmt): # type: ignore
                    QMessageBox.information(self, "Export Success", f"Alignment exported to {os.path.basename(filepath)}.")
                else: QMessageBox.critical(self, "Export Error", f"Failed to export alignment to {os.path.basename(filepath)} (writer function returned false).")
            except Exception as e:
                logger.error(f"Error exporting alignment to {filepath}: {e}", exc_info=True)
                QMessageBox.critical(self, "Export Error", f"Failed to export alignment: {e}")
        else: logger.info("Alignment export cancelled.")

    def _export_tree_newick(self): 
        if not self.tree_data: QMessageBox.warning(self, "Export Error", "No tree to export."); return
        file_types = "Newick (*.nwk *.newick *.tre *.tree);;All Files (*)"
        last_dir = settings_manager.get_setting("user_paths.last_export_dir", str(Path.home()))
        default_filename = os.path.join(last_dir, "exported_tree.nwk")
        filepath, _ = QFileDialog.getSaveFileName(self, "Export Tree as Newick", default_filename, file_types)
        if filepath:
            settings_manager.update_setting("user_paths.last_export_dir", str(Path(filepath).parent))
            try:
                if write_newick(self.tree_data, filepath): 
                    QMessageBox.information(self, "Export Success", f"Tree exported to {os.path.basename(filepath)}.")
                else: QMessageBox.critical(self, "Export Error", f"Failed to export tree to {os.path.basename(filepath)} (writer function returned false).")
            except Exception as e:
                logger.error(f"Error exporting Newick tree to {filepath}: {e}", exc_info=True)
                QMessageBox.critical(self, "Export Error", f"Failed to export tree: {e}")
        else: logger.info("Newick tree export cancelled.")

    def _export_tree_image(self):
        if not self.tree_data or not self.tree_canvas or not self.tree_canvas.figure:
            QMessageBox.warning(self, "Export Error", "No tree displayed to export as image."); return
        file_filters = "PNG Image (*.png);;SVG Image (*.svg);;JPEG Image (*.jpg *.jpeg);;PDF Document (*.pdf);;All Files (*)"
        last_dir = settings_manager.get_setting("user_paths.last_export_dir", str(Path.home()))
        default_filename = os.path.join(last_dir, "tree_image.png")
        filepath, selected_filter = QFileDialog.getSaveFileName(self, "Export Tree as Image", default_filename, file_filters)
        if filepath:
            final_filepath = Path(filepath)
            if selected_filter == "All Files (*)" and not final_filepath.suffix:
                final_filepath = final_filepath.with_suffix(".png"); logger.info("Defaulting to .png for image export.")
            try:
                self.tree_canvas.figure.savefig(str(final_filepath), dpi=300, bbox_inches='tight')
                settings_manager.update_setting("user_paths.last_export_dir", str(final_filepath.parent))
                QMessageBox.information(self, "Export Successful", f"Tree image saved to {final_filepath.name}")
            except Exception as e:
                self.logger.error(f"Error exporting tree image: {e}", exc_info=True)
                QMessageBox.critical(self, "Export Error", f"Could not save tree image: {e}")
        else: logger.info("Tree image export cancelled.")

    def _run_mafft_alignment(self):
        if not self.sequence_data: QMessageBox.warning(self,"MAFFT Error","No sequences loaded."); return
        try: num_threads = int(settings_manager.get_setting("external_tool_options.mafft_threads",1))
        except ValueError: num_threads=1
        with tempfile.TemporaryDirectory(prefix="tw_mafft_") as tmpdir:
            input_fp=os.path.join(tmpdir,"in.fas"); output_fp=os.path.join(tmpdir,"out.fas")
            if not write_fasta(self.sequence_data,input_fp): QMessageBox.critical(self,"MAFFT Error","Failed to prepare input for MAFFT."); return
            wait_msg=QMessageBox(QMessageBox.Icon.Information,"Processing","Running MAFFT alignment...",QMessageBox.StandardButton.NoButton,self); wait_msg.setModal(True); wait_msg.show(); QApplication.processEvents()
            success, error_message = run_mafft(input_fp,output_fp,num_threads)
            wait_msg.close()
            if success:
                aligned_data = load_sequences(output_fp,"fasta") # Assuming load_sequences handles its own errors and returns None
                if aligned_data and len(aligned_data.get_all_sequences()) > 0:
                    self.sequence_data=aligned_data; self.tree_data=None; self.best_fit_model=None
                    self.model_display_label.setText("Best-fit model: None (Data changed)")
                    self.tree_canvas.clear_tree(); self.sequence_panel.update_sequences(self.sequence_data)
                    QMessageBox.information(self,"MAFFT Success","Alignment complete.")
                else: QMessageBox.critical(self,"MAFFT Error","MAFFT ran, but failed to load or parse aligned sequences.")
            else: QMessageBox.critical(self,"MAFFT Error", f"MAFFT alignment failed: {error_message if error_message else 'Unknown error'}")

    def _run_model_selection(self, tool_name: str):
        if not self.sequence_data: QMessageBox.warning(self,f"{tool_name} Error","No sequences loaded."); return
        tool_key = "iqtree" if tool_name == "iqtree" else "modeltest-ng"
        threads_key = f"external_tool_options.{tool_key}_threads"
        try: num_threads = int(settings_manager.get_setting(threads_key,1))
        except ValueError: num_threads=1
        with tempfile.TemporaryDirectory(prefix=f"tw_{tool_name}_") as tmpdir:
            input_phy=os.path.join(tmpdir,"in.phy")
            if not write_phylip(self.sequence_data,input_phy): QMessageBox.critical(self,f"{tool_name} Error","Failed to prepare input PHYLIP file."); return
            prefix=os.path.join(tmpdir,f"{tool_name}_run")
            wait_msg=QMessageBox(QMessageBox.Icon.Information,"Processing",f"Running {tool_name} model selection...",QMessageBox.StandardButton.NoButton,self); wait_msg.setModal(True); wait_msg.show(); QApplication.processEvents()
            success, result_or_error = False, None
            if tool_name == "iqtree": success, result_or_error = run_iqtree(input_phy,prefix,threads=num_threads,run_model_finder_only=True)
            else: success, result_or_error = run_modeltest_ng(input_phy,prefix,threads=num_threads,sequence_type="DNA")
            wait_msg.close()
            if success:
                self.best_fit_model = result_or_error # This is the model string
                QMessageBox.information(self,f"{tool_name} Success",f"Model selection complete.\nBest model: {self.best_fit_model}")
                self.model_display_label.setText(f"Best-fit model: {self.best_fit_model}")
            else: # Tool execution failed or parsing failed (result_or_error contains message)
                QMessageBox.critical(self,f"{tool_name} Error", str(result_or_error))
                self.best_fit_model=None
                self.model_display_label.setText("Best-fit model: Failed")

    def _run_raxml_ng_tree_inference(self):
        if not self.sequence_data: QMessageBox.warning(self,"RAxML-NG Error","No sequences loaded."); return
        model = self.best_fit_model or "GTR+G"
        dialog=RaxmlDialog(model,self)
        if dialog.exec()==QDialog.DialogCode.Accepted:
            params=dialog.get_parameters()
            with tempfile.TemporaryDirectory(prefix="tw_raxml_") as tmpdir:
                input_phy=os.path.join(tmpdir,"in.phy")
                if not create_phylip_with_internal_ids(self.sequence_data,input_phy): QMessageBox.critical(self,"RAxML-NG Error","Failed to prepare input PHYLIP."); return
                prefix_path=os.path.join(tmpdir,params['prefix'])
                wait_msg=QMessageBox(QMessageBox.Icon.Information,"Processing","Running RAxML-NG tree inference...",QMessageBox.StandardButton.NoButton,self); wait_msg.setModal(True); wait_msg.show(); QApplication.processEvents()
                success, result_or_error = run_raxml_ng(input_phy,params['model'],prefix_path,threads=params['threads'],bootstrap_replicates=params['bootstraps'],working_dir=tmpdir)
                wait_msg.close()
                if success and result_or_error and os.path.exists(result_or_error):
                    tree_file_path = result_or_error
                    raw_tree = parse_newick(tree_file_path)
                    if raw_tree: 
                        self.tree_data = map_raxml_tree_tips_to_original_ids(raw_tree,self.sequence_data)
                        QMessageBox.information(self,"RAxML-NG Success","Tree inference complete.")
                        self.tree_canvas.draw_tree(self.tree_data)
                    else: 
                        QMessageBox.critical(self,"RAxML-NG Error",f"Failed to parse output tree from {os.path.basename(tree_file_path)}."); self.tree_data=None
                        self.tree_canvas.clear_tree()
                else: 
                    error_msg = result_or_error if isinstance(result_or_error, str) else "RAxML-NG failed. Check logs."
                    QMessageBox.critical(self,"RAxML-NG Error", error_msg); self.tree_data=None
                    self.tree_canvas.clear_tree()
        else: logger.info("RAxML-NG dialog cancelled.")

    def _handle_edit_sequence_request(self, seq_id: str):
        if not self.sequence_data: return
        record = self.sequence_data.get_sequence_by_id(seq_id)
        if not record: QMessageBox.critical(self,"Edit Error",f"Seq ID '{seq_id}' not found."); return
        existing_ids = [s.id for s in self.sequence_data.get_all_sequences()]
        dialog = SequenceEditDialog(record.id, record.sequence, existing_ids, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_id, new_seq = dialog.get_validated_data()
            id_changed = record.id != new_id; seq_changed = record.sequence != new_seq
            updated = False; current_id_for_seq_update = record.id # Start with original ID
            if id_changed: 
                if self.sequence_data.update_sequence_id(record.id,new_id): 
                    current_id_for_seq_update = new_id 
                    updated = True
                else: QMessageBox.critical(self,"Error","Failed to update ID."); return 
            if seq_changed:
                if self.sequence_data.update_sequence_string(current_id_for_seq_update, new_seq): updated = True
                else: QMessageBox.critical(self,"Error","Failed to update sequence string."); return 
            if updated:
                self.sequence_panel.update_sequences(self.sequence_data)
                QMessageBox.information(self,"Sequence Updated",f"Sequence '{new_id}' updated.")
                self.tree_data=None; self.tree_canvas.clear_tree(); self.best_fit_model=None
                self.model_display_label.setText("Best-fit model: None (Data changed)")
        else: logger.info(f"Edit for '{seq_id}' cancelled.")
    
    def _toggle_deletion_mode(self, checked: bool):
        self.deletion_mode_active = checked
        status_message = f"Deletion Mode {'Activated' if checked else 'Deactivated'}"
        self.statusBar.showMessage(status_message, 3000); logger.info(status_message)
        self.deletion_mode_action.setText("Disable Deletion Mode" if checked else "Enable Deletion Mode")
        if self.tree_canvas: self.tree_canvas.set_deletion_mode(checked)

    def _handle_delete_clade_request(self, clade_name_to_delete: str, is_terminal: bool):
        if not self.tree_data or not self.sequence_data:
            QMessageBox.warning(self, "Deletion Error", "No data to delete from."); return
        target_clade = next(self.tree_data.find_clades(name=clade_name_to_delete), None)
        if not target_clade:
            QMessageBox.critical(self, "Deletion Error", f"Clade '{clade_name_to_delete}' not found."); return
        confirm_msg = f"Delete {'sequence' if is_terminal else 'clade'} '{clade_name_to_delete}'?" \
                      f"{'' if is_terminal else ' This will remove all descendant sequences.'}"
        if QMessageBox.question(self,"Confirm Deletion",confirm_msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.No:
            logger.info(f"Deletion of '{clade_name_to_delete}' cancelled."); return
        ids_to_remove = {tip.name for tip in (target_clade.get_terminals() if not is_terminal else [target_clade]) if tip.name}
        for seq_id in ids_to_remove: self.sequence_data.remove_sequence_by_id(seq_id)
        try: self.tree_data.prune(target_clade)
        except ValueError as e: 
             logger.error(f"Error pruning tree: {e}. Setting tree to None.")
             self.tree_data = None 
        self.sequence_panel.update_sequences(self.sequence_data)
        if self.tree_data and self.tree_data.root and self.tree_data.root.clades: 
            self.tree_canvas.draw_tree(self.tree_data)
        else:
            self.tree_canvas.clear_tree(); self.tree_data = None
            if len(self.sequence_data.get_all_sequences()) == 0: 
                 self.best_fit_model = None; self.model_display_label.setText("Best-fit model: None (Data cleared)")
        self.statusBar.showMessage(f"Deleted '{clade_name_to_delete}'. {len(ids_to_remove)} sequences removed.", 5000)

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    app = QApplication(sys.argv)
    dark_stylesheet_main = """ ... """ # Keep your existing stylesheet
    app.setStyleSheet(dark_stylesheet_main)
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())
