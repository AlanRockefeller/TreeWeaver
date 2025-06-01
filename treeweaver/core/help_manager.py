# This module will manage and display help content and documentation.

import markdown
import logging

logger = logging.getLogger(__name__)

HELP_MARKDOWN_CONTENT = """
# TreeWeaver Help

## Introduction

Welcome to TreeWeaver! This application is designed to help you perform phylogenetic analysis,
from sequence alignment and model selection to tree inference and visualization.

## Getting Started

1.  **Loading Sequences:**
    *   Go to `File > Import Sequences...`.
    *   Supported formats: FASTA, PHYLIP, FASTQ, NEXUS.
    *   Loaded sequences will appear in the "Loaded Sequences" panel on the left.

2.  **User Interface Overview:**
    *   **Menu Bar:** Access all functionalities (File, Edit, View, Tools, Help).
    *   **Sequence Panel (Left):** Lists your loaded sequences with ID and length. Right-click for options.
    *   **Tree Canvas (Center):** Displays the phylogenetic tree once generated.
    *   **Status Bar (Bottom):** Shows current status, selected model, and other messages.

## Core Workflow

The typical workflow in TreeWeaver involves these steps:

1.  **Sequence Alignment (MAFFT):**
    *   Load your unaligned sequences.
    *   Go to `Tools > Run MAFFT...`.
    *   This will align your sequences using MAFFT (must be configured in Settings).
    *   The sequence panel will update with the aligned sequences (lengths may become uniform).
    *   **Note:** Running alignment will clear any existing tree and model selection results.

2.  **Model Selection (IQ-TREE / ModelTest-NG):**
    *   Requires an alignment (e.g., from MAFFT).
    *   Go to `Tools > Run IQ-TREE (ModelFinder)...` or `Tools > Run ModelTest-NG...`.
    *   These tools will test various substitution models and select the best-fit model for your data.
    *   The selected model (usually by BIC) will be displayed in the status bar.
    *   IQ-TREE and ModelTest-NG must be configured in `File > Settings...`.

3.  **Tree Generation (RAxML-NG):**
    *   Requires an alignment and preferably a selected substitution model.
    *   Go to `Tools > Run RAxML-NG (Tree Inference)...`.
    *   A dialog will appear allowing you to confirm/edit the model, set bootstrap replicates, and other parameters.
    *   RAxML-NG (must be configured in Settings) will then infer the tree.
    *   The resulting tree will be displayed in the central Tree Canvas.

## Tree Viewer

Once a tree is generated and displayed:

*   **Basic Navigation:** If the Matplotlib toolbar is active (usually at the top of the canvas or integrated), you can use its Pan and Zoom tools. (Toolbar not explicitly added by default in TreeWeaver yet).
*   **Customization (via Settings):**
    *   Go to `File > Settings... > Visualization` tab.
    *   You can customize:
        *   Font Family (for tree labels)
        *   Font Size (for tree labels and confidence values)
        *   Line Thickness (for tree branches)
        *   Show/Hide Confidence Values (e.g., bootstrap support)
    *   Changes are applied when you click "Save" in the Settings dialog. The current tree will redraw.
*   **Interactive Operations:**
    *   **Collapse/Expand Nodes:** Right-click on an internal node's label (if it has one and is identifiable by the click heuristic) or a tip. If an internal node is targeted, select "Collapse Clade" or "Expand Clade". Left-clicking an identifiable internal node's label also toggles collapse.
    *   **Re-rooting:** Right-click on a tip or an internal node's label. Select the "Re-root..." option.
    *   **Deletion Mode:**
        *   Enable via `Edit > Enable Deletion Mode`. The status bar will confirm.
        *   In this mode, left-clicking on a tip label (or an internal node label if identifiable) will prompt for deletion.
        *   If confirmed, the selected clade and all its descendants (if any) will be removed from the tree, and corresponding sequences will be removed from the sequence data.
        *   Disable deletion mode via `Edit > Disable Deletion Mode`.

## Data Management

*   **Editing Sequences:**
    *   Right-click on a sequence in the "Loaded Sequences" panel and select "Edit Sequence...".
    *   You can modify the sequence ID and the sequence string.
    *   Validation ensures IDs are not empty or conflicting, and sequence characters are valid.
    *   **Important:** Editing sequence data will invalidate and clear any existing alignment, model selection, and tree results.
*   **Exporting Data:**
    *   `File > Export > Export Alignment...`: Saves the current sequences (aligned or unaligned) in FASTA, PHYLIP, or NEXUS format.
    *   `File > Export > Export Tree (Newick)...`: Saves the current tree in Newick format.
    *   `File > Export > Export Tree as Image...`: Saves the displayed tree as an image (PNG, SVG, JPG, PDF).

## Settings

*   Access via `File > Settings...`.
*   **External Tools Tab:**
    *   Configure the full paths to MAFFT, RAxML-NG, IQ-TREE, and ModelTest-NG executables if they are not in your system's PATH.
    *   Set default thread counts for these tools.
*   **Visualization Tab:** Customize tree appearance (see "Tree Viewer" section).

## Command-line Options

*   `--debug`: Launches TreeWeaver in debug mode, which provides more verbose logging to the console. This is useful for troubleshooting.

## Troubleshooting

*   **"Tool not found" errors:** If you see messages like "MAFFT path is not configured" or "[TOOL] command not found", ensure the correct path to the executable is set in `File > Settings... > External Tools`. If the tool is supposed to be in your system PATH, verify your PATH environment variable.
*   **Tree drawing issues:** Ensure Matplotlib and a compatible Qt backend are correctly installed (`PyQt6`, `matplotlib`).
*   **Incorrect analysis results:** Double-check your input data, alignment quality, and chosen models/parameters.

---
For further assistance or to report issues, please visit the TreeWeaver project page.
(Project page URL would go here if it existed)
"""

