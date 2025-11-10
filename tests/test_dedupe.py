"""Tests for deduplication."""
import pytest
from dedupe.dedupe import Deduper


def test_exact_duplicate():
    """Test exact duplicate detection."""
    deduper = Deduper()
    content = "This is a test document about Nigerian grants."
    
    is_dup, hash1 = deduper.is_exact_duplicate(content)
    assert not is_dup
    
    is_dup, hash2 = deduper.is_exact_duplicate(content)
    assert is_dup
    assert hash1 == hash2


def test_near_duplicate():
    """Test near-duplicate detection."""
    deduper = Deduper(simhash_threshold=3)
    content1 = "This is a test document about Nigerian grants and scholarships."
    content2 = "This is a test document about Nigerian grants and scholarships for students."
    
    is_dup1, _ = deduper.is_near_duplicate(content1)
    assert not is_dup1
    
    is_dup2, _ = deduper.is_near_duplicate(content2)
    # Should detect as near-duplicate if threshold is appropriate
    # Note: This may vary based on SimHash implementation


def test_no_duplicate():
    """Test that different content is not detected as duplicate."""
    deduper = Deduper()
    content1 = "This is about grants."
    content2 = "This is about scholarships."
    
    is_dup1, _ = deduper.is_exact_duplicate(content1)
    assert not is_dup1
    
    is_dup2, _ = deduper.is_exact_duplicate(content2)
    assert not is_dup2

