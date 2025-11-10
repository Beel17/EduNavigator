"""Pydantic schemas for tool I/O."""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class CrawlOut(BaseModel):
    """Output schema for crawler."""
    url: str
    title: str
    fetched_at: str
    http_hash: str
    mime: str
    raw_text: Optional[str] = None


class ChangeSummary(BaseModel):
    """Schema for change detection output."""
    what_changed: List[str] = Field(default_factory=list)
    who_is_affected: List[str] = Field(default_factory=list)
    key_dates: List[Dict[str, str]] = Field(default_factory=list)  # [{"label":"deadline","date":"2026-01-15"}]
    required_actions: List[str] = Field(default_factory=list)
    citations: List[Dict[str, str]] = Field(default_factory=list)  # [{"url":"...#section","text":"section title"}]


class OppExtract(BaseModel):
    """Schema for opportunity extraction."""
    title: str
    agency: str
    url: str
    deadline: Optional[str] = None
    eligibility: Optional[str] = None
    amount: Optional[str] = None
    action: str  # 1-line call to action


class QuoteIn(BaseModel):
    """Schema for RAG query input."""
    query: str
    top_k: int = Field(default=4, ge=1, le=20)


class QuoteOut(BaseModel):
    """Schema for RAG query output."""
    answer: str
    citations: List[Dict[str, str]]  # [{"url":"...","text":"..."}]
    chunks: List[Dict[str, Any]]  # Full chunk data


class DigestItem(BaseModel):
    """Schema for digest item."""
    title: str
    action: str
    deadline: Optional[str] = None
    url: str
    opportunity_id: Optional[int] = None


class WhatsAppMessage(BaseModel):
    """Schema for WhatsApp message."""
    from_number: str
    message_text: str
    message_id: str
    timestamp: str


class ProposalRequest(BaseModel):
    """Schema for proposal generation request."""
    opportunity_id: int
    include_ics: bool = True

