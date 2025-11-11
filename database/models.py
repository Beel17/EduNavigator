"""Database models."""
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, 
    ForeignKey, Float, BLOB, CheckConstraint, Index,LargeBinary
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Source(Base):
    """Source model for crawling targets."""
    __tablename__ = "sources"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    url = Column(Text, nullable=False)
    schedule_cron = Column(String(100), nullable=False, default="0 6 * * *")
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    documents = relationship("Document", back_populates="source")


class Document(Base):
    """Document model for crawled content."""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    url = Column(Text, nullable=False)
    title = Column(String(500), nullable=False)
    fetched_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    http_hash = Column(String(64), nullable=False, index=True)  # SHA256 hash
    mime = Column(String(100), nullable=False)
    raw_text = Column(Text)
    raw_blob = Column(LargeBinary)
    
    source = relationship("Source", back_populates="documents")
    versions = relationship("DocVersion", back_populates="document")
    changes = relationship("Change", back_populates="document")
    opportunities = relationship("Opportunity", back_populates="document")
    
    __table_args__ = (
        Index("idx_url_hash", "url", "http_hash",mysql_length={"url": 255},),
    )


class DocVersion(Base):
    """Document version model for change tracking."""
    __tablename__ = "doc_versions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    document = relationship("Document", back_populates="versions")
    
    __table_args__ = (
        Index("idx_doc_version", "doc_id", "version"),
    )


class Change(Base):
    """Change model for tracking document changes."""
    __tablename__ = "changes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    old_version = Column(Integer, nullable=False)
    new_version = Column(Integer, nullable=False)
    summary_json = Column(Text)  # JSON string of ChangeSummary
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    document = relationship("Document", back_populates="changes")


class Opportunity(Base):
    """Opportunity model for grants/scholarships/policies."""
    __tablename__ = "opportunities"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    title = Column(String(500), nullable=False)
    deadline = Column(DateTime)
    eligibility = Column(Text)
    amount = Column(String(200))
    agency = Column(String(200), nullable=False)
    url = Column(Text, nullable=False)
    score = Column(Float, default=0.0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    document = relationship("Document", back_populates="opportunities")
    proposals = relationship("Proposal", back_populates="opportunity")
    
    __table_args__ = (
        Index("idx_deadline", "deadline"),
        Index("idx_score", "score"),
    )


class Proposal(Base):
    """Proposal model for generated one-pagers."""
    __tablename__ = "proposals"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    opportunity_id = Column(Integer, ForeignKey("opportunities.id"), nullable=False)
    pdf_path = Column(String(500), nullable=False)
    summary = Column(Text)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    opportunity = relationship("Opportunity", back_populates="proposals")


class Subscriber(Base):
    """Subscriber model for WhatsApp users."""
    __tablename__ = "subscribers"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    channel = Column(String(50), nullable=False)
    handle = Column(String(100), nullable=False)  # WhatsApp number
    locale = Column(String(10), default="en", nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        CheckConstraint("channel IN ('whatsapp')", name="check_channel"),
        Index("idx_channel_handle", "channel", "handle"),
    )

