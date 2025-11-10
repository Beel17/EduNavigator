"""Agent router for handling user queries."""
import logging
from typing import Dict, List, Optional
from agents.llm_client import LLMClient
from rag.store import RAGStore
from tools.schemas import QuoteOut, DigestItem

logger = logging.getLogger(__name__)


class AgentRouter:
    """Router for handling different types of queries."""
    
    def __init__(self, rag_store: Optional[RAGStore] = None, llm_client: Optional[LLMClient] = None):
        """Initialize agent router."""
        self.rag_store = rag_store or RAGStore()
        self.llm_client = llm_client or LLMClient()
    
    def answer_query(self, query: str, top_k: int = 4) -> QuoteOut:
        """
        Answer a free-form query using RAG.
        
        Args:
            query: User query
            top_k: Number of chunks to retrieve
        
        Returns:
            QuoteOut with answer and citations
        """
        try:
            # Retrieve relevant chunks
            chunks = self.rag_store.query(query, top_k=top_k)
            
            if not chunks:
                return QuoteOut(
                    answer="I couldn't find relevant information in the knowledge base. Please try rephrasing your query.",
                    citations=[],
                    chunks=[]
                )
            
            # Build context from chunks
            context_parts = []
            citations = []
            for i, chunk in enumerate(chunks, 1):
                context_parts.append(f"[{i}] {chunk.get('text', '')}")
                if chunk.get('url'):
                    citations.append({
                        "url": chunk['url'],
                        "text": chunk.get('title', '') or chunk.get('heading', '') or f"Source {i}"
                    })
            
            context = "\n\n".join(context_parts)
            
            # Generate answer using LLM
            system_prompt = """You are a helpful assistant answering questions about Nigerian grants, scholarships, and education policies. Always ground your answers in the provided context. Include citations in your answer. If information is not available in the context, say "Not specified in source (see citation)." Be concise and factual."""
            
            user_prompt = f"""Query: {query}

Context:
{context}

Provide a clear, concise answer with citations."""
            
            answer = self.llm_client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3
            )
            
            # Format answer with citations
            if citations:
                citation_text = "\n\nCitations:\n"
                for i, citation in enumerate(citations, 1):
                    citation_text += f"[{i}] {citation['text']}: {citation['url']}\n"
                answer += citation_text
            
            return QuoteOut(
                answer=answer,
                citations=citations,
                chunks=chunks
            )
        except Exception as e:
            logger.error(f"Error answering query: {e}")
            return QuoteOut(
                answer=f"Error processing query: {str(e)}",
                citations=[],
                chunks=[]
            )

