# TreeWeaver v0.1

**License:** MIT License

## Overview

TreeWeaver is a desktop application designed for biologists and researchers working in phylogenetics. It provides a user-friendly graphical interface for visualizing, manipulating, and analyzing phylogenetic trees and associated sequence data. The primary goal of TreeWeaver is to streamline common phylogenetic workflows by integrating popular external tools and offering interactive data exploration capabilities.

## Key Features

*   **Modern GUI:** Built with Python and PyQt6, featuring a dark mode by default for comfortable viewing and helpful tooltips for ease of use.
*   **Data Import:** Supports common sequence formats including FASTA, PHYLIP, and FASTQ.
*   **Sequence Alignment:** Integrated MAFFT for performing multiple sequence alignments.
*   **Substitution Model Selection:** Integrated IQ-TREE (via its ModelFinder functionality) and ModelTest-NG to help users select the best-fit evolutionary model for their data.
*   **Phylogenetic Tree Generation:** Integrated RAxML-NG for maximum likelihood tree inference. Includes automated internal mapping of sequence names to ensure compatibility with RAxML-NG's requirements.
*   **Interactive Tree Visualization:** A dedicated canvas displays phylogenetic trees, offering clear visualization of branch lengths and topology. Basic zoom/pan is available via Matplotlib's default toolbar (if enabled/visible).
*   **Tree Customization:** Users can adjust the appearance of the tree, including font family, font size for labels, and branch line thickness, via the Settings dialog. Confidence values (e.g., bootstrap support) can be toggled on/off.
*   **Tree Manipulation:**
    *   **Collapse/Expand Clades:** Interactively hide or show clades on the tree.
    *   **Re-root Tree:** Change the root of the tree by selecting a new outgroup (tip or branch).
*   **Data Editing:**
    *   Edit sequence identifiers (names) and the sequence strings directly within the application.
    *   Changes to sequence data automatically invalidate previous analysis results (tree, model) to ensure consistency.
*   **Deletion Mode:** An interactive mode to remove specific sequences or entire clades from the tree and the underlying dataset.
*   **Data Export:**
    *   **Trees:** Export in Newick format.
    *   **Tree Images:** Save the current tree visualization as PNG, SVG, JPG, or PDF.
    *   **Alignments/Sequences:** Export in FASTA, PHYLIP, or NEXUS formats.
*   **In-application Help System:** Comprehensive help documentation accessible from the "Help" menu, covering all major features.
*   **Configurable Settings:** A dialog to configure paths to external bioinformatics tools and set default options (e.g., thread counts).
*   **Debugging:** Command-line option `--debug` for verbose console output, aiding in troubleshooting.

## Installation

### Recommended Setup: Using Conda

