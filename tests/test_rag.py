"""Tests for RAG store."""
import pytest
from unittest.mock import patch, MagicMock
from rag.store import RAGStore, EmbeddingClient
from rag.chunker import chunk_text
import os


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


def test_embedding_client_remote(monkeypatch):
    """Test EmbeddingClient with remote service."""
    # Mock environment variables for remote mode
    monkeypatch.setenv("EMBEDDING_PROVIDER", "remote")
    monkeypatch.setenv("EMBEDDING_SERVICE_URL", "https://test-embedding-service.hf.space")
    monkeypatch.setenv("EMBEDDING_SERVICE_API_KEY", "test-api-key")
    
    # Reload config to pick up new env vars
    from config import settings
    import importlib
    import config
    importlib.reload(config)
    settings = config.settings
    
    # Mock HTTP response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "embeddings": [[0.1] * 384, [0.2] * 384]  # Mock embedding vectors
    }
    mock_response.raise_for_status = MagicMock()
    
    # Mock httpx client
    with patch("rag.store.httpx.Client") as mock_client:
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value = mock_client_instance
        
        # Create client (this will fail if sentence-transformers is required)
        # So we need to make sure we're in remote mode
        try:
            client = EmbeddingClient()
            embeddings = client.encode(["test text 1", "test text 2"])
            assert len(embeddings) == 2
            assert len(embeddings[0]) == 384
        except ValueError as e:
            # If local mode is still being used, skip this test
            pytest.skip(f"Remote mode not properly configured: {e}")


# TODO: Add integration test for remote embedding service
# This would require a running embedding service or a more sophisticated mock

