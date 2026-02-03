"""Agent router for handling user queries."""
import logging
from typing import Dict, List, Optional, Any
from agents.llm_client import LLMClient
from rag.store import RAGStore
from tools.schemas import QuoteOut, DigestItem

logger = logging.getLogger(__name__)


def _format_opportunity_for_prompt(opp: Any) -> str:
    """Format a single opportunity (model or dict) for LLM prompt."""
    title = getattr(opp, "title", None) or (opp.get("title") if isinstance(opp, dict) else "")
    url = getattr(opp, "url", None) or (opp.get("url") if isinstance(opp, dict) else "")
    eligibility = getattr(opp, "eligibility", None) or (opp.get("eligibility") if isinstance(opp, dict) else "")
    deadline = getattr(opp, "deadline", None) or (opp.get("deadline") if isinstance(opp, dict) else "")
    if eligibility and len(str(eligibility)) > 200:
        eligibility = str(eligibility)[:200] + "..."
    deadline_str = str(deadline)[:10] if deadline else "Not specified"
    return f"- {title}\n  URL: {url}\n  Eligibility: {eligibility or 'Not specified'}\n  Deadline: {deadline_str}"


class AgentRouter:
    """Router for handling different types of queries."""
    
    def __init__(self, rag_store: Optional[RAGStore] = None, llm_client: Optional[LLMClient] = None):
        """Initialize agent router."""
        self.rag_store = rag_store or RAGStore()
        self.llm_client = llm_client or LLMClient()

    def answer_query_conversational(
        self,
        query: str,
        opportunities: List[Any],
        top_k_rag: int = 4,
        max_reply_chars: int = 1200,
    ) -> Optional[str]:
        """
        Use the LLM to produce one conversational reply that uses RAG context and
        picks the most relevant opportunities (by meaning, not just keywords).
        Returns None if LLM is unavailable or errors.
        """
        if not opportunities:
            return None
        try:
            chunks = self.rag_store.query(query, top_k=top_k_rag)
            context_parts = []
            for i, chunk in enumerate(chunks, 1):
                context_parts.append(f"[{i}] {chunk.get('text', '')}")
                if chunk.get('url'):
                    context_parts.append(f"Source: {chunk['url']}")
            rag_context = "\n\n".join(context_parts) if context_parts else "No specific passages found for this query."

            opportunities_text = "\n\n".join(_format_opportunity_for_prompt(opp) for opp in opportunities)

            system_prompt = """You are a friendly WhatsApp assistant helping users find scholarships, grants, and fellowships. 
Your reply must be conversational and warm. Use the knowledge-base context if it helps answer the question; if not, that's okay.
You will be given a list of opportunities from our database. Pick the 3-5 that are MOST relevant to what the user asked (by meaning and intent, not just keywords). 
For each chosen opportunity, include its title and URL on one line. Keep the whole reply under """ + str(max_reply_chars) + """ characters so it fits WhatsApp.
Do not say "I couldn't find" if we have relevant opportunities—instead, recommend them naturally. Be brief and helpful."""

            user_prompt = f"""User asked: "{query}"

Knowledge-base context:
{rag_context}

Opportunities in our database (pick the most relevant for the user's query):
{opportunities_text}

Write a short, conversational reply. Recommend the best-matching opportunities with their title and URL. Keep under """ + str(max_reply_chars) + """ characters."""

            reply = self.llm_client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.4,
            )
            return (reply or "").strip()[:max_reply_chars] if reply else None
        except Exception as e:
            logger.warning(f"Conversational reply failed, will use fallback: {e}")
            return None

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

