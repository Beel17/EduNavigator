import base64
import hashlib
import hmac
import time
from typing import Optional

from config import settings


def _urlsafe_b64encode_no_padding(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _get_signing_secret() -> bytes:
    secret = (settings.proposal_link_secret or "").strip()
    if not secret:
        secret = settings.secret_key
    return secret.encode("utf-8")


def proposal_download_signature(proposal_id: int, exp: int) -> str:
    """
    Compute an HMAC signature for a proposal download link.

    Token format is: sig = HMAC_SHA256(secret, f"{proposal_id}.{exp}").
    """
    msg = f"{proposal_id}.{exp}".encode("utf-8")
    digest = hmac.new(_get_signing_secret(), msg, hashlib.sha256).digest()
    return _urlsafe_b64encode_no_padding(digest)


def verify_proposal_download_signature(proposal_id: int, exp: int, sig: str) -> bool:
    expected = proposal_download_signature(proposal_id, exp)
    return hmac.compare_digest((sig or "").strip(), expected)


def create_signed_proposal_download_url(proposal_id: int) -> Optional[str]:
    """
    Create a time-limited, signed URL for downloading a proposal PDF.

    Requires `PUBLIC_BASE_URL` to be configured (publicly reachable by users).
    """
    base = (settings.public_base_url or "").strip().rstrip("/")
    if not base:
        return None

    exp = int(time.time()) + int(settings.proposal_link_ttl_seconds)
    sig = proposal_download_signature(proposal_id, exp)
    return f"{base}/proposals/{proposal_id}/download?exp={exp}&sig={sig}"

