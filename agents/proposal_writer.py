"""Proposal writer agent."""
import logging
import re
from typing import List, Dict, Optional
from pathlib import Path
from agents.llm_client import LLMClient
from tools.pdf_generator import generate_proposal_pdf
from config import settings

logger = logging.getLogger(__name__)


class ProposalWriter:
    """Agent for writing proposal one-pagers."""
    
    SYSTEM_PROMPT = """Draft a one-page proposal for Nigerian academia (students/lecturers/research teams). 500–700 words. Sections: Title, Background (problem in Nigeria), Objectives, Activities & 6-month Timeline, Budget Band (low/med/high), Eligibility & Risks, Citations [1..N]. Use the provided passages; if something is missing, say 'Not specified'."""
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        """Initialize proposal writer."""
        self.llm_client = llm_client or LLMClient()
    
    def write_proposal(
        self,
        opportunity_title: str,
        agency: str,
        deadline: Optional[str],
        amount: Optional[str],
        chunks: List[Dict[str, str]]
    ) -> str:
        """
        Write proposal markdown.
        
        Args:
            opportunity_title: Opportunity title
            agency: Agency name
            deadline: Deadline (optional)
            amount: Amount (optional)
            chunks: Relevant RAG chunks
        
        Returns:
            Proposal markdown
        """
        try:
            # Build context from chunks
            context_parts = []
            for i, chunk in enumerate(chunks, 1):
                context_parts.append(f"[{i}] {chunk.get('text', '')}")
                if chunk.get('url'):
                    context_parts.append(f"Source: {chunk['url']}")
                context_parts.append("")
            
            context = "\n".join(context_parts)
            
            user_prompt = f"""Opportunity: {opportunity_title}
Agency: {agency}
Deadline: {deadline or 'Not specified'}
Amount: {amount or 'Not specified'}

Relevant passages:
{context}

Write a comprehensive one-page proposal following the specified format."""
            
            proposal = self.llm_client.generate(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.3
            )
            
            return proposal
        except Exception as e:
            logger.error(f"Error writing proposal: {e}")
            raise
    
    def generate_proposal_pdf(
        self,
        opportunity_title: str,
        agency: str,
        deadline: Optional[str],
        amount: Optional[str],
        chunks: List[Dict[str, str]],
        output_path: Optional[str] = None
    ) -> str:
        """
        Generate proposal PDF.
        
        Args:
            opportunity_title: Opportunity title
            agency: Agency name
            deadline: Deadline (optional)
            amount: Amount (optional)
            chunks: Relevant RAG chunks
            output_path: Output file path
        
        Returns:
            Path to generated PDF
        """
        try:
            # Write proposal
            proposal_markdown = self.write_proposal(
                opportunity_title,
                agency,
                deadline,
                amount,
                chunks
            )
            
            # Generate PDF
            if output_path is None:
                output_path = Path(settings.pdf_storage_dir) / f"{opportunity_title.replace(' ', '_')}_proposal.pdf"
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
            
            pdf_path = generate_proposal_pdf(proposal_markdown, str(output_path))
            
            logger.info(f"Generated proposal PDF: {pdf_path}")
            return pdf_path
        except Exception as e:
            logger.error(f"Error generating proposal PDF: {e}")
            raise
    
    def generate_proposal_text(
        self,
        opportunity_title: str,
        agency: str,
        deadline: Optional[str],
        amount: Optional[str],
        chunks: List[Dict[str, str]]
    ) -> str:
        """
        Generate proposal as plain text (formatted for WhatsApp).
        
        Args:
            opportunity_title: Opportunity title
            agency: Agency name
            deadline: Deadline (optional)
            amount: Amount (optional)
            chunks: Relevant RAG chunks
        
        Returns:
            Proposal as plain text
        """
        try:
            # Write proposal markdown
            proposal_markdown = self.write_proposal(
                opportunity_title,
                agency,
                deadline,
                amount,
                chunks
            )
            
            # Convert markdown to plain text for WhatsApp
            text = self._markdown_to_text(proposal_markdown)
            
            # Add opportunity header
            header = f"📋 *Proposal for: {opportunity_title}*\n"
            header += f"Agency: {agency}\n"
            if deadline:
                header += f"Deadline: {deadline}\n"
            if amount:
                header += f"Amount: {amount}\n"
            header += "\n" + "="*50 + "\n\n"
            
            return header + text
        except Exception as e:
            logger.error(f"Error generating proposal text: {e}")
            raise
    
    @staticmethod
    def _markdown_to_text(markdown_content: str) -> str:
        """
        Convert markdown to plain text suitable for WhatsApp.
        
        Args:
            markdown_content: Markdown text
        
        Returns:
            Plain text
        """
        text = markdown_content
        
        # Remove markdown headers (convert to bold text)
        text = re.sub(r'^#+\s+(.+)$', r'*\1*', text, flags=re.MULTILINE)
        
        # Remove markdown bold/italic markers (keep the text)
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        text = re.sub(r'__([^_]+)__', r'\1', text)
        text = re.sub(r'_([^_]+)_', r'\1', text)
        
        # Remove markdown links but keep the text
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        
        # Remove markdown code blocks
        text = re.sub(r'```[^`]*```', '', text, flags=re.DOTALL)
        text = re.sub(r'`([^`]+)`', r'\1', text)
        
        # Remove markdown list markers (convert to simple bullets)
        text = re.sub(r'^\s*[-*+]\s+', '• ', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
        
        # Clean up multiple blank lines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Trim whitespace
        text = text.strip()
        
        return text

