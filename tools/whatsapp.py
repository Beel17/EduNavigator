"""WhatsApp messaging abstraction for Meta and Twilio providers."""
import logging
from typing import Optional, List

import requests

from config import settings

logger = logging.getLogger(__name__)

try:
    from twilio.rest import Client as TwilioClient
    from twilio.base.exceptions import TwilioException
except ImportError:  # pragma: no cover - twilio optional for meta deployments
    TwilioClient = None  # type: ignore
    TwilioException = Exception  # type: ignore


class BaseWhatsAppSender:
    """Base WhatsApp sender."""

    def send_text(self, to: str, message: str) -> bool:  # pragma: no cover - abstract
        raise NotImplementedError

    def send_document(self, to: str, document_path: str, caption: Optional[str] = None) -> bool:
        logger.warning("Document sending not implemented for this provider")
        return False

    def send_digest(self, to: str, items: List[dict]) -> bool:
        if not items:
            logger.warning("Attempted to send digest with no items to %s", to)
            return False

        message_lines = []
        for i, item in enumerate(items[:3], 1):
            line = f"{i}) {item.get('title', 'Untitled')}"
            if item.get("deadline"):
                line += f" — Deadline: {item['deadline']}"
            line += f"\n   Action: {item.get('action', 'See details')}"
            line += f"\n   {item.get('url', '')}\n"
            message_lines.append(line)

        message_lines.append("\nReply 1/2/3 for full one-pager + calendar invite.")
        message = "\n".join(message_lines)
        logger.info("Digest message content (%d chars): %s", len(message), message[:200])
        return self.send_text(to, message)
    
    def send_proposal_text(self, to: str, proposal_text: str, opportunity_title: str) -> bool:
        """
        Send proposal as text message.
        
        Args:
            to: Recipient WhatsApp number
            proposal_text: Proposal text content
            opportunity_title: Opportunity title for logging
        
        Returns:
            Success status
        """
        # WhatsApp has a message length limit (4096 characters)
        # Split long proposals into multiple messages if needed
        max_length = 4000  # Leave some buffer
        
        if len(proposal_text) <= max_length:
            return self.send_text(to, proposal_text)
        
        # Split into chunks
        chunks = []
        lines = proposal_text.split('\n')
        current_chunk = []
        current_length = 0
        
        for line in lines:
            line_length = len(line) + 1  # +1 for newline
            if current_length + line_length > max_length and current_chunk:
                chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
                current_length = line_length
            else:
                current_chunk.append(line)
                current_length += line_length
        
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        # Send all chunks
        success = True
        for i, chunk in enumerate(chunks, 1):
            if len(chunks) > 1:
                header = f"📄 *Proposal Part {i}/{len(chunks)}*\n\n"
                chunk = header + chunk
            
            if not self.send_text(to, chunk):
                success = False
                logger.warning(f"Failed to send proposal chunk {i}/{len(chunks)} to {to}")
        
        if success:
            logger.info(f"Sent proposal text for '{opportunity_title}' to {to} ({len(chunks)} parts)")
        
        return success


class MetaWhatsAppSender(BaseWhatsAppSender):
    """WhatsApp message sender using Meta Cloud API."""

    def __init__(self):
        self.access_token = settings.whatsapp_access_token
        self.phone_number_id = settings.whatsapp_phone_number_id
        self.api_version = settings.whatsapp_api_version
        self.base_url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/messages"

    def send_text(self, to: str, message: str) -> bool:
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }

            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "text",
                "text": {"body": message},
            }

            response = requests.post(self.base_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()

            logger.info("Sent Meta WhatsApp message to %s", to)
            return True
        except Exception as exc:  # pragma: no cover - network errors
            logger.error("Error sending Meta WhatsApp message: %s", exc)
            return False

    def send_document(self, to: str, document_path: str, caption: Optional[str] = None) -> bool:
        try:
            upload_url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/media"
            headers = {"Authorization": f"Bearer {self.access_token}"}

            with open(document_path, "rb") as file:
                files = {"file": file}
                data = {"messaging_product": "whatsapp", "type": "document"}
                if caption:
                    data["caption"] = caption

                response = requests.post(upload_url, files=files, data=data, headers=headers, timeout=60)
                response.raise_for_status()
                media_id = response.json()["id"]

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "document",
                "document": {"id": media_id},
            }

            response = requests.post(self.base_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()

            logger.info("Sent Meta WhatsApp document to %s", to)
            return True
        except Exception as exc:  # pragma: no cover - network errors
            logger.error("Error sending Meta WhatsApp document: %s", exc)
            return False


class TwilioWhatsAppSender(BaseWhatsAppSender):
    """WhatsApp sender using Twilio Programmable Messaging."""

    def __init__(self):
        if not TwilioClient:
            raise ImportError("twilio package is required for Twilio WhatsApp provider")

        if not all(
            [
                settings.twilio_account_sid,
                settings.twilio_auth_token,
                settings.twilio_whatsapp_number,
            ]
        ):
            raise ValueError("Twilio WhatsApp configuration is incomplete")

        self.client = TwilioClient(settings.twilio_account_sid, settings.twilio_auth_token)
        self.from_number = self._format_number(settings.twilio_whatsapp_number)

    @staticmethod
    def _format_number(number: str) -> str:
        formatted = (number or "").strip()
        formatted = formatted.replace("whatsapp://", "")
        formatted = formatted.replace("whatsapp:", "")
        formatted = formatted.replace("whatsapp", "")
        formatted = formatted.replace(":", "")
        formatted = formatted.strip()
        formatted = formatted.lstrip("+")
        if not formatted:
            raise ValueError("Invalid WhatsApp number")
        return f"whatsapp:+{formatted}"

    def send_text(self, to: str, message: str) -> bool:
        try:
            formatted_to = self._format_number(to)
            logger.debug("Sending Twilio message to %s (from %s): %s", 
                        formatted_to, self.from_number, message[:100])
            result = self.client.messages.create(from_=self.from_number, to=formatted_to, body=message)
            logger.info("Sent Twilio WhatsApp message to %s (SID: %s, Status: %s)", 
                       formatted_to, result.sid, result.status)
            return True
        except TwilioException as exc:  # pragma: no cover - network errors
            logger.error("Error sending Twilio WhatsApp message to %s: %s", to, exc, exc_info=True)
            return False

    def send_document(self, to: str, document_path: str, caption: Optional[str] = None) -> bool:
        logger.warning(
            "Twilio WhatsApp sender cannot send local documents directly. Sending fallback notification."
        )
        fallback_message = caption or "A document is available. Please check your email for details."
        return self.send_text(to, fallback_message)


def get_whatsapp_sender() -> BaseWhatsAppSender:
    """Return the configured WhatsApp sender."""
    provider = (settings.whatsapp_provider or "meta").lower()

    if provider == "twilio":
        return TwilioWhatsAppSender()

    if provider != "meta":
        logger.warning("Unknown WhatsApp provider '%s', defaulting to Meta", provider)

    return MetaWhatsAppSender()

