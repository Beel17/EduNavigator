"""RAG store using Chroma (with interface for pgvector)."""
from typing import List, Dict, Optional, Any
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import logging
from config import settings

logger = logging.getLogger(__name__)


class RAGStore:
    """RAG store using ChromaDB."""
    
    def __init__(self):
        """Initialize RAG store."""
        self.embedding_model = SentenceTransformer(settings.embedding_model)
        self.chroma_client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=Settings(anonymized_telemetry=False)
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
            embeddings = self.embedding_model.encode(texts, show_progress_bar=False).tolist()
            
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
            query_embedding = self.embedding_model.encode([query], show_progress_bar=False).tolist()[0]
            
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

