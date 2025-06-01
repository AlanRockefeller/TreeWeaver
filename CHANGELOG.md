# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2024-03-16

### Added

*   Initial beta release of TreeWeaver, a tool for phylogenetic tree visualization, manipulation, and analysis.
*   Graphical User Interface (GUI) built with Python (PyQt6) with a dark mode default and helpful tooltips.
*   Support for importing sequence data: FASTA, PHYLIP, FASTQ.
*   Integration of MAFFT for multiple sequence alignment.
*   Integration of IQ-TREE (ModelFinder) and ModelTest-NG for substitution model selection.
*   Integration of RAxML-NG for maximum likelihood phylogenetic tree generation, including internal mapping of sequence names for compatibility.
*   Interactive tree visualization canvas with zoom/pan capabilities (via Matplotlib's toolbar if active).
*   Customization options for tree display: font family, font size, and line thickness.
*   Interactive tree manipulation: collapse/expand clades, re-root tree by clicking on text labels or via context menu.
*   Sequence data editing: modify sequence names and content directly within the application.
*   Deletion Mode for removing sequences or clades directly from the tree view, with confirmation prompts.
*   Data export:
    *   Phylogenetic trees in Newick format.
    *   Tree visualizations as image files (PNG, SVG, JPG, PDF).
    *   Sequence alignments in FASTA, PHYLIP, NEXUS formats.
*   In-application help system with detailed documentation accessible via the "Help" menu, rendered from Markdown.
*   Settings dialog for configuring external tool paths and application options (e.g., thread counts, visualization preferences).
*   Command-line `--debug` option for verbose logging to the console.
*   Basic tooltips for most GUI elements to guide users.
*   Robust error handling and user feedback for external tool execution and file operations.
*   Persistent user settings for tool paths, options, and last-used directories for file dialogs.
