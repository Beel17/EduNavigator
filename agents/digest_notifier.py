"""Digest notifier agent."""
import logging
from typing import List, Dict
from sqlalchemy.orm import Session
from database.models import Opportunity, Subscriber
from tools.whatsapp import get_whatsapp_sender, BaseWhatsAppSender
from tools.schemas import DigestItem
from datetime import datetime

logger = logging.getLogger(__name__)


class DigestNotifier:
    """Agent for sending digest notifications."""
    
    def __init__(self, db: Session):
        """Initialize digest notifier."""
        self.db = db
        self.whatsapp_sender: BaseWhatsAppSender = get_whatsapp_sender()
    
    def get_digest_items(self, limit: int = 3) -> List[DigestItem]:
        """
        Get digest items (top opportunities).
        
        Args:
            limit: Number of items to return
        
        Returns:
            List of digest items
        """
        try:
            opportunities = self.db.query(Opportunity).filter(
                Opportunity.deadline >= datetime.utcnow()
            ).order_by(
                Opportunity.score.desc(),
                Opportunity.deadline.asc()
            ).limit(limit).all()
            
            items = []
            for opp in opportunities:
                items.append(DigestItem(
                    title=opp.title,
                    action="See details and apply",
                    deadline=opp.deadline.isoformat() if opp.deadline else None,
                    url=opp.url,
                    opportunity_id=opp.id
                ))
            
            return items
        except Exception as e:
            logger.error(f"Error getting digest items: {e}")
            return []
    
    def send_digest(self, subscriber_handle: str) -> bool:
        """
        Send digest to subscriber.
        
        Args:
            subscriber_handle: Subscriber WhatsApp number
        
        Returns:
            Success status
        """
        try:
            items = self.get_digest_items(limit=3)
            if not items:
                self.whatsapp_sender.send_text(
                    subscriber_handle,
                    "No new opportunities available at the moment. Check back later!"
                )
                return True
            
            # Convert to dict for WhatsApp sender
            items_dict = [item.model_dump() for item in items]
            return self.whatsapp_sender.send_digest(subscriber_handle, items_dict)
        except Exception as e:
            logger.error(f"Error sending digest to {subscriber_handle}: {e}")
            return False

