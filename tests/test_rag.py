"""Tests for RAG store."""
import pytest
from rag.store import RAGStore
from rag.chunker import chunk_text


def test_chunk_text():
    """Test text chunking."""
    text = """
# Title
This is a test document about Nigerian grants.

## Section 1
This section contains information about eligibility criteria.

## Section 2
This section contains information about deadlines.
"""
    url = "https://example.com/test"
    title = "Test Document"
    
    chunks = chunk_text(text, url, title)
    
    assert len(chunks) > 0
    assert all("text" in chunk for chunk in chunks)
    assert all("url" in chunk for chunk in chunks)
    assert all(chunk["url"] == url for chunk in chunks)


def test_rag_store():
    """Test RAG store operations."""
    rag_store = RAGStore()
    
    # Create test chunks
    chunks = [
        {
            "text": "This is a test document about Nigerian grants.",
            "url": "https://example.com/test",
            "title": "Test Document",
            "heading": None,
            "metadata": {
                "url": "https://example.com/test",
                "title": "Test Document"
            }
        }
    ]
    
    # Add documents
    result = rag_store.add_documents(chunks)
    assert result is True
    
    # Query
    results = rag_store.query("Nigerian grants", top_k=1)
    assert len(results) > 0
    assert "text" in results[0]
    assert "url" in results[0]

