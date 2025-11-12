"""Tests for WhatsApp sender selection."""
from unittest.mock import MagicMock

from config import settings
from tools.whatsapp import (
    get_whatsapp_sender,
    MetaWhatsAppSender,
    TwilioWhatsAppSender,
)


def test_get_whatsapp_sender_meta(monkeypatch):
    """Default provider should return Meta sender."""
    monkeypatch.setattr(settings, "whatsapp_provider", "meta", raising=False)
    sender = get_whatsapp_sender()
    assert isinstance(sender, MetaWhatsAppSender)


def test_get_whatsapp_sender_twilio(monkeypatch):
    """Twilio provider should instantiate Twilio sender."""
    mock_client = MagicMock()

    monkeypatch.setattr(settings, "whatsapp_provider", "twilio", raising=False)
    monkeypatch.setattr(settings, "twilio_account_sid", "AC123456789", raising=False)
    monkeypatch.setattr(settings, "twilio_auth_token", "token", raising=False)
    monkeypatch.setattr(settings, "twilio_whatsapp_number", "whatsapp:+15551234567", raising=False)
    monkeypatch.setattr("tools.whatsapp.TwilioClient", MagicMock(return_value=mock_client))

    sender = get_whatsapp_sender()
    assert isinstance(sender, TwilioWhatsAppSender)

    sender.send_text("15559876543", "hello")
    mock_client.messages.create.assert_called_with(
        from_="whatsapp:+15551234567",
        to="whatsapp:+15559876543",
        body="hello",
    )

