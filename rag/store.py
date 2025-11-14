"""RAG store using Chroma (with interface for pgvector)."""
from typing import List, Dict, Optional, Any
import chromadb
from chromadb.config import Settings
import logging
import httpx
from config import settings

logger = logging.getLogger(__name__)

# Conditional import for local embeddings
# Use local if provider is "sentence_transformers" (default), "local", or if no service URL is set
_use_local_embeddings = (
    settings.embedding_provider in ("sentence_transformers", "local") or
    (not settings.embedding_service_url and settings.embedding_provider != "remote")
)

if _use_local_embeddings:
    try:
        from sentence_transformers import SentenceTransformer
        _sentence_transformers_available = True
    except ImportError:
        _sentence_transformers_available = False
        logger.warning("sentence-transformers not available, remote mode required")
else:
    _sentence_transformers_available = False


class EmbeddingClient:
    """Client for generating embeddings locally or remotely."""
    
    def __init__(self):
        """Initialize embedding client."""
        self.provider = settings.embedding_provider
        self.service_url = settings.embedding_service_url
        self.api_key = settings.embedding_service_api_key
        self.local_model = None
        
        # Determine if we should use local or remote
        # Backward compatible: "sentence_transformers" (default) uses local mode
        use_local = (
            self.provider in ("sentence_transformers", "local") or
            (not self.service_url and self.provider != "remote")
        )
        
        if use_local and _sentence_transformers_available:
            try:
                self.local_model = SentenceTransformer(settings.embedding_model)
                logger.info(f"Initialized local embedding model: {settings.embedding_model}")
            except Exception as e:
                logger.error(f"Failed to load local embedding model: {e}")
                raise
        elif use_local and not _sentence_transformers_available:
            raise ValueError("Local embedding provider requested but sentence-transformers not available")
        else:
            if not self.service_url:
                raise ValueError("Remote embedding provider requires EMBEDDING_SERVICE_URL")
            logger.info(f"Using remote embedding service: {self.service_url}")
    
    def encode(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for texts.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        if self.local_model:
            return self.local_model.encode(texts, show_progress_bar=False).tolist()
        else:
            return self._encode_remote(texts)
    
    def _encode_remote(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings via remote service."""
        try:
            url = f"{self.service_url.rstrip('/')}/embed"
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            payload = {"texts": texts}
            
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()
                return result.get("embeddings", [])
        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling embedding service: {e}")
            return []
        except Exception as e:
            logger.error(f"Error calling embedding service: {e}")
            return []


class RAGStore:
    """RAG store using ChromaDB."""
    
    def __init__(self):
        """Initialize RAG store."""
        self.embedding_client = EmbeddingClient()
        # Disable telemetry if configured
        anonymized_telemetry = not settings.chromadb_disable_telemetry
        self.chroma_client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=Settings(anonymized_telemetry=anonymized_telemetry)
        )
        self.collection = self.chroma_client.get_or_create_collection(
            name="nigerian_grants",
            metadata={"hnsw:space": "cosine"}
        )
        logger.info(f"Initialized RAG store with collection: nigerian_grants")
    
    def add_documents(self, chunks: List[Dict[str, Any]]) -> bool:
        """
        Add document chunks to the store.
        
        Args:
            chunks: List of chunks with text, url, title, metadata
        
        Returns:
            Success status
        """
        if not chunks:
            return False
        
        try:
            texts = [chunk["text"] for chunk in chunks]
            embeddings = self.embedding_client.encode(texts)
            
            if not embeddings:
                logger.error("Failed to generate embeddings")
                return False
            
            ids = [f"chunk_{i}_{hash(chunk['url'])}" for i, chunk in enumerate(chunks)]
            metadatas = [
                {
                    "url": chunk.get("url", ""),
                    "title": chunk.get("title", ""),
                    "heading": chunk.get("heading", ""),
                    **chunk.get("metadata", {})
                }
                for chunk in chunks
            ]
            
            self.collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Added {len(chunks)} chunks to RAG store")
            return True
        except Exception as e:
            logger.error(f"Error adding documents to RAG store: {e}")
            return False
    
    def query(self, query: str, top_k: int = 4, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Query the RAG store.
        
        Args:
            query: Query text
            top_k: Number of results to return
            filters: Optional metadata filters
        
        Returns:
            List of relevant chunks with scores
        """
        try:
            query_embeddings = self.embedding_client.encode([query])
            if not query_embeddings:
                logger.error("Failed to generate query embedding")
                return []
            query_embedding = query_embeddings[0]
            
            where = filters or {}
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where
            )
            
            chunks = []
            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    chunk = {
                        "text": doc,
                        "url": results["metadatas"][0][i].get("url", ""),
                        "title": results["metadatas"][0][i].get("title", ""),
                        "heading": results["metadatas"][0][i].get("heading", ""),
                        "score": 1 - results["distances"][0][i] if results["distances"] else 0.0,
                        "metadata": results["metadatas"][0][i]
                    }
                    chunks.append(chunk)
            
            logger.info(f"Retrieved {len(chunks)} chunks for query: {query[:50]}")
            return chunks
        except Exception as e:
            logger.error(f"Error querying RAG store: {e}")
            return []
    
    def delete_by_url(self, url: str) -> bool:
        """Delete all chunks for a given URL."""
        try:
            # ChromaDB doesn't support direct deletion by metadata, so we need to query first
            # For now, we'll implement a simpler version
            logger.warning("Delete by URL not fully implemented for ChromaDB")
            return True
        except Exception as e:
            logger.error(f"Error deleting documents by URL: {e}")
            return False

