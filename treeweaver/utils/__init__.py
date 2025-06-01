# Utility functions for TreeWeaver

from .external_tools import (
    run_mafft,
    run_raxml_ng,
    run_iqtree, # Renamed from run_iqtree_model_finder for generality
    run_modeltest_ng,
    _check_tool_path # If useful for GUI to check tool status
)

__all__ = [
    'run_mafft',
    'run_raxml_ng',
    'run_iqtree',
    'run_modeltest_ng',
    '_check_tool_path' # Exposing this can be useful for UI checks
]

import logging
# Set up a default null handler for the library to avoid 'No handler found' warnings
logging.getLogger(__name__).addHandler(logging.NullHandler())
