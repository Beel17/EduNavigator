"""Change detection agent."""
import json
import logging
from typing import Optional
from agents.llm_client import LLMClient
from tools.schemas import ChangeSummary

logger = logging.getLogger(__name__)


class ChangeDetector:
    """Agent for detecting changes in documents."""
    
    SYSTEM_PROMPT = """You compare OLD vs NEW regulator/funding content. Output only valid JSON per schema ChangeSummary. Be terse, factual, Nigeria-specific, and include citations (URLs with anchors/headings). If no change, set what_changed: [].

ChangeSummary schema:
{
  "what_changed": ["list of what changed"],
  "who_is_affected": ["list of who is affected"],
  "key_dates": [{"label": "deadline", "date": "2026-01-15"}],
  "required_actions": ["list of required actions"],
  "citations": [{"url": "https://...#section", "text": "section title"}]
}"""
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        """Initialize change detector."""
        self.llm_client = llm_client or LLMClient()
    
    def detect_changes(
        self,
        url: str,
        fetched_at: str,
        old_text: Optional[str],
        new_text: str
    ) -> ChangeSummary:
        """
        Detect changes between old and new text.
        
        Args:
            url: Document URL
            fetched_at: Fetch timestamp
            old_text: Old text (None if first version)
            new_text: New text
        
        Returns:
            ChangeSummary
        """
        try:
            if old_text is None or old_text.strip() == "":
                # First version, no changes
                return ChangeSummary(
                    what_changed=[],
                    who_is_affected=[],
                    key_dates=[],
                    required_actions=[],
                    citations=[]
                )
            
            user_prompt = f"""URL: {url}
FETCHED_AT: {fetched_at}

--- OLD ---
{old_text[:4000]}

--- NEW ---
{new_text[:4000]}
"""
            
            response = self.llm_client.generate_json(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=user_prompt
            )
            
            # Ensure citations include URL if not present
            if "citations" in response:
                for citation in response["citations"]:
                    if "url" not in citation or not citation["url"]:
                        citation["url"] = url
            
            return ChangeSummary(**response)
        except Exception as e:
            logger.error(f"Error detecting changes: {e}")
            # Return empty change summary on error
            return ChangeSummary(
                what_changed=[],
                who_is_affected=[],
                key_dates=[],
                required_actions=[],
                citations=[{"url": url, "text": "Error detecting changes"}]
            )

