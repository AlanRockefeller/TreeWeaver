# This module will handle the rendering and interaction with the phylogenetic tree visualization.

import sys
import logging

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QMenu
from PyQt6.QtCore import Qt, pyqtSignal # Import pyqtSignal
from PyQt6.QtGui import QCursor # For changing cursor

try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
except ImportError:
    try:
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
        logging.warning("Using Matplotlib backend_qt5agg for PyQt6.")
    except ImportError:
        logging.critical("Matplotlib Qt backend (qtagg or qt5agg) not found. TreeCanvas will not work.")
        FigureCanvas = None

from matplotlib.figure import Figure
import matplotlib.lines
from Bio import Phylo
from Bio.Phylo.BaseTree import Clade
from typing import Optional

from treeweaver.config import settings_manager

logger = logging.getLogger(__name__)

class TreeCanvas(QWidget):
    """
    A QWidget that embeds a Matplotlib Figure for displaying phylogenetic trees,
    with interactive features like collapse/expand, re-rooting, and deletion.
    """
    delete_clade_requested = pyqtSignal(str, bool) # Emits (clade_name, is_terminal)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("TreeCanvasWidget")
        self.logger = logging.getLogger(__name__)

        if FigureCanvas is None:
            self.logger.critical("Matplotlib FigureCanvas could not be imported. Tree drawing is disabled.")
            error_label = QLabel("Error: Matplotlib Qt backend not found.\nTree visualization is disabled.", self)
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            error_label.setStyleSheet("QLabel { color: red; font-size: 14pt; }")
            layout = QVBoxLayout(self)
            layout.addWidget(error_label)
            self.setLayout(layout)
            self.figure = None; self.canvas = None; self.axes = None; self.tree = None
            self.clicked_clade = None
            self.deletion_mode_active = False
            return

        self.figure = Figure(figsize=(7, 5), dpi=100)
        self.canvas = FigureCanvas(self.figure)

        layout = QVBoxLayout(self)
        layout.addWidget(self.canvas)
        self.setLayout(layout)

        self.tree: Optional[Phylo.BaseTree.Tree] = None
        self.axes = None
        self.clicked_clade: Optional[Clade] = None
        self.deletion_mode_active = False

        self.canvas.mpl_connect('button_press_event', self._on_mouse_press)

        self.logger.info("TreeCanvas initialized with event handling and deletion mode support.")

    def set_deletion_mode(self, active: bool):
        """Activates or deactivates deletion mode for the canvas."""
        self.deletion_mode_active = active
        self.logger.info(f"Deletion mode {'activated' if active else 'deactivated'}.")
        if self.canvas: # Ensure canvas exists
            if active:
                self.canvas.setCursor(QCursor(Qt.CursorShape.CrossCursor))
            else:
                self.canvas.setCursor(QCursor(Qt.CursorShape.ArrowCursor))


    def draw_tree(self, tree: Optional[Phylo.BaseTree.Tree]) -> None:
        if not self.canvas or not self.figure:
            self.logger.error("Canvas not initialized, cannot draw tree.")
            return

        self.tree = tree
        self.figure.clear()

        if self.tree is None:
            self.logger.info("No tree to draw. Clearing canvas to 'No tree loaded'.")
            self.axes = self.figure.add_subplot(111)
            self.axes.text(0.5, 0.5, "No tree loaded or generated.",
                           ha='center', va='center',
                           transform=self.axes.transAxes, fontsize=12, color='gray')
            self.axes.set_axis_off()
            self.canvas.draw()
            return

        try:
            self.axes = self.figure.add_subplot(111)
            font_family = settings_manager.get_setting("visualization.font_family", "Arial")
            font_size = settings_manager.get_setting("visualization.font_size", 8)
            line_thickness = settings_manager.get_setting("visualization.line_thickness", 1.0)
            show_confidence = settings_manager.get_setting("visualization.show_confidence_values", True)

            def label_func(clade):
                return clade.name if clade.name and clade.name != "None" else ""

            Phylo.draw(self.tree, axes=self.axes, do_show=False, show_confidence=show_confidence, label_func=label_func)

            for item in self.axes.get_xticklabels() + self.axes.get_yticklabels():
                item.set_fontsize(font_size); item.set_fontfamily(font_family)
            for text_obj in self.axes.texts:
                text_obj.set_fontsize(font_size); text_obj.set_fontfamily(font_family)
            for line in self.axes.findobj(matplotlib.lines.Line2D):
                line.set_linewidth(line_thickness)
            self.axes.set_title("Phylogenetic Tree", fontsize=font_size + 2, family=font_family)

            self.axes.spines['top'].set_visible(False); self.axes.spines['right'].set_visible(False)
            self.axes.spines['left'].set_visible(False); self.axes.spines['bottom'].set_visible(False)
            self.axes.set_xticks([]); self.axes.set_yticks([])

            try: self.figure.tight_layout()
            except Exception as e_tl: self.logger.warning(f"tight_layout() failed: {e_tl}")

            self.canvas.draw()
            self.logger.info("Tree drawn on canvas with custom visualization settings.")
        except Exception as e:
            self.logger.error(f"Error drawing tree: {e}", exc_info=True)
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, f"Error drawing tree:\n{e}", ha='center', va='center', transform=ax.transAxes, color='red', wrap=True)
            ax.set_axis_off()
            self.canvas.draw()

    def clear_tree(self) -> None:
        if not self.canvas or not self.figure: return
        self.tree = None
        self.figure.clear()
        self.axes = self.figure.add_subplot(111)
        self.axes.text(0.5, 0.5, "Tree cleared.", ha='center', va='center', transform=self.axes.transAxes, fontsize=12, color='gray')
        self.axes.set_axis_off()
        self.canvas.draw()
        self.logger.info("Tree canvas cleared.")

    def _on_mouse_press(self, event):
        self.clicked_clade = None
        if not self.figure or not self.axes or event.inaxes != self.axes or self.tree is None:
            return

        # Identify clade (simplified text-based)
        # This heuristic prioritizes text artists (tip labels).
        for text_artist in self.axes.texts:
            if text_artist.contains(event)[0]:
                clade_name = text_artist.get_text()
                target_clades = list(self.tree.find_clades(name=clade_name))
                if target_clades:
                    self.clicked_clade = target_clades[0]
                    self.logger.debug(f"Clicked on text for clade: {self.clicked_clade.name if self.clicked_clade.name else 'Unnamed Internal'}")
                    break # Found a match based on text label

        if not self.clicked_clade:
            self.logger.debug("No specific clade text label identified at click position.")
            # Future: Implement more robust click detection (e.g., nearest node/branch) if needed.
            return # No action if no clade identified near click

        # --- Deletion Mode Logic ---
        if self.deletion_mode_active:
            if event.button == 1: # Left-click for deletion
                if self.clicked_clade.name: # Ensure name exists before emitting
                    self.logger.info(f"Deletion requested for clade: {self.clicked_clade.name}")
                    self.delete_clade_requested.emit(self.clicked_clade.name, self.clicked_clade.is_terminal())
                else:
                    self.logger.warning("Clicked on a clade with no name for deletion.")
                return # Prevent other actions in deletion mode
            else: # Other mouse buttons do nothing in deletion mode
                return

        # --- Normal Mode Logic ---
        if event.button == 1:
            if not self.clicked_clade.is_terminal():
                self._toggle_clade_collapse(self.clicked_clade)
        elif event.button == 3:
            self._show_context_menu(event, self.clicked_clade)


    def _show_context_menu(self, event, clade: Clade):
        menu = QMenu(self.canvas)
        if clade.is_terminal():
            action_reroot = menu.addAction(f"Re-root on tip: {clade.name if clade.name else 'Unnamed'}")
            action_reroot.triggered.connect(lambda: self._reroot_tree_with_outgroup(clade))
        else:
            action_text = "Expand Clade" if clade.is_collapsed() else "Collapse Clade"
            action_collapse = menu.addAction(action_text)
            action_collapse.triggered.connect(lambda: self._toggle_clade_collapse(clade))
            action_reroot_branch = menu.addAction(f"Re-root on branch to this node")
            action_reroot_branch.triggered.connect(lambda: self._reroot_tree_with_outgroup(clade))

        if hasattr(event, 'guiEvent') and event.guiEvent is not None:
            global_pos = event.guiEvent.globalPos()
        else:
            # This fallback might be inaccurate depending on window decorations and exact setup.
            global_pos = self.canvas.mapToGlobal(self.canvas.pos().toPoint() + event.pos().toPoint() if event.pos() else QPoint(int(event.x), int(event.y)))
            self.logger.warning("Using fallback for QMenu position.")
        menu.exec(global_pos)

    def _toggle_clade_collapse(self, clade: Clade):
        if clade is None or clade.is_terminal():
            self.logger.warning("_toggle_clade_collapse called on terminal or None clade.")
            return
        clade.collapsed = not clade.is_collapsed()
        self.logger.info(f"Toggled collapse for clade (now {'collapsed' if clade.is_collapsed() else 'expanded'}). Redrawing.")
        self.draw_tree(self.tree)

    def _reroot_tree_with_outgroup(self, outgroup_clade: Clade):
        if outgroup_clade is None or self.tree is None:
            self.logger.warning("Cannot re-root: outgroup_clade or tree is None."); return
        try:
            self.tree.root_with_outgroup(outgroup_clade)
            self.logger.info(f"Re-rooted tree with outgroup: {outgroup_clade.name if outgroup_clade.name else 'Unnamed internal'}. Redrawing.")
            self.draw_tree(self.tree)
        except Exception as e:
            self.logger.error(f"Re-rooting failed: {e}", exc_info=True)
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Re-rooting Error", f"Failed to re-root tree: {e}")


