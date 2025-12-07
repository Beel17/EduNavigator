"""Document ingestion pipeline."""
import logging
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from database.models import Source, Document, DocVersion, Change, Opportunity, Subscriber
from database.session import SessionLocal
from tools.schemas import CrawlOut
from dedupe.dedupe import Deduper
from rag.store import RAGStore
from rag.chunker import chunk_text
from agents.change_detector import ChangeDetector
from agents.opportunity_extractor import OpportunityExtractor
from agents.proposal_writer import ProposalWriter
from tools.whatsapp import get_whatsapp_sender, BaseWhatsAppSender
from config import settings

logger = logging.getLogger(__name__)


class Ingester:
    """Document ingestion pipeline."""
    
    def __init__(self, db: Optional[Session] = None):
        """Initialize ingester."""
        self.db = db or SessionLocal()
        self.deduper = Deduper()
        self.rag_store = RAGStore()
        self.change_detector = ChangeDetector()
        self.opportunity_extractor = OpportunityExtractor()
        self.proposal_writer = ProposalWriter()
        self.whatsapp_sender: BaseWhatsAppSender = get_whatsapp_sender()
    
    def ingest(self, source_id: int, crawl_results: List[CrawlOut]) -> int:
        """
        Ingest crawled documents.
        
        Args:
            source_id: Source ID
            crawl_results: Crawled documents
        
        Returns:
            Number of documents ingested
        """
        ingested_count = 0
        
        for crawl_result in crawl_results:
            try:
                # Check for duplicates
                is_duplicate, exact_hash, _ = self.deduper.is_duplicate(crawl_result.raw_text or "")
                
                if is_duplicate:
                    logger.info(f"Skipping duplicate document: {crawl_result.url}")
                    continue
                
                # Check if document exists with same hash
                existing_doc = self.db.query(Document).filter(
                    Document.http_hash == crawl_result.http_hash,
                    Document.url == crawl_result.url
                ).first()
                
                if existing_doc:
                    # Check if content changed
                    latest_version = self.db.query(DocVersion).filter(
                        DocVersion.doc_id == existing_doc.id
                    ).order_by(DocVersion.version.desc()).first()
                    
                    if latest_version and latest_version.text == (crawl_result.raw_text or ""):
                        logger.info(f"Document unchanged: {crawl_result.url}")
                        continue
                    
                    # Create new version
                    new_version_num = (latest_version.version if latest_version else 0) + 1
                    new_version = DocVersion(
                        doc_id=existing_doc.id,
                        version=new_version_num,
                        text=crawl_result.raw_text or ""
                    )
                    self.db.add(new_version)
                    
                    # Detect changes
                    old_text = latest_version.text if latest_version else ""
                    change_summary = self.change_detector.detect_changes(
                        url=crawl_result.url,
                        fetched_at=crawl_result.fetched_at,
                        old_text=old_text,
                        new_text=crawl_result.raw_text or ""
                    )
                    
                    if change_summary.what_changed:
                        change = Change(
                            doc_id=existing_doc.id,
                            old_version=(latest_version.version if latest_version else 0),
                            new_version=new_version_num,
                            summary_json=change_summary.model_dump_json()
                        )
                        self.db.add(change)
                    
                    # Update document
                    existing_doc.fetched_at = datetime.fromisoformat(crawl_result.fetched_at.replace('Z', '+00:00'))
                    existing_doc.http_hash = crawl_result.http_hash
                    existing_doc.raw_text = crawl_result.raw_text
                    
                    doc = existing_doc
                else:
                    # Create new document
                    doc = Document(
                        source_id=source_id,
                        url=crawl_result.url,
                        title=crawl_result.title,
                        fetched_at=datetime.fromisoformat(crawl_result.fetched_at.replace('Z', '+00:00')),
                        http_hash=crawl_result.http_hash,
                        mime=crawl_result.mime,
                        raw_text=crawl_result.raw_text
                    )
                    self.db.add(doc)
                    self.db.flush()
                    
                    # Create initial version
                    version = DocVersion(
                        doc_id=doc.id,
                        version=1,
                        text=crawl_result.raw_text or ""
                    )
                    self.db.add(version)
                
                # Extract opportunities
                opportunities = self.opportunity_extractor.extract_opportunities(
                    url=crawl_result.url,
                    title=crawl_result.title,
                    text=crawl_result.raw_text or ""
                )
                
                for opp in opportunities:
                    if opp.title and opp.url:
                        # Parse deadline if present
                        deadline = None
                        if opp.deadline:
                            try:
                                deadline = datetime.fromisoformat(opp.deadline.replace('Z', '+00:00'))
                            except Exception:
                                pass
                        
                        opportunity = Opportunity(
                            doc_id=doc.id,
                            title=opp.title,
                            deadline=deadline,
                            eligibility=opp.eligibility,
                            amount=opp.amount,
                            agency=opp.agency,
                            url=opp.url,
                            score=0.0  # Can be updated by ranking
                        )
                        self.db.add(opportunity)
                        self.db.flush()  # Flush to get opportunity.id
                        
                        # Automatically generate and send proposal to active subscribers
                        if settings.enable_auto_proposal_sending:
                            try:
                                self._send_proposal_to_subscribers(opportunity, doc)
                            except Exception as e:
                                logger.error(f"Error sending proposal for opportunity {opp.title}: {e}", exc_info=True)
                
                # Chunk and add to RAG store
                if crawl_result.raw_text:
                    chunks = chunk_text(
                        text=crawl_result.raw_text,
                        url=crawl_result.url,
                        title=crawl_result.title
                    )
                    if chunks:
                        self.rag_store.add_documents(chunks)
                
                ingested_count += 1
                logger.info(f"Ingested document: {crawl_result.url}")
                
            except Exception as e:
                logger.error(f"Error ingesting document {crawl_result.url}: {e}")
                continue
        
        try:
            self.db.commit()
            logger.info(f"Ingested {ingested_count} documents")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error committing ingestion: {e}")
            raise
        
        return ingested_count
    
    def _send_proposal_to_subscribers(self, opportunity: Opportunity, document: Document):
        """
        Generate and send proposal text to all active subscribers.
        
        Args:
            opportunity: The opportunity for which to generate proposal
            document: The source document
        """
        try:
            # Get active subscribers
            subscribers = self.db.query(Subscriber).filter(
                Subscriber.active == True,
                Subscriber.channel == "whatsapp"
            ).all()
            
            if not subscribers:
                logger.debug("No active subscribers to send proposal to")
                return
            
            # Get RAG chunks for the opportunity
            chunks = self.rag_store.query(opportunity.title, top_k=5)
            
            # Fallback: if no RAG chunks found, create chunks from document text
            if not chunks and document.raw_text:
                logger.info(f"No RAG chunks found, creating chunks from document text for: {opportunity.title}")
                chunks_from_doc = chunk_text(
                    text=document.raw_text,
                    url=document.url,
                    title=document.title
                )
                # Convert chunk format to match RAG query results
                chunks = [
                    {
                        "text": chunk.get("text", ""),
                        "url": chunk.get("url", document.url),
                        "title": chunk.get("title", document.title),
                        "heading": chunk.get("heading", ""),
                        "metadata": {}
                    }
                    for chunk in chunks_from_doc[:5]  # Limit to top 5
                ]
            
            if not chunks:
                logger.warning(f"No chunks available for proposal generation: {opportunity.title}")
                return
            
            # Generate proposal text
            deadline_str = opportunity.deadline.isoformat() if opportunity.deadline else None
            proposal_text = self.proposal_writer.generate_proposal_text(
                opportunity_title=opportunity.title,
                agency=opportunity.agency,
                deadline=deadline_str,
                amount=opportunity.amount,
                chunks=chunks
            )
            
            # Send to all active subscribers
            sent_count = 0
            for subscriber in subscribers:
                try:
                    success = self.whatsapp_sender.send_proposal_text(
                        to=subscriber.handle,
                        proposal_text=proposal_text,
                        opportunity_title=opportunity.title
                    )
                    if success:
                        sent_count += 1
                        logger.info(f"Sent proposal for '{opportunity.title}' to subscriber {subscriber.handle}")
                    else:
                        logger.warning(f"Failed to send proposal to subscriber {subscriber.handle}")
                except Exception as e:
                    logger.error(f"Error sending proposal to subscriber {subscriber.handle}: {e}", exc_info=True)
            
            logger.info(f"Sent proposal for '{opportunity.title}' to {sent_count}/{len(subscribers)} subscribers")
            
        except Exception as e:
            logger.error(f"Error in _send_proposal_to_subscribers: {e}", exc_info=True)
            raise

