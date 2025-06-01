# Unit tests for core I/O functionalities in TreeWeaver

import unittest
import os
import tempfile
import logging
from io import StringIO

# Modules to test
from treeweaver.core.data_structures import SequenceData
from treeweaver.core.file_parser import (
    load_sequences, write_fasta, write_phylip, write_nexus,
    parse_newick, write_newick, SEQ_FORMAT_TYPE
)
from Bio import Phylo # For creating a test tree object

# Configure logging for tests (optional, can be useful for debugging)
# logging.basicConfig(level=logging.DEBUG)
# To avoid logs during normal test runs unless a test fails,
# it's often better to let the test runner handle log capture.

class TestCoreIO(unittest.TestCase):

    def setUp(self):
        """Set up temporary files and test data for each test method."""
        self.test_dir = tempfile.TemporaryDirectory()

        self.fasta_content = """>seq1 desc1
ATGCGTAGCATCGATCGATCGATCGATCGATCGATCGATCG
>seq2 desc2
GATTACAGATTACAGATTACAGATTACAGATTACAGATTACA
>seq3 desc3
CGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACG
"""
        self.phylip_content_strict = """3 40
seq1------ ATGCGTAGCATCGATCGATCGATCGATCGATCGATCGATCG
seq2------ GATTACAGATTACAGATTACAGATTACAGATTACAGATTACA
seq3------ CGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACG
"""
        self.nexus_content_basic = """#NEXUS
BEGIN DATA;
DIMENSIONS NTAX=2 NCHAR=10;
FORMAT DATATYPE=DNA MISSING=? GAP=-;
MATRIX
seq1 ATGCATGCAT
seq2 GATTACAGAT
;
END;
"""

        self.newick_content = "((seq1:0.1,seq2:0.2):0.05,seq3:0.15);"

        self.fasta_file = self._create_temp_file("test.fasta", self.fasta_content)
        self.phylip_file = self._create_temp_file("test.phy", self.phylip_content_strict)
        self.nexus_file = self._create_temp_file("test.nex", self.nexus_content_basic)
        self.newick_file = self._create_temp_file("test.nwk", self.newick_content)

        # Create a SequenceData object for testing writes
        self.seq_data_instance = SequenceData()
        self.seq_data_instance.add_sequence("seq1", "ATGC", "desc1")
        self.seq_data_instance.add_sequence("seq2", "GATT", "desc2")

        # Create a simple Biopython tree for testing tree writing
        try:
            self.tree_instance = Phylo.read(StringIO(self.newick_content), "newick")
        except Exception as e:
            # This setup should not fail, but if it does, make it obvious
            logging.error(f"Failed to create tree instance in setUp: {e}")
            self.tree_instance = None


    def tearDown(self):
        """Clean up temporary files after each test method."""
        self.test_dir.cleanup()

    def _create_temp_file(self, name, content):
        """Helper function to create a temporary file with given content."""
        path = os.path.join(self.test_dir.name, name)
        with open(path, "w") as f:
            f.write(content)
        return path

    # --- Sequence Loading Tests ---
    def test_load_fasta(self):
        """Test loading sequences from a FASTA file."""
        seq_data = load_sequences(self.fasta_file, "fasta")
        self.assertIsNotNone(seq_data)
        self.assertEqual(len(seq_data), 3)
        self.assertEqual(seq_data.get_sequence_by_id("seq1").sequence, "ATGCGTAGCATCGATCGATCGATCGATCGATCGATCGATCG")
        self.assertEqual(seq_data.get_sequence_by_id("seq2").description, "seq2 desc2")

    def test_load_phylip_strict(self):
        """Test loading sequences from a PHYLIP file (strict format)."""
        seq_data = load_sequences(self.phylip_file, "phylip")
        self.assertIsNotNone(seq_data)
        self.assertEqual(len(seq_data), 3)
        # Biopython's Phylip parser might trim IDs like 'seq1------' to 'seq1'
        self.assertIsNotNone(seq_data.get_sequence_by_id("seq1"))
        self.assertEqual(seq_data.get_sequence_by_id("seq1").sequence, "ATGCGTAGCATCGATCGATCGATCGATCGATCGATCGATCG")

    def test_load_nexus_sequences(self):
        """Test loading sequences from a basic NEXUS file."""
        seq_data = load_sequences(self.nexus_file, "nexus")
        self.assertIsNotNone(seq_data)
        self.assertEqual(len(seq_data), 2)
        self.assertEqual(seq_data.get_sequence_by_id("seq1").sequence, "ATGCATGCAT")

    def test_load_auto_detect_format(self):
        """Test auto-detection of FASTA format from extension."""
        seq_data = load_sequences(self.fasta_file) # No format specified
        self.assertIsNotNone(seq_data)
        self.assertEqual(len(seq_data), 3)
        self.assertTrue("seq1" in seq_data)

    def test_load_non_existent_file(self):
        """Test loading a non-existent file."""
        seq_data = load_sequences("non_existent_file.fasta", "fasta")
        self.assertIsNone(seq_data)

    def test_load_malformed_fasta(self):
        """Test loading a malformed FASTA file."""
        malformed_fasta_content = ">seq1\nATGC\n>seq2\nAGTC\nseq3\nTTTT" # Missing '>' for seq3
        malformed_file = self._create_temp_file("malformed.fasta", malformed_fasta_content)
        seq_data = load_sequences(malformed_file, "fasta")
        # Depending on parser strictness, it might load some or none.
        # Biopython's SeqIO.parse for FASTA is quite lenient and might load seq1 and seq2.
        # The current implementation of load_sequences continues on add_sequence failure.
        # Let's check if it loaded at least the valid ones.
        if seq_data is not None: # If it returns None, that's also acceptable for severe malformation
            self.assertIn(len(seq_data), [0,2]) # Could be 0 if error is fatal, or 2 if it parses what it can
        # For this specific malformation, Biopython FASTA parser might actually parse seq1 and seq2,
        # and then the third entry would be misread or cause an error that our wrapper catches.
        # The goal is it doesn't crash and returns None or partial data with warnings.
        # Current file_parser.py logs warnings and returns data if any was added.
        # If the error occurs during SeqIO.parse itself before any records are processed, it returns None.

    # --- Sequence Writing Tests ---
    def test_write_fasta(self):
        """Test writing sequences to a FASTA file."""
        out_path = os.path.join(self.test_dir.name, "out.fasta")
        success = write_fasta(self.seq_data_instance, out_path)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(out_path))

        # Verify content by reloading
        reloaded_data = load_sequences(out_path, "fasta")
        self.assertIsNotNone(reloaded_data)
        self.assertEqual(len(reloaded_data), len(self.seq_data_instance))
        self.assertEqual(reloaded_data.get_sequence_by_id("seq1").sequence, "ATGC")

    def test_write_phylip(self):
        """Test writing sequences to a PHYLIP file."""
        out_path = os.path.join(self.test_dir.name, "out.phy")
        success = write_phylip(self.seq_data_instance, out_path)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(out_path))
        reloaded_data = load_sequences(out_path, "phylip")
        self.assertIsNotNone(reloaded_data)
        self.assertEqual(len(reloaded_data), len(self.seq_data_instance))
        # PHYLIP IDs might be padded/truncated, Biopython handles this on read/write.
        # 'seq1' is short enough not to be truncated.
        self.assertIsNotNone(reloaded_data.get_sequence_by_id("seq1"))
        self.assertEqual(reloaded_data.get_sequence_by_id("seq1").sequence, "ATGC")

    def test_write_nexus(self):
        """Test writing sequences to a NEXUS file."""
        out_path = os.path.join(self.test_dir.name, "out.nex")
        success = write_nexus(self.seq_data_instance, out_path)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(out_path))
        reloaded_data = load_sequences(out_path, "nexus")
        self.assertIsNotNone(reloaded_data)
        self.assertEqual(len(reloaded_data), len(self.seq_data_instance))
        self.assertEqual(reloaded_data.get_sequence_by_id("seq1").sequence, "ATGC")


    # --- Tree Parsing and Writing Tests ---
    def test_parse_newick(self):
        """Test parsing a Newick tree file."""
        self.assertIsNotNone(self.tree_instance, "Tree instance should have been created in setUp")
        tree = parse_newick(self.newick_file)
        self.assertIsNotNone(tree)
        self.assertEqual(tree.count_terminals(), 3)
        self.assertTrue(any(c.name == "seq1" for c in tree.get_terminals()))

    def test_write_newick(self):
        """Test writing a Biopython Tree object to a Newick file."""
        self.assertIsNotNone(self.tree_instance, "Tree instance should have been created in setUp")
        out_path = os.path.join(self.test_dir.name, "out.nwk")
        success = write_newick(self.tree_instance, out_path)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(out_path))

        reloaded_tree = parse_newick(out_path)
        self.assertIsNotNone(reloaded_tree)
        self.assertEqual(reloaded_tree.count_terminals(), self.tree_instance.count_terminals())

    def test_parse_malformed_newick(self):
        """Test parsing a malformed Newick file."""
        malformed_newick = "((A,B),C;" # Missing closing parenthesis for root
        malformed_file = self._create_temp_file("malformed.nwk", malformed_newick)
        tree = parse_newick(malformed_file)
        self.assertIsNone(tree) # Phylo.read should raise an error, and our wrapper returns None

if __name__ == '__main__':
    unittest.main()
