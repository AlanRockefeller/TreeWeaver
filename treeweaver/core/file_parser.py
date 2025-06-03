# This module will handle parsing of various file formats (e.g., Newick, Nexus).

import logging
import os
from typing import Optional, Union, List, Literal

from Bio import SeqIO, Phylo
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord as BioSeqRecord
# Bio.Nexus.Nexus is needed for more complex Nexus writing, but SeqIO handles basic cases.
# from Bio.Nexus import Nexus

from .data_structures import SequenceData, SequenceRecord

logger = logging.getLogger(__name__)

# Supported sequence formats for loading and a more specific type for writing
SEQ_FORMAT_TYPE = Literal["fasta", "phylip", "fastq", "nexus"]


def load_sequences(filepath: str, file_format: Optional[SEQ_FORMAT_TYPE] = None) -> Optional[SequenceData]:
    """
    Loads sequences from a file, attempting to auto-detect format if not provided.

    Args:
        filepath: Path to the sequence file.
        file_format: The format of the sequence file (e.g., "fasta", "phylip", "fastq").
                     If None, attempts to guess from common extensions.

    Returns:
        A SequenceData object populated with sequences, or None if loading fails.
    """
    if not os.path.exists(filepath):
        logger.error(f"File not found: {filepath}")
        # raise FileNotFoundError(f"File not found: {filepath}") # Or return None
        return None

    detected_format = file_format
    if not detected_format:
        # Basic format detection from extension
        _, ext = os.path.splitext(filepath.lower())
        if ext in ['.fasta', '.fa', '.fna', '.fas']:
            detected_format = "fasta"
        elif ext in ['.phy', '.phylip']:
            detected_format = "phylip"
        elif ext in ['.fq', '.fastq']:
            detected_format = "fastq"
        elif ext in ['.nex', '.nexus']:
            detected_format = "nexus" # Nexus can contain sequences
        else:
            logger.error(f"Could not determine file format for: {filepath}. Please specify format.")
            return None
    
    logger.info(f"Attempting to load '{filepath}' as '{detected_format}' format.")
    
    data = SequenceData()
    try:
        # SeqIO.parse returns an iterator. We need to consume it.
        # For FASTQ, quality scores are available via record.letter_annotations["phred_quality"]
        # We are currently ignoring them for simplicity in SequenceRecord.
        for bio_record in SeqIO.parse(filepath, detected_format):
            seq_id = bio_record.id
            sequence = str(bio_record.seq)
            description = bio_record.description if bio_record.description != seq_id else ""
            
            if not sequence:
                logger.warning(f"Sequence '{seq_id}' in '{filepath}' is empty. Skipping.")
                continue

            added_record = data.add_sequence(seq_id, sequence, description)
            if not added_record:
                logger.warning(f"Failed to add sequence ID '{seq_id}' from '{filepath}' to SequenceData (likely a duplicate or invalid ID).")
        
        if len(data) == 0:
            logger.warning(f"No sequences loaded from '{filepath}'. The file might be empty or in an incorrect format.")
            return None # Or return empty SequenceData based on desired behavior

        logger.info(f"Successfully loaded {len(data)} sequences from '{filepath}'.")
        return data

    except FileNotFoundError: # Should be caught by os.path.exists, but as a safeguard
        logger.error(f"File not found during SeqIO parsing: {filepath}")
        return None
    except ValueError as e: # Handles malformed files for the specified format
        logger.error(f"Error parsing '{filepath}' as '{detected_format}': {e}")
        return None
    except Exception as e: # Catch any other unexpected errors during parsing
        logger.error(f"An unexpected error occurred while parsing '{filepath}': {e}")
        return None


def _convert_to_biopython_seqrecords(sequence_data: SequenceData) -> List[BioSeqRecord]:
    """Helper to convert SequenceRecord objects to Biopython SeqRecord objects."""
    bio_records = []
    for record in sequence_data.get_all_sequences():
        # Use original ID for output, description might need adjustment if it was auto-generated
        # and only contained the ID.
        desc = record.description
        if desc == f"{record.id} sequence": # Avoid redundant description
            desc = ""
        # Create Bio.SeqRecord.SeqRecord for Biopython
        # The id should be just the identifier, description is the rest of the header line.
        # Biopython's SeqRecord takes id and description separately.
        # If record.description was `seq1 some description`, id='seq1', description='some description'
        # If record.description was just `seq1`, id='seq1', description=''
        
        # SeqIO.write will typically format the header as ">id description"
        # So, if description contains the id, it might appear duplicated.
        # Let's ensure the description doesn't redundantly include the ID if it's the sole content.
        final_description = record.description
        if final_description == record.id: # If description is just the ID, Biopython handles it.
            final_description = ""

        bio_rec = BioSeqRecord(Seq(record.sequence), id=record.id, description=final_description, name="") # name is often redundant with id
        bio_records.append(bio_rec)
    return bio_records

