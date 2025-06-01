# Core phylogenetic operations and data transformations for TreeWeaver

import logging
import os # For join in test section
from typing import Optional

from Bio import Phylo, SeqIO
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord as BioSeqRecord

from .data_structures import SequenceData # Assuming this is in the same 'core' package directory

logger = logging.getLogger(__name__)

def create_phylip_with_internal_ids(sequence_data: SequenceData, output_phylip_path: str) -> bool:
    """
    Creates a PHYLIP file from SequenceData, using internal numerical IDs as sequence names.

    Args:
        sequence_data: The SequenceData object containing sequences.
        output_phylip_path: Path to write the output PHYLIP file.

    Returns:
        True if successful, False otherwise.
    """
    if not sequence_data or len(sequence_data.get_all_sequences()) == 0:
        logger.error("No sequence data provided to create PHYLIP file.")
        return False

    biopython_records = []
    for seq_rec in sequence_data.get_all_sequences():
        internal_id_str = str(seq_rec.internal_id)
        if len(internal_id_str) > 10:
            logger.warning(f"Internal ID '{internal_id_str}' is longer than 10 characters. "
                           "This might be an issue for strict PHYLIP parsers, but RAxML-NG should be okay.")

        bio_srec = BioSeqRecord(Seq(seq_rec.sequence), id=internal_id_str, description="")
        biopython_records.append(bio_srec)

    try:
        count = SeqIO.write(biopython_records, output_phylip_path, "phylip-relaxed")
        if count == 0:
            logger.error(f"No records were written to PHYLIP file: {output_phylip_path}")
            return False
        logger.info(f"Successfully wrote {count} sequences with internal IDs to PHYLIP file: {output_phylip_path}")
        return True
    except Exception as e:
        logger.error(f"Error writing PHYLIP file with internal IDs to '{output_phylip_path}': {e}")
        return False


def map_raxml_tree_tips_to_original_ids(tree: Phylo.BaseTree.Tree, sequence_data: SequenceData) -> Optional[Phylo.BaseTree.Tree]:
    """
    Maps tip names in a RAxML-NG output tree (which are internal_ids) back to original sequence IDs.

    Args:
        tree: A Biopython Tree object (presumably from RAxML-NG).
        sequence_data: The SequenceData object used to generate internal IDs.

    Returns:
        The modified Biopython Tree object with original IDs as tip names, or None if input tree is None.
    """
    if not tree:
        logger.error("No tree provided for tip name mapping.")
        return None
    if not sequence_data:
        logger.error("No sequence data provided for tip name mapping.")
        return tree # Return tree unmodified if no mapping data

    for tip in tree.get_terminals():
        try:
            internal_id_from_tip = int(tip.name)
            original_id = sequence_data.get_original_id(internal_id_from_tip)
            if original_id:
                logger.debug(f"Mapping tip '{tip.name}' (internal ID: {internal_id_from_tip}) to original ID: '{original_id}'")
                tip.name = original_id
            else:
                logger.warning(f"Could not find original ID for tip name (internal ID): '{tip.name}'. Leaving as is.")
        except ValueError:
            logger.warning(f"Tip name '{tip.name}' is not a valid integer internal ID. Cannot map. Leaving as is.")
        except Exception as e:
            logger.error(f"An unexpected error occurred while mapping tip name '{tip.name}': {e}")

    logger.info("RAxML tree tip name mapping to original IDs completed.")
    return tree

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    import tempfile
    from io import StringIO

    sd = SequenceData()
    s1 = sd.add_sequence("SeqA_human", "ATGCGT")
    s2 = sd.add_sequence("SeqB_mouse", "GATTACA")
    s3 = sd.add_sequence("SeqC_chimp", "AGCTAGCT")

    if not (s1 and s2 and s3): logger.error("Failed to add sequences for testing."); exit()

    with tempfile.TemporaryDirectory() as tmpdir:
        test_phylip_path = os.path.join(tmpdir, "test_internal.phy")
        success_phylip = create_phylip_with_internal_ids(sd, test_phylip_path)
        assert success_phylip
        logger.info(f"PHYLIP with internal IDs created at: {test_phylip_path}")
        with open(test_phylip_path, "r") as f: logger.debug("PHYLIP content:\n" + f.read())

        dummy_newick_internal_ids = f"(({s1.internal_id}:0.1,{s2.internal_id}:0.2):0.05,{s3.internal_id}:0.3);"
        try:
            tree_internal = Phylo.read(StringIO(dummy_newick_internal_ids), "newick")
            logger.debug(f"Original tree with internal IDs: {str(tree_internal)}")
            # Phylo.draw_ascii(tree_internal) # Requires specific terminal capabilities

            mapped_tree = map_raxml_tree_tips_to_original_ids(tree_internal, sd)
            if mapped_tree:
                logger.debug(f"Mapped tree with original IDs: {str(mapped_tree)}")
                # Phylo.draw_ascii(mapped_tree)
                terminal_names = sorted([tip.name for tip in mapped_tree.get_terminals()])
                expected_names = sorted(["SeqA_human", "SeqB_mouse", "SeqC_chimp"])
                assert terminal_names == expected_names
                logger.info("Tree tip mapping test successful.")
            else:
                logger.error("Tree mapping returned None.")
        except Exception as e:
            logger.error(f"Error during tree mapping test: {e}")
    logger.info("phylogenetics.py basic tests completed.")
