# This module will define core data structures for phylogenetic trees and related data.

import logging
from typing import Optional, List, Dict, Union

logger = logging.getLogger(__name__)

class SequenceRecord:
    """
    Represents a single biological sequence with associated metadata.
    """
    def __init__(self, seq_id: str, sequence: str, internal_id: int, description: Optional[str] = None):
        if not isinstance(seq_id, str) or not seq_id:
            raise ValueError("seq_id must be a non-empty string.")
        if not isinstance(sequence, str):
            raise ValueError("sequence must be a string.")
        if not isinstance(internal_id, int):
            raise ValueError("internal_id must be an integer.")

        self.id: str = seq_id
        self.internal_id: int = internal_id  # Unique numerical ID for tools like RAxML
        self.sequence: str = sequence.upper() # Standardize to uppercase
        self.description: Optional[str] = description if description else f"{seq_id} sequence"
        self.length: int = len(sequence)

    def __repr__(self):
        return f"SequenceRecord(id='{self.id}', internal_id={self.internal_id}, length={self.length})"

    def update_sequence(self, new_sequence: str):
        """Updates the sequence string and its length."""
        if not isinstance(new_sequence, str):
            raise ValueError("New sequence must be a string.")
        self.sequence = new_sequence.upper()
        self.length = len(self.sequence)
        logger.debug(f"Sequence updated for ID: {self.id}")

    def update_id(self, new_id: str):
        """Updates the original sequence identifier."""
        if not isinstance(new_id, str) or not new_id:
            raise ValueError("New ID must be a non-empty string.")
        logger.debug(f"Original ID for internal_id {self.internal_id} changed from '{self.id}' to '{new_id}'")
        self.id = new_id
        if self.description == f"{self.id} sequence" or self.description == f"{new_id} sequence": # Basic auto-description
             self.description = f"{new_id} sequence"


class SequenceData:
    """
    Manages a collection of SequenceRecord objects, including mapping between
    original IDs and internal numerical IDs.
    """
    def __init__(self):
        self._sequences: Dict[str, SequenceRecord] = {}  # Maps original_id to SequenceRecord
        self._internal_id_map: Dict[int, str] = {}      # Maps internal_id to original_id
        self._original_id_to_internal: Dict[str, int] = {} # Maps original_id to internal_id
        self._next_internal_id: int = 1 # RAxML typically expects internal IDs starting from 1

    def add_sequence(self, seq_id: str, sequence: str, description: Optional[str] = None) -> Optional[SequenceRecord]:
        """
        Adds a new sequence to the collection.

        Args:
            seq_id: The original identifier for the sequence.
            sequence: The sequence string.
            description: Optional description for the sequence.

        Returns:
            The created SequenceRecord if successful, None otherwise (e.g., if seq_id already exists).
        """
        if seq_id in self._sequences:
            logger.error(f"Sequence ID '{seq_id}' already exists. Cannot add duplicate.")
            return None
        if not seq_id:
            logger.error("Sequence ID cannot be empty.")
            return None

        internal_id = self._next_internal_id
        self._next_internal_id += 1

        record = SequenceRecord(seq_id=seq_id, sequence=sequence, internal_id=internal_id, description=description)
        
        self._sequences[record.id] = record
        self._internal_id_map[record.internal_id] = record.id
        self._original_id_to_internal[record.id] = record.internal_id
        
        logger.info(f"Added sequence: ID='{record.id}', InternalID={record.internal_id}, Length={record.length}")
        return record

    def get_sequence_by_id(self, seq_id: str) -> Optional[SequenceRecord]:
        """Retrieves a SequenceRecord by its original ID."""
        return self._sequences.get(seq_id)

    def get_sequence_by_internal_id(self, internal_id: int) -> Optional[SequenceRecord]:
        """Retrieves a SequenceRecord by its internal numerical ID."""
        original_id = self._internal_id_map.get(internal_id)
        if original_id:
            return self._sequences.get(original_id)
        return None

    def get_original_id(self, internal_id: int) -> Optional[str]:
        """Retrieves the original sequence ID from an internal numerical ID."""
        return self._internal_id_map.get(internal_id)

    def get_internal_id(self, seq_id: str) -> Optional[int]:
        """Retrieves the internal numerical ID from an original sequence ID."""
        return self._original_id_to_internal.get(seq_id)

    def get_all_sequences(self) -> List[SequenceRecord]:
        """Returns a list of all SequenceRecord objects."""
        return list(self._sequences.values())

    def remove_sequence_by_id(self, seq_id: str) -> bool:
        """
        Removes a sequence from the collection by its original ID.

        Args:
            seq_id: The original ID of the sequence to remove.

        Returns:
            True if removal was successful, False otherwise.
        """
        record = self._sequences.pop(seq_id, None)
        if record:
            del self._internal_id_map[record.internal_id]
            del self._original_id_to_internal[record.id]
            logger.info(f"Removed sequence: ID='{record.id}', InternalID={record.internal_id}")
            # Note: Internal IDs are not reused to maintain uniqueness if needed for external tools
            return True
        logger.warning(f"Sequence ID '{seq_id}' not found for removal.")
        return False

    def update_sequence_id(self, old_id: str, new_id: str) -> bool:
        """
        Updates the original ID of a sequence.

        Args:
            old_id: The current original ID of the sequence.
            new_id: The new original ID to assign.

        Returns:
            True if the update was successful, False otherwise.
        """
        if old_id == new_id:
            logger.info(f"Old ID and new ID are the same ('{old_id}'). No update performed.")
            return True # No change, but not an error
        if new_id in self._sequences:
            logger.error(f"New sequence ID '{new_id}' already exists. Cannot update '{old_id}'.")
            return False
        
        record = self._sequences.get(old_id)
        if record:
            # Update the record itself
            record.update_id(new_id)
            
            # Update keys in internal maps
            self._sequences[new_id] = self._sequences.pop(old_id)
            self._internal_id_map[record.internal_id] = new_id
            self._original_id_to_internal.pop(old_id) # Remove old mapping
            self._original_id_to_internal[new_id] = record.internal_id # Add new mapping
            
            logger.info(f"Updated sequence ID from '{old_id}' to '{new_id}' (InternalID: {record.internal_id}).")
            return True
        logger.warning(f"Sequence ID '{old_id}' not found for ID update.")
        return False

    def update_sequence_data(self, seq_id: str, new_sequence_string: str) -> bool:
        """
        Updates the sequence string for a given sequence ID.

        Args:
            seq_id: The original ID of the sequence to update.
            new_sequence_string: The new sequence data.

        Returns:
            True if update was successful, False otherwise.
        """
        record = self.get_sequence_by_id(seq_id)
        if record:
            record.update_sequence(new_sequence_string)
            logger.info(f"Sequence data updated for ID: '{seq_id}'. New length: {record.length}.")
            return True
        logger.warning(f"Sequence ID '{seq_id}' not found for sequence data update.")
        return False
        
    def __len__(self) -> int:
        """Returns the number of sequences in the collection."""
        return len(self._sequences)

    def __iter__(self):
        """Allows iteration over the SequenceRecord objects."""
        return iter(self._sequences.values())

    def __contains__(self, seq_id: str) -> bool:
        """Checks if a sequence ID is in the collection."""
        return seq_id in self._sequences