def write_sequences(sequence_data: SequenceData, filepath: str, file_format: SEQ_FORMAT_TYPE) -> bool:
    """
    Writes sequences from a SequenceData object to a file.

    Args:
        sequence_data: The SequenceData object containing the sequences.
        filepath: Path to the output file.
        file_format: The format to write ("fasta", "phylip", "nexus").

    Returns:
        True if writing was successful, False otherwise.
    """
    if not sequence_data or len(sequence_data) == 0:
        logger.warning("No sequence data provided to write. Aborting.")
        return False

    bio_records = _convert_to_biopython_seqrecords(sequence_data)
    
    try:
        # For PHYLIP, Biopython might truncate IDs to 10 characters. This is a limitation of the format.
        # We should warn the user about this if PHYLIP is chosen.
        if file_format == "phylip":
            original_ids = [rec.id for rec in sequence_data.get_all_sequences()]
            if any(len(oid) > 10 for oid in original_ids):
                logger.warning(
                    f"PHYLIP format truncates sequence IDs to 10 characters. "
                    f"Long IDs in your data will be shortened in '{filepath}'. "
                    f"Consider using FASTA or NEXUS for full ID preservation."
                )
        
        # For NEXUS, SeqIO can write basic sequence data. For more complex Nexus files (trees, charsets, etc.),
        # one would use Bio.Nexus.Nexus objects directly.
        count = SeqIO.write(bio_records, filepath, file_format)
        if count == 0:
            logger.warning(f"No sequences were written to {filepath} for format {file_format} (input might have been empty or filtered).")
            # Still consider it a successful write operation if no error, but 0 records.
            # Or return False if 0 records written is an issue. For now, True if no exception.
        logger.info(f"Successfully wrote {count} sequences to '{filepath}' in {file_format} format.")
        return True
    except (IOError, PermissionError) as e:
        logger.error(f"File system error writing sequences to '{filepath}' in {file_format} format: {e}", exc_info=True)
        return False
    except Exception as e: # Catch other potential errors from SeqIO.write or elsewhere
        logger.error(f"Unexpected error writing sequences to '{filepath}' in {file_format} format: {e}", exc_info=True)
        return False

# Specific writer functions for convenience
def write_fasta(sequence_data: SequenceData, filepath: str) -> bool:
    return write_sequences(sequence_data, filepath, "fasta")

def write_phylip(sequence_data: SequenceData, filepath: str) -> bool:
    return write_sequences(sequence_data, filepath, "phylip")

def write_nexus(sequence_data: SequenceData, filepath: str) -> bool:
    # Note: SeqIO's nexus writer is for sequential nexus. For interleaved, or trees + sequences,
    # direct construction with Bio.Nexus might be needed. This is fine for sequences only.
    return write_sequences(sequence_data, filepath, "nexus")


# Tree File Parsing
def parse_newick(filepath: str) -> Optional[Phylo.BaseTree.Tree]:
    """
    Parses a Newick tree file.

    Args:
        filepath: Path to the Newick file.

    Returns:
        A Biopython Tree object, or None if parsing fails.
    """
    if not os.path.exists(filepath):
        logger.error(f"Tree file not found: {filepath}")
        return None
    try:
        tree = Phylo.read(filepath, "newick")
        logger.info(f"Successfully parsed Newick tree from '{filepath}'. Found {tree.count_terminals()} terminals.")
        return tree
    except FileNotFoundError: # Should be caught by os.path.exists
        logger.error(f"Tree file not found during Phylo.read: {filepath}")
        return None
    except Exception as e: # Biopython can raise various errors for malformed Newick
        logger.error(f"Error parsing Newick tree from '{filepath}': {e}")
        return None

# Tree File Writing
def write_newick(tree: Phylo.BaseTree.Tree, filepath: str) -> bool:
    """
    Writes a Biopython Tree object to a Newick file.

    Args:
        tree: The Biopython Tree object.
        filepath: Path to the output Newick file.

    Returns:
        True if writing was successful, False otherwise.
    """
    if not tree:
        logger.warning("No tree object provided to write. Aborting.")
        return False
    try:
        Phylo.write(tree, filepath, "newick")
        logger.info(f"Successfully wrote tree to '{filepath}' in Newick format.")
        return True
    except (IOError, PermissionError) as e:
        logger.error(f"File system error writing Newick tree to '{filepath}': {e}", exc_info=True)
        return False
    except Exception as e: # Catch other potential errors from Phylo.write
        logger.error(f"Unexpected error writing Newick tree to '{filepath}': {e}", exc_info=True)
        return False