if __name__ == '__main__':
    from PyQt6.QtWidgets import QApplication, QMainWindow
    from Bio.Phylo.BaseTree import Tree as BioTree, Clade as BioClade
    from PyQt6.QtCore import QPoint

    logging.basicConfig(level=logging.DEBUG)
    app = QApplication(sys.argv)
    main_win = QMainWindow()
    main_win.setWindowTitle("TreeCanvas Test")
    main_win.setGeometry(200, 200, 700, 500)

    if FigureCanvas is None:
        error_label_main = QLabel("Matplotlib Qt backend not found. Cannot run test.", main_win)
        main_win.setCentralWidget(error_label_main); main_win.show(); sys.exit(app.exec())

    tree_canvas_widget = TreeCanvas(main_win)
    main_win.setCentralWidget(tree_canvas_widget)

    c1 = BioClade(name="TipA", branch_length=0.1)
    c2 = BioClade(name="TipB", branch_length=0.2); c2.confidence = 100
    c3 = BioClade(name="TipC", branch_length=0.3)
    c4 = BioClade(name="TipD", branch_length=0.4); c4.confidence = 95
    c5 = BioClade(name="TipE", branch_length=0.5)
    n1 = BioClade(clades=[c1, c2], branch_length=0.05); n1.confidence = 90; n1.name="Node_AB"
    n2 = BioClade(clades=[c3, c4], branch_length=0.06); n2.confidence = 80; n2.name="Node_CD"
    n3 = BioClade(clades=[n2, c5], branch_length=0.07); n3.name="Node_CDE"
    root = BioClade(clades=[n1, n3])
    dummy_tree_interactive = BioTree(root=root, rooted=True)

    tree_canvas_widget.draw_tree(dummy_tree_interactive)
    main_win.show()
    sys.exit(app.exec())
