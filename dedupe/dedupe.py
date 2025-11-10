"""Deduplication module for exact and near-duplicate detection."""
import hashlib
from typing import Optional, Set
from simhash import Simhash
import logging

logger = logging.getLogger(__name__)


class Deduper:
    """Deduplication using exact hash and SimHash for near-duplicates."""
    
    def __init__(self, simhash_threshold: int = 3):
        """
        Initialize deduper.
        
        Args:
            simhash_threshold: Hamming distance threshold for near-duplicates (lower = stricter)
        """
        self.simhash_threshold = simhash_threshold
        self.seen_hashes: Set[str] = set()
        self.seen_simhashes: Set[int] = set()
    
    def is_exact_duplicate(self, content: str) -> tuple[bool, str]:
        """
        Check if content is an exact duplicate.
        
        Returns:
            (is_duplicate, hash)
        """
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        is_duplicate = content_hash in self.seen_hashes
        
        if not is_duplicate:
            self.seen_hashes.add(content_hash)
        
        return is_duplicate, content_hash
    
    def is_near_duplicate(self, content: str) -> tuple[bool, int]:
        """
        Check if content is a near-duplicate using SimHash.
        
        Returns:
            (is_duplicate, simhash_value)
        """
        # Generate SimHash
        simhash_value = Simhash(content).value
        
        # Check against existing SimHashes
        for existing_simhash in self.seen_simhashes:
            distance = Simhash(content).distance(Simhash(value=existing_simhash))
            if distance <= self.simhash_threshold:
                return True, simhash_value
        
        # Not a duplicate, add to set
        self.seen_simhashes.add(simhash_value)
        return False, simhash_value
    
    def is_duplicate(self, content: str) -> tuple[bool, Optional[str], Optional[int]]:
        """
        Check if content is duplicate (exact or near).
        
        Returns:
            (is_duplicate, exact_hash, simhash_value)
        """
        is_exact, exact_hash = self.is_exact_duplicate(content)
        if is_exact:
            return True, exact_hash, None
        
        is_near, simhash_value = self.is_near_duplicate(content)
        if is_near:
            return True, exact_hash, simhash_value
        
        return False, exact_hash, simhash_value
    
    def reset(self):
        """Reset seen hashes (useful for testing)."""
        self.seen_hashes.clear()
        self.seen_simhashes.clear()