if __name__ == '__main__':
    # Basic testing for file_parser
    logging.basicConfig(level=logging.DEBUG)
    
    # Create dummy files for testing
    test_data_dir = "temp_test_data"
    os.makedirs(test_data_dir, exist_ok=True)

    fasta_content = """>seq1 description one
ATGCATGC
>seq2
GATTACA
>seq3 a very long description for this sequence
CGTACGTA
"""
    phylip_content = """3 8
seq1      ATGCATGC
seq2      GATTACA-
seq3      CGTACGTA
""" # Note: Phylip IDs are typically fixed length, often 10 chars. Biopython handles this.
    # Biopython's Phylip parser is strict about the name length.
    # Let's make them 10 characters.
    phylip_content_strict = """3 8
seq1------ ATGCATGC
seq2------ GATTACA-
seq3------ CGTACGTA
"""


    newick_content = "((seq1:0.1,seq2:0.2):0.05,seq3:0.15);"

    fasta_file = os.path.join(test_data_dir, "test.fasta")
    phylip_file = os.path.join(test_data_dir, "test.phy")
    newick_file = os.path.join(test_data_dir, "test.nwk")

    with open(fasta_file, "w") as f: f.write(fasta_content)
    with open(phylip_file, "w") as f: f.write(phylip_content_strict)
    with open(newick_file, "w") as f: f.write(newick_content)

    # Test loading sequences
    logger.info("--- Testing FASTA load ---")
    seq_data_fasta = load_sequences(fasta_file, "fasta")
    if seq_data_fasta:
        assert len(seq_data_fasta) == 3
        assert seq_data_fasta.get_sequence_by_id("seq1").sequence == "ATGCATGC"
        assert seq_data_fasta.get_sequence_by_id("seq3").description == "seq3 a very long description for this sequence"
        logger.info(f"FASTA loaded: {len(seq_data_fasta)} sequences.")
        for rec in seq_data_fasta: logger.debug(rec)

    logger.info("--- Testing PHYLIP load ---")
    seq_data_phylip = load_sequences(phylip_file) # Test auto-detect
    if seq_data_phylip:
        assert len(seq_data_phylip) == 3
        # Biopython's Phylip parser might strip the hyphens from IDs like 'seq1------'
        assert seq_data_phylip.get_sequence_by_id("seq1").sequence == "ATGCATGC" 
        assert seq_data_phylip.get_sequence_by_id("seq2").sequence == "GATTACA-"
        logger.info(f"PHYLIP loaded: {len(seq_data_phylip)} sequences.")
        for rec in seq_data_phylip: logger.debug(rec)


    # Test writing sequences
    if seq_data_fasta:
        logger.info("--- Testing FASTA write ---")
        out_fasta = os.path.join(test_data_dir, "out.fasta")
        write_fasta(seq_data_fasta, out_fasta)
        assert os.path.exists(out_fasta)
        # 간단히 읽어서 첫번째 ID 확인
        loaded_out_fasta = load_sequences(out_fasta, "fasta")
        assert loaded_out_fasta.get_sequence_by_id("seq1") is not None

        logger.info("--- Testing PHYLIP write ---")
        out_phylip = os.path.join(test_data_dir, "out.phy")
        write_phylip(seq_data_fasta, out_phylip) # Write data from FASTA load to PHYLIP
        assert os.path.exists(out_phylip)
        # Verify by loading (IDs might be truncated)
        loaded_out_phylip = load_sequences(out_phylip, "phylip")
        # Depending on Biopython's writer, ID "seq1" might become "seq1      " or "seq1"
        # and then read back as "seq1".
        assert loaded_out_phylip.get_sequence_by_id("seq1") is not None 
        logger.info("PHYLIP write test passed (check file for truncation if IDs were long).")


        logger.info("--- Testing NEXUS write ---")
        out_nexus = os.path.join(test_data_dir, "out.nex")
        write_nexus(seq_data_fasta, out_nexus)
        assert os.path.exists(out_nexus)
        loaded_out_nexus = load_sequences(out_nexus, "nexus")
        assert loaded_out_nexus.get_sequence_by_id("seq1") is not None


    # Test tree parsing
    logger.info("--- Testing Newick parse ---")
    tree = parse_newick(newick_file)
    if tree:
        assert tree.count_terminals() == 3
        assert any(c.name == "seq1" for c in tree.get_terminals())
        logger.info(f"Newick tree parsed. Terminals: {[t.name for t in tree.get_terminals()]}")

    # Test tree writing
    if tree:
        logger.info("--- Testing Newick write ---")
        out_newick = os.path.join(test_data_dir, "out.nwk")
        write_newick(tree, out_newick)
        assert os.path.exists(out_newick)
        loaded_out_newick = parse_newick(out_newick)
        assert loaded_out_newick.count_terminals() == 3

    logger.info("Basic file_parser tests completed.")
    # Consider removing temp_test_data directory after tests
    # import shutil
    # shutil.rmtree(test_data_dir)
    # logger.info(f"Removed temporary test data directory: {test_data_dir}")
