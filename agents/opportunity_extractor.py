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
}

Respond with a single JSON object only. Do not include any text before or after the JSON."""
    
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
                    logger.debug(f"Unexpected response type from LLM: {type(response)}")
                    continue
                
                # Validate opportunity - relax URL requirement (use provided URL if missing)
                title = opp_data.get("title", "").strip()
                if title:
                    # Use provided URL if model didn't return one
                    opp_url = opp_data.get("url", "").strip() or url
                    
                    opp = OppExtract(
                        title=title,
                        agency=opp_data.get("agency", "Unknown"),
                        url=opp_url,
                        deadline=opp_data.get("deadline"),
                        eligibility=opp_data.get("eligibility"),
                        amount=opp_data.get("amount"),
                        action=opp_data.get("action", "See details")
                    )
                    opportunities.append(opp)
                    logger.info(f"Extracted opportunity: {title} from {url}")
                else:
                    logger.debug(f"Discarded opportunity data (no title): {opp_data}")
        
        except Exception as e:
            logger.error(f"Error extracting opportunities from {url}: {e}", exc_info=True)
            # Log partial response if available for debugging
            if hasattr(e, 'args') and len(e.args) > 0:
                logger.debug(f"Error details: {e.args}")
        
        logger.info(f"Extracted {len(opportunities)} opportunities from {url}")
        return opportunities