1.  **Install Conda:** Ensure you have Miniconda or Anaconda installed. If not, download and install it from [https://docs.conda.io/en/latest/miniconda.html](https://docs.conda.io/en/latest/miniconda.html).
2.  **Get TreeWeaver:** Clone the TreeWeaver repository (if you haven't already):
    ```bash
    git clone https://github.com/AlanRockefeller/TreeWeaver.git 
    cd TreeWeaver
    ```
    (If you downloaded a source archive, extract it and navigate into the directory).
3.  **Create Conda Environment:** Create the Conda environment using the provided `environment.yml` file. This will install all necessary Python dependencies with compatible versions:
    ```bash
    conda env create -f environment.yml
    ```
4.  **Activate Environment:** Activate the new environment:
    ```bash
    conda activate treeweaver-env
    ```
5.  **Ready to Run:** You are now ready to run TreeWeaver (see 'Running TreeWeaver' section below). Each time you want to run TreeWeaver in a new terminal session, remember to activate the environment using `conda activate treeweaver-env`.

### Alternative Setup: Using pip (Virtual Environment Recommended)

1.  **Python Requirement:**
    *   TreeWeaver requires Python 3.8 or newer. Ensure it's installed and accessible.
2.  **Create Virtual Environment (Recommended):**
    *   It's highly recommended to use a Python virtual environment to manage dependencies:
        ```bash
        python -m venv venv_treeweaver
        source venv_treeweaver/bin/activate  # On Windows: venv_treeweaver\Scripts\activate
        ```
3.  **Install Dependencies:**
    *   Navigate to the project directory in your terminal (where `requirements.txt` is located).
    *   Install required Python packages using pip:
        ```bash
        pip install -r requirements.txt
        ```
    *   This will install `PyQt6`, `biopython`, `matplotlib`, and `markdown`.
    *   **Note:** While `pip` can be used, Conda is recommended to ensure better compatibility of complex libraries like NumPy and Matplotlib, and to avoid potential conflicts like the NumPy versioning issue (e.g. NumPy 1.x vs 2.x). If using `pip`, ensure your NumPy and Matplotlib versions are compatible. If you encounter issues, try the Conda setup.

### External Tools (Required for Analysis Features)

Regardless of how you set up your Python environment (Conda or pip), TreeWeaver relies on the following external command-line tools for its analysis capabilities. These must be installed separately by the user:

*   **MAFFT:** For multiple sequence alignment. (Search for "MAFFT aligner installation")
*   **RAxML-NG:** For phylogenetic tree inference. (Search for "RAxML-NG installation")
*   **IQ-TREE:** For phylogenetic tree inference and model selection (ModelFinder). (Search for "IQ-TREE installation")
*   **ModelTest-NG:** For substitution model selection. (Search for "ModelTest-NG installation")

After installation, these tools must either be:
*   Available in your system's PATH environment variable.
*   Or, their full executable paths must be configured within TreeWeaver via `File > Settings... > External Tools`.

## Running TreeWeaver

*   **If using Conda:** Ensure the `treeweaver-env` environment is activated (`conda activate treeweaver-env`).
*   **If using pip with a virtual environment:** Ensure your virtual environment is activated.
*   Navigate to the root directory of TreeWeaver in your terminal.
*   To run the application:
    ```bash
    python treeweaver.py
    ```
*   For detailed console logs, which can be helpful for debugging or seeing tool outputs:
    ```bash
    python treeweaver.py --debug
    ```

## Basic Usage Workflow

1.  **Configure Tool Paths (First time or if not in PATH):**
    *   Go to `File > Settings...`.
    *   In the "External Tools" tab, ensure the paths to MAFFT, RAxML-NG, IQ-TREE, and ModelTest-NG are correctly set.
    *   Adjust default thread counts for tools if desired.
    *   Save settings.

2.  **Load Sequences:**
    *   Go to `File > Import Sequences...`.
    *   Select your sequence file (e.g., in FASTA format). Loaded sequences appear in the left panel.

3.  **Align Sequences (if unaligned):**
    *   Go to `Tools > Run MAFFT...`.
    *   The alignment will replace the current sequences. The sequence panel will update.

4.  **Select Substitution Model:**
    *   Go to `Tools > Run IQ-TREE (ModelFinder)...` or `Tools > Run ModelTest-NG...`.
    *   The best-fit model (typically by BIC) will be displayed in the status bar.

5.  **Generate Phylogenetic Tree:**
    *   Go to `Tools > Run RAxML-NG (Tree Inference)...`.
    *   Confirm or modify the substitution model (pre-filled if model selection was run), set bootstrap replicates, and other parameters. Click "OK".
    *   The generated tree will be displayed in the central canvas.

6.  **View, Customize, and Interact:**
    *   Use the options in `File > Settings... > Visualization` to change tree appearance (fonts, line thickness, show/hide confidence values).
    *   Right-click on tree elements (tips, internal nodes if their labels are identifiable) for options like collapsing/expanding clades or re-rooting.
    *   Use `Edit > Enable Deletion Mode` to remove clades/sequences by clicking on them.

7.  **Export Results:**
    *   Use `File > Export` submenu to save:
        *   The current alignment/sequences (`Export Alignment...`).
        *   The tree in Newick format (`Export Tree (Newick)...`).
        *   The tree visualization as an image (`Export Tree as Image...`).

## Future Development

*   Support for more input/output formats (e.g., Nexus trees, GFF for annotations).
*   Advanced tree annotation and metadata integration.
*   More sophisticated tree visualization options and controls.
*   Integration of additional phylogenetic tools.
*   Session management (saving/loading projects).

## Contributing

Contributions are welcome! Please refer to (placeholder for CONTRIBUTING.md if it existed).
You can report bugs or suggest features via the project's issue tracker.