def get_help_html() -> str:
    """
    Converts the Markdown help content to HTML with basic styling.
    """
    try:
        # CommonMark 'extra' includes abbreviations, attribute lists, fenced code blocks, footnotes, tables, etc.
        # 'nl2br' converts newlines to <br> tags.
        # 'toc' generates a table of contents (might need specific markers in MD like [TOC]).
        # 'sane_lists' improves list parsing.
        html_content = markdown.markdown(
            HELP_MARKDOWN_CONTENT,
            extensions=['extra', 'nl2br', 'toc', 'sane_lists']
        )

        # Basic CSS for better readability
        styled_html = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol";
                    line-height: 1.6;
                    padding: 15px;
                    background-color: #fdfdfd;
                    color: #333;
                }}
                h1, h2, h3, h4 {{
                    color: #2c3e50;
                    margin-top: 1.5em;
                    margin-bottom: 0.5em;
                }}
                h1 {{ font-size: 1.8em; border-bottom: 2px solid #bdc3c7; padding-bottom: 0.3em; }}
                h2 {{ font-size: 1.5em; border-bottom: 1px solid #eaecef; padding-bottom: 0.2em; }}
                h3 {{ font-size: 1.25em; }}
                h4 {{ font-size: 1.0em; }}
                code {{
                    background-color: #ecf0f1;
                    padding: 0.2em 0.4em;
                    margin: 0;
                    font-size: 85%;
                    border-radius: 3px;
                    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace;
                }}
                pre {{
                    background-color: #ecf0f1;
                    padding: 10px;
                    border-radius: 3px;
                    overflow-x: auto;
                    border: 1px solid #bdc3c7;
                }}
                pre code {{ background-color: transparent; padding: 0; }}
                ul, ol {{ padding-left: 20px; }}
                li {{ margin-bottom: 0.3em; }}
                a {{ color: #3498db; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
                table {{ border-collapse: collapse; margin: 1em 0; display: block; overflow-x: auto; }}
                th, td {{ border: 1px solid #dfe2e5; padding: 0.6em 1em; }}
                th {{ background-color: #f6f8fa; font-weight: bold; }}
                blockquote {{
                    padding: 0 1em;
                    color: #777;
                    border-left: 0.25em solid #dfe2e5;
                    margin-left: 0;
                }}
                hr {{ border: none; border-top: 1px solid #dfe2e5; margin: 1.5em 0; }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
        return styled_html
    except Exception as e:
        logger.error(f"Error converting help Markdown to HTML: {e}", exc_info=True)
        # Fallback basic HTML with error
        return f"<html><body><h1>Error generating help content</h1><p>Details: {e}</p></body></html>"

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    html = get_help_html()
    # print(html)
    try:
        with open("temp_help_preview.html", "w", encoding="utf-8") as f:
            f.write(html)
        logger.info("Help HTML content saved to temp_help_preview.html for testing.")
    except IOError as e:
        logger.error(f"Failed to write help preview file: {e}")
