"""Intent detection for incoming messages (natural language → digest / proposal / subscribe / query)."""
import re
import logging
from typing import Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class Intent(str, Enum):
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    DIGEST = "digest"
    PROPOSAL = "proposal"
    QUERY = "query"


# Only these single words trigger digest (no "scholarships"/"grants" so "engineering scholarships" stays query)
DIGEST_SHORT = {"digest", "latest", "new", "recent", "list", "top", "grants", "opportunities", "summary"}

# For 2+ word messages: digest only if message contains one of these phrases (not just any word like "scholarships")
# So "engineering scholarships" and "scholarships for Nigerian students" never match → QUERY
DIGEST_REQUEST_PHRASES = [
    "what's new",
    "whats new",
    "any new",
    "any opportunities",
    "show me",
    "send me",
    "get me",
    "give me",
    "list of",
    "top opportunities",
    "latest opportunities",
    "new opportunities",
    "recent opportunities",
    "new grants",
    "latest grants",
    "this week",
    "today",
]

# Proposal: "1", "2", "3", "first", "second", "third", "proposal 1", "proposal for 2", "I want 1", "number 2"
PROPOSAL_NUMBER_PATTERN = re.compile(
    r"\b(?:proposal\s*)?(?:for\s*)?(?:#?\s*)?(1|2|3)\b|"
    r"\b(?:first|second|third|1st|2nd|3rd)\b|"
    r"^(1|2|3)$",
    re.IGNORECASE
)
ORDINAL_TO_NUM = {"first": 1, "1st": 1, "second": 2, "2nd": 2, "third": 3, "3rd": 3}


def _normalize(text: str) -> str:
    """Normalize for matching: lowercase, collapse spaces."""
    return " ".join(text.lower().strip().split())


def _contains_digest_intent(text: str) -> bool:
    normalized = _normalize(text)
    words = normalized.split()
    # Exactly one word: digest only if it's a clear command (digest, latest, grants, etc.)
    # "scholarships" is NOT in DIGEST_SHORT, so "scholarships" alone → query
    if len(words) == 1:
        return words[0] in DIGEST_SHORT
    # Two or more words: digest only if message contains an explicit "give me the digest" phrase
    # "engineering scholarships", "scholarships for Nigerian students" have no such phrase → QUERY
    for phrase in DIGEST_REQUEST_PHRASES:
        if phrase in normalized:
            return True
    return False


def _extract_proposal_number(text: str) -> int | None:
    """Extract 1, 2, or 3 from message. Returns None if not a proposal request."""
    normalized = _normalize(text)
    # Pure digit 1–3
    if normalized in ("1", "2", "3"):
        return int(normalized)
    # Ordinals
    for word in ("first", "second", "third", "1st", "2nd", "3rd"):
        if word in normalized and not re.search(r"\d", normalized.replace("1st", "").replace("2nd", "").replace("3rd", "")):
            return ORDINAL_TO_NUM.get(word)
    # "proposal 1", "proposal for 2", "number 3", "#1", "first", "second", "third", etc.
    for m in PROPOSAL_NUMBER_PATTERN.finditer(text):
        for g in m.groups():
            if g:
                return int(g)
        chunk = m.group(0).lower().strip()
        if chunk in ORDINAL_TO_NUM:
            return ORDINAL_TO_NUM[chunk]
    return None


def detect_intent(message: str) -> Tuple[Intent, int | None]:
    """
    Detect intent from raw message text.

    Returns:
        (Intent, proposal_number or None)
        - proposal_number is 1, 2, or 3 only for Intent.PROPOSAL; else None.
    """
    if not message or not message.strip():
        return Intent.QUERY, None

    text = message.strip()
    upper = text.upper()

    # Unsubscribe
    if upper in ("STOP", "UNSUBSCRIBE", "CANCEL", "OPT OUT"):
        return Intent.UNSUBSCRIBE, None

    # Subscribe
    if upper in ("SUBSCRIBE", "START", "JOIN", "SIGN UP", "SIGNUP", "OPT IN", "HI", "HELLO", "HEY"):
        return Intent.SUBSCRIBE, None
    normalized = _normalize(text)
    if normalized in ("subscribe", "start", "join", "sign up", "signup", "hi", "hello", "hey"):
        return Intent.SUBSCRIBE, None

    # Proposal: must check before digest so "1"/"2"/"3" are proposal
    num = _extract_proposal_number(text)
    if num is not None:
        return Intent.PROPOSAL, num

    # Digest
    if _contains_digest_intent(text):
        return Intent.DIGEST, None

    return Intent.QUERY, None
