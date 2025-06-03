# Core functionality for TreeWeaver

from .data_structures import SequenceRecord, SequenceData
from .file_parser import (
    load_sequences,
    write_sequences, # Generic writer
    write_fasta,
    write_phylip,
    write_nexus,
    parse_newick,
    write_newick,
    SEQ_FORMAT_TYPE 
)
from .phylogenetics import (
    create_phylip_with_internal_ids,
    map_raxml_tree_tips_to_original_ids
)
# Placeholder for help manager
# from .help_manager import ...


__all__ = [
    # Data Structures
    'SequenceRecord',
    'SequenceData',
    # File I/O
    'load_sequences',
    'write_sequences',
    'write_fasta',
    'write_phylip',
    'write_nexus',
    'parse_newick',
    'write_newick',
    'SEQ_FORMAT_TYPE',
    # Phylogenetics
    'create_phylip_with_internal_ids',
    'map_raxml_tree_tips_to_original_ids',
    # Help Manager
    'get_help_html',
]

import logging
from .help_manager import get_help_html # Ensure this is imported to be exportable

# Set up a default null handler for the library to avoid 'No handler found' warnings
# if the application using this library doesn't configure logging.
# The application itself (treeweaver.py) will configure the actual handlers.
logging.getLogger(__name__).addHandler(logging.NullHandler())
