"""Opportunity extraction agent."""
import json
import logging
from typing import List, Optional
from agents.llm_client import LLMClient
from tools.schemas import OppExtract

logger = logging.getLogger(__name__)


class OpportunityExtractor:
    """Agent for extracting opportunities from documents."""
    
    SYSTEM_PROMPT = """From the NEW content, extract a potential grant/scholarship/policy opportunity. If none, return empty fields. Output OppExtract JSON. Prefer items with deadlines and eligibility.

OppExtract schema:
{
  "title": "Opportunity title",
  "agency": "Agency name",
  "url": "Source URL",
  "deadline": "2026-01-15" or null,
  "eligibility": "Eligibility criteria" or null,
  "amount": "Amount or range" or null,
  "action": "1-line call to action"
}

If no opportunity found, return:
{
  "title": "",
  "agency": "",
  "url": "",
  "deadline": null,
  "eligibility": null,
  "amount": null,
  "action": ""
}"""
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        """Initialize opportunity extractor."""
        self.llm_client = llm_client or LLMClient()
    
    def extract_opportunities(
        self,
        url: str,
        title: str,
        text: str
    ) -> List[OppExtract]:
        """
        Extract opportunities from text.
        
        Args:
            url: Document URL
            title: Document title
            text: Document text
        
        Returns:
            List of extracted opportunities
        """
        opportunities = []
        
        try:
            # Split text into chunks if too long
            max_chunk_size = 4000
            chunks = [text[i:i+max_chunk_size] for i in range(0, len(text), max_chunk_size)]
            
            for chunk in chunks:
                user_prompt = f"""URL: {url}
Title: {title}

Content:
{chunk}
"""
                
                response = self.llm_client.generate_json(
                    system_prompt=self.SYSTEM_PROMPT,
                    user_prompt=user_prompt
                )
                
                # Handle single opportunity or list
                if isinstance(response, dict):
                    opp_data = response
                elif isinstance(response, list):
                    opp_data = response[0] if response else {}
                else:
                    continue
                
                # Validate opportunity
                if opp_data.get("title") and opp_data.get("url"):
                    opp = OppExtract(
                        title=opp_data.get("title", ""),
                        agency=opp_data.get("agency", "Unknown"),
                        url=opp_data.get("url", url),
                        deadline=opp_data.get("deadline"),
                        eligibility=opp_data.get("eligibility"),
                        amount=opp_data.get("amount"),
                        action=opp_data.get("action", "See details")
                    )
                    opportunities.append(opp)
        
        except Exception as e:
            logger.error(f"Error extracting opportunities: {e}")
        
        return opportunities