if __name__ == '__main__':
    # Example Usage and Basic Tests
    logging.basicConfig(level=logging.DEBUG)

    seq_data = SequenceData()
    rec1 = seq_data.add_sequence("seq1", "ATGCGT", "Sequence 1 from GeneX")
    rec2 = seq_data.add_sequence("seq2", "GATTACA", "Sequence 2 from GeneY")
    seq_data.add_sequence("seq1", "AGGG", "Attempt to add duplicate") # Should fail

    if rec1:
        logger.debug(f"Record 1: {rec1}")
        logger.debug(f"Seq1 internal ID: {seq_data.get_internal_id('seq1')}")
    
    if rec2:
        logger.debug(f"Record 2: {rec2.id}, {rec2.sequence}, {rec2.internal_id}")

    logger.debug(f"All sequences: {seq_data.get_all_sequences()}")
    logger.debug(f"Number of sequences: {len(seq_data)}")

    # Test updates
    seq_data.update_sequence_id("seq1", "seq_one_updated")
    if rec1: # rec1 is a reference to the object, its id attribute should change
         logger.debug(f"Record 1 after ID update: {rec1}") 
    logger.debug(f"Internal ID for seq_one_updated: {seq_data.get_internal_id('seq_one_updated')}")
    logger.debug(f"Original ID for internal ID {rec1.internal_id if rec1 else -1}: {seq_data.get_original_id(rec1.internal_id if rec1 else -1)}")


    seq_data.update_sequence_data("seq_one_updated", "TTTTTTTTTT")
    updated_rec1 = seq_data.get_sequence_by_id("seq_one_updated")
    if updated_rec1:
        logger.debug(f"Updated Record 1 sequence: {updated_rec1.sequence}, length: {updated_rec1.length}")

    # Test removal
    seq_data.remove_sequence_by_id("seq2")
    logger.debug(f"Number of sequences after removal: {len(seq_data)}")
    assert seq_data.get_sequence_by_id("seq2") is None
    assert seq_data.get_internal_id("seq2") is None
    if rec2: # Check original rec2 internal id mapping
        assert seq_data.get_original_id(rec2.internal_id) is None

    # Test adding after removal
    rec3 = seq_data.add_sequence("seq3", "CCCC", "Sequence 3")
    if rec3:
        logger.debug(f"Record 3: {rec3}, expected internal ID { (rec1.internal_id if rec1 else 0) + (1 if seq_data.get_sequence_by_id('seq2') is None else 2) } (actual: {rec3.internal_id})")
        # Note: Expected internal ID depends on whether seq2 was successfully added and then removed.
        # If seq1 was internal_id 1, seq2 was 2, then seq3 should be 3.

    logger.debug("Final state:")
    for seq_record in seq_data:
        logger.debug(f"  {seq_record}")

    assert "seq_one_updated" in seq_data
    assert "seq2" not in seq_data
    assert len(seq_data) == 2 # seq_one_updated and seq3
    
    # Test error handling for SequenceRecord
    try:
        SequenceRecord("", "AGTC", 1)
    except ValueError as e:
        logger.debug(f"Caught expected error for empty ID: {e}")
    try:
        SequenceRecord("test", "AGTC", "not-an-int") # type: ignore
    except ValueError as e:
        logger.debug(f"Caught expected error for non-int internal_id: {e}")

    logger.info("Basic tests for data_structures completed.")
