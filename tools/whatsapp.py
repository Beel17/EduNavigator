"""WhatsApp Cloud API integration."""
import requests
import logging
from typing import Optional, List
from config import settings

logger = logging.getLogger(__name__)


class WhatsAppSender:
    """WhatsApp message sender using Cloud API."""
    
    def __init__(self):
        """Initialize WhatsApp sender."""
        self.access_token = settings.whatsapp_access_token
        self.phone_number_id = settings.whatsapp_phone_number_id
        self.api_version = settings.whatsapp_api_version
        self.base_url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/messages"
    
    def send_text(self, to: str, message: str) -> bool:
        """
        Send text message.
        
        Args:
            to: Recipient phone number (with country code, no +)
            message: Message text
        
        Returns:
            Success status
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "text",
                "text": {
                    "body": message
                }
            }
            
            response = requests.post(self.base_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            logger.info(f"Sent WhatsApp message to {to}")
            return True
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {e}")
            return False
    
    def send_document(self, to: str, document_path: str, caption: Optional[str] = None) -> bool:
        """
        Send document (PDF, etc.).
        
        Args:
            to: Recipient phone number
            document_path: Path to document file
            caption: Optional caption
        
        Returns:
            Success status
        """
        try:
            # First upload media
            upload_url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/media"
            
            headers = {
                "Authorization": f"Bearer {self.access_token}"
            }
            
            with open(document_path, "rb") as file:
                files = {"file": file}
                data = {
                    "messaging_product": "whatsapp",
                    "type": "document"
                }
                if caption:
                    data["caption"] = caption
                
                response = requests.post(upload_url, files=files, data=data, headers=headers, timeout=60)
                response.raise_for_status()
                media_id = response.json()["id"]
            
            # Send message with media
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "document",
                "document": {
                    "id": media_id
                }
            }
            
            response = requests.post(self.base_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            logger.info(f"Sent WhatsApp document to {to}")
            return True
        except Exception as e:
            logger.error(f"Error sending WhatsApp document: {e}")
            return False
    
    def send_digest(self, to: str, items: List[dict]) -> bool:
        """
        Send digest message with numbered items.
        
        Args:
            to: Recipient phone number
            items: List of digest items with title, action, deadline, url
        
        Returns:
            Success status
        """
        if not items:
            return False
        
        message_lines = []
        for i, item in enumerate(items[:3], 1):  # Top 3 items
            line = f"{i}) {item.get('title', 'Untitled')}"
            if item.get('deadline'):
                line += f" — Deadline: {item['deadline']}"
            line += f"\n   Action: {item.get('action', 'See details')}"
            line += f"\n   {item.get('url', '')}\n"
            message_lines.append(line)
        
        message_lines.append("\nReply 1/2/3 for full one-pager + calendar invite.")
        
        message = "\n".join(message_lines)
        return self.send_text(to, message)

