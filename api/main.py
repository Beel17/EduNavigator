"""FastAPI application."""
import logging
import os
from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import json

from config import settings
from database.session import get_db, init_db
from database.models import Subscriber, Opportunity, Proposal
from tools.whatsapp import get_whatsapp_sender, BaseWhatsAppSender
from agents.router import AgentRouter
from agents.proposal_writer import ProposalWriter
from tools.ics_generator import generate_ics
from datetime import datetime

# Configure logging
logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)

app = FastAPI(title="Nigerian Grants Agent", version="1.0.0")

# Initialize components
whatsapp_sender: BaseWhatsAppSender = get_whatsapp_sender()
agent_router = AgentRouter()
proposal_writer = ProposalWriter()


def normalize_whatsapp_number(number: Optional[str]) -> str:
    """Normalize WhatsApp numbers to digits only."""
    if not number:
        return ""
    normalized = number.replace("whatsapp:", "").replace("whatsapp://", "")
    normalized = normalized.strip()
    normalized = normalized.lstrip("+")
    return normalized


async def process_incoming_message(from_number: str, message_text: str, db: Session) -> None:
    """Process a normalized incoming message."""
    if not from_number or not message_text:
        return

    text_clean = message_text.strip()
    if not text_clean:
        return

    upper_text = text_clean.upper()

    # Handle unsubscribe
    if upper_text in ["STOP", "UNSUBSCRIBE"]:
        subscriber = (
            db.query(Subscriber)
            .filter(Subscriber.handle == from_number, Subscriber.channel == "whatsapp")
            .first()
        )
        if subscriber:
            subscriber.active = False
            db.commit()
            whatsapp_sender.send_text(
                from_number,
                "You have been unsubscribed. Send 'SUBSCRIBE' to resubscribe.",
            )
        return

    # Handle subscribe
    if upper_text in ["SUBSCRIBE", "START"]:
        subscriber = (
            db.query(Subscriber)
            .filter(Subscriber.handle == from_number, Subscriber.channel == "whatsapp")
            .first()
        )
        if not subscriber:
            subscriber = Subscriber(
                channel="whatsapp",
                handle=from_number,
                locale="en",
                active=True,
            )
            db.add(subscriber)
        else:
            subscriber.active = True
        db.commit()
        whatsapp_sender.send_text(
            from_number,
            "Welcome! You are now subscribed. Send 'digest' for weekly digest or ask a question.",
        )
        return

    # Handle digest request
    if text_clean.lower() == "digest":
        await handle_digest_request(from_number, db)
        return

    # Handle numbered proposal request
    if text_clean.isdigit():
        await handle_proposal_request(from_number, int(text_clean), db)
        return

    # Default: treat as general query
    await handle_query(from_number, text_clean, db)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    try:
        init_db()
        logger.info("Application started successfully")
    except Exception as e:
        logger.error(f"Error during startup: {e}")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/debug/opportunities")
async def debug_opportunities(db: Session = Depends(get_db)):
    """Debug endpoint to check opportunities in database."""
    from sqlalchemy import or_, func
    from datetime import datetime
    
    now = datetime.utcnow()
    
    # Get all opportunities
    all_opps = db.query(Opportunity).all()
    
    # Get opportunities matching digest query
    digest_opps = db.query(Opportunity).filter(
        or_(
            Opportunity.deadline >= now,
            Opportunity.deadline.is_(None)
        )
    ).order_by(
        Opportunity.score.desc(),
        Opportunity.deadline.asc().nulls_last()
    ).limit(3).all()
    
    # Get statistics
    total_count = db.query(Opportunity).count()
    with_deadline = db.query(Opportunity).filter(Opportunity.deadline.isnot(None)).count()
    future_deadline = db.query(Opportunity).filter(Opportunity.deadline >= now).count()
    past_deadline = db.query(Opportunity).filter(
        Opportunity.deadline.isnot(None),
        Opportunity.deadline < now
    ).count()
    null_deadline = db.query(Opportunity).filter(Opportunity.deadline.is_(None)).count()
    
    return {
        "total_opportunities": total_count,
        "with_deadline": with_deadline,
        "future_deadline": future_deadline,
        "past_deadline": past_deadline,
        "null_deadline": null_deadline,
        "digest_query_matches": len(digest_opps),
        "all_opportunities": [
            {
                "id": opp.id,
                "title": opp.title,
                "deadline": opp.deadline.isoformat() if opp.deadline else None,
                "score": opp.score,
                "agency": opp.agency,
                "url": opp.url,
                "created_at": opp.created_at.isoformat() if opp.created_at else None
            }
            for opp in all_opps[:20]  # Limit to first 20
        ],
        "digest_opportunities": [
            {
                "id": opp.id,
                "title": opp.title,
                "deadline": opp.deadline.isoformat() if opp.deadline else None,
                "score": opp.score,
                "agency": opp.agency,
                "url": opp.url
            }
            for opp in digest_opps
        ]
    }


@app.get("/whatsapp/webhook")
async def verify_whatsapp_webhook(request: Request):
    """Verify Meta WhatsApp webhook."""
    if (settings.whatsapp_provider or "meta").lower() != "meta":
        raise HTTPException(status_code=404, detail="Webhook verification not available for Twilio")

    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == settings.whatsapp_verify_token:
        logger.info("Webhook verified successfully")
        return Response(content=challenge, media_type="text/plain")

    logger.warning("Webhook verification failed")
    raise HTTPException(status_code=403, detail="Verification failed")


@app.get("/webhook", include_in_schema=False)
async def legacy_verify_webhook(request: Request):
    """Legacy webhook verification endpoint for backwards compatibility."""
    return await verify_whatsapp_webhook(request)


@app.post("/whatsapp/webhook")
async def handle_whatsapp_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle incoming WhatsApp webhook for configured provider."""
    provider = (settings.whatsapp_provider or "meta").lower()

    if provider == "twilio":
        return await handle_twilio_webhook(request, db)

    return await handle_meta_webhook(request, db)


@app.post("/webhook", include_in_schema=False)
async def legacy_handle_webhook(request: Request, db: Session = Depends(get_db)):
    """Legacy webhook endpoint for backwards compatibility."""
    return await handle_whatsapp_webhook(request, db)


async def handle_meta_webhook(request: Request, db: Session) -> JSONResponse:
    """Handle Meta WhatsApp webhook payload."""
    try:
        body = await request.json()
        logger.info("Received Meta WhatsApp webhook: %s", json.dumps(body, indent=2))

        if body.get("object") != "whatsapp_business_account":
            return JSONResponse(content={"status": "ignored"})

        entries = body.get("entry", [])
        for entry in entries:
            changes = entry.get("changes", [])
            for change in changes:
                value = change.get("value", {})
                messages = value.get("messages", [])

                for message in messages:
                    from_number = normalize_whatsapp_number(message.get("from"))
                    message_text = message.get("text", {}).get("body", "")

                    if not message_text:
                        continue

                    await process_incoming_message(from_number, message_text, db)

        return JSONResponse(content={"status": "ok"})
    except Exception as exc:
        logger.error("Error handling Meta webhook: %s", exc)
        return JSONResponse(content={"status": "error", "message": str(exc)}, status_code=500)


async def handle_twilio_webhook(request: Request, db: Session) -> JSONResponse:
    """Handle Twilio WhatsApp webhook payload."""
    try:
        form = await request.form()
        form_dict = {k: v for k, v in form.multi_items()}
        
        # Check if this is a status callback (sent, delivered, etc.)
        message_status = form_dict.get("MessageStatus")
        if message_status:
            logger.debug("Received Twilio status callback: %s for MessageSid: %s", 
                        message_status, form_dict.get("MessageSid", "unknown"))
            return JSONResponse(content={"status": "ok"})
        
        # This is an incoming message - validate signature
        signature = request.headers.get("X-Twilio-Signature", "")
        if not settings.twilio_auth_token:
            logger.error("Twilio auth token not configured")
            raise HTTPException(status_code=500, detail="Twilio configuration incomplete")

        from twilio.request_validator import RequestValidator  # type: ignore

        # Construct the full URL for signature validation
        # Twilio expects the full URL including scheme and host
        url = str(request.url)
        # Remove query parameters if present (Twilio signature doesn't include them)
        if '?' in url:
            url = url.split('?')[0]

        validator = RequestValidator(settings.twilio_auth_token)
        
        # Try validation with different URL formats
        # Twilio signature validation can be sensitive to URL format
        is_valid = False
        
        # Try 1: URL without query parameters (most common)
        try:
            is_valid = validator.validate(url, form_dict, signature)
            if is_valid:
                logger.debug("Twilio signature validated with URL (no query)")
        except Exception as e:
            logger.debug("Validation attempt 1 failed: %s", e)
        
        # Try 2: Full URL with query parameters
        if not is_valid and request.url.query:
            try:
                url_with_query = str(request.url)
                is_valid = validator.validate(url_with_query, form_dict, signature)
                if is_valid:
                    logger.debug("Twilio signature validated with full URL (with query)")
            except Exception as e:
                logger.debug("Validation attempt 2 failed: %s", e)
        
        # Try 3: URL with just path (for some proxy setups)
        if not is_valid:
            try:
                path_only = request.url.path
                is_valid = validator.validate(path_only, form_dict, signature)
                if is_valid:
                    logger.debug("Twilio signature validated with path only")
            except Exception as e:
                logger.debug("Validation attempt 3 failed: %s", e)
        
        if not is_valid:
            logger.warning(
                "Invalid Twilio signature. URL: %s, Has query: %s, Signature present: %s, "
                "Auth token configured: %s",
                url, bool(request.url.query), bool(signature), bool(settings.twilio_auth_token)
            )
            
            # For development: allow bypassing signature validation
            # Set ENABLE_TWILIO_SIGNATURE_VALIDATION=false in .env to disable
            if settings.app_env == "development" and not os.getenv("ENABLE_TWILIO_SIGNATURE_VALIDATION", "true").lower() == "true":
                logger.warning("Bypassing Twilio signature validation in development mode")
                is_valid = True
            
            if not is_valid:
                raise HTTPException(status_code=403, detail="Invalid Twilio signature")

        # Extract message content
        message_text = form_dict.get("Body", "")
        if not message_text:
            logger.info("No message body in Twilio webhook, ignoring")
            return JSONResponse(content={"status": "ignored"})

        from_number = normalize_whatsapp_number(form_dict.get("From"))
        logger.info("Processing incoming Twilio message from %s: %s", from_number, message_text[:50])
        await process_incoming_message(from_number, message_text, db)

        return JSONResponse(content={"status": "ok"})
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error handling Twilio webhook: %s", exc, exc_info=True)
        return JSONResponse(content={"status": "error", "message": str(exc)}, status_code=500)


async def handle_digest_request(from_number: str, db: Session):
    """Handle digest request."""
    try:
        # Get most recent opportunities - include those with future deadlines or no deadline
        from sqlalchemy import or_
        now = datetime.utcnow()
        
        opportunities = db.query(Opportunity).filter(
            or_(
                Opportunity.deadline >= now,
                Opportunity.deadline.is_(None)
            )
        ).order_by(
            Opportunity.created_at.desc()  # Most recent first
        ).limit(3).all()
        
        logger.info("Found %d opportunities for digest to %s", len(opportunities), from_number)
        
        # Log details about each opportunity found
        for opp in opportunities:
            logger.info("Opportunity: %s (deadline: %s, score: %s)", 
                       opp.title, opp.deadline, opp.score)
        
        if not opportunities:
            logger.warning("No opportunities found with future deadlines or no deadline")
            # Check total count and breakdown for debugging
            from sqlalchemy import func
            total_count = db.query(Opportunity).count()
            future_count = db.query(Opportunity).filter(Opportunity.deadline >= now).count()
            null_count = db.query(Opportunity).filter(Opportunity.deadline.is_(None)).count()
            past_count = db.query(Opportunity).filter(
                Opportunity.deadline.isnot(None),
                Opportunity.deadline < now
            ).count()
            
            logger.warning(
                "Opportunity breakdown - Total: %d, Future: %d, Null: %d, Past: %d",
                total_count, future_count, null_count, past_count
            )
            
            # Log a few sample opportunities for debugging
            sample_opps = db.query(Opportunity).limit(5).all()
            for sample in sample_opps:
                logger.warning(
                    "Sample opportunity: %s (deadline: %s, score: %s)",
                    sample.title, sample.deadline, sample.score
                )
            whatsapp_sender.send_text(
                from_number,
                "No opportunities available at the moment. Check back later!"
            )
            return
        
        # Format digest items
        items = []
        for opp in opportunities:
            items.append({
                "title": opp.title,
                "action": "See details and apply",
                "deadline": opp.deadline.isoformat() if opp.deadline else None,
                "url": opp.url,
                "opportunity_id": opp.id
            })
            logger.info("Added opportunity to digest: %s (deadline: %s)", opp.title, opp.deadline)
        
        # Send digest
        logger.info("Sending digest with %d items to %s", len(items), from_number)
        success = whatsapp_sender.send_digest(from_number, items)
        if success:
            logger.info("Digest sent successfully to %s", from_number)
        else:
            logger.error("Failed to send digest to %s", from_number)
        
    except Exception as e:
        logger.error("Error handling digest request: %s", e, exc_info=True)
        whatsapp_sender.send_text(
            from_number,
            "Sorry, there was an error generating the digest. Please try again later."
        )


async def handle_proposal_request(from_number: str, item_num: int, db: Session):
    """Handle proposal request (1, 2, 3, etc.)."""
    try:
        # Get opportunities (same logic as digest) - include those with future deadlines or no deadline
        from sqlalchemy import or_
        now = datetime.utcnow()
        
        opportunities = db.query(Opportunity).filter(
            or_(
                Opportunity.deadline >= now,
                Opportunity.deadline.is_(None)
            )
        ).order_by(
            Opportunity.created_at.desc()  # Most recent first (matches digest)
        ).limit(3).all()
        
        if item_num < 1 or item_num > len(opportunities):
            whatsapp_sender.send_text(
                from_number,
                f"Invalid selection. Please reply with 1, 2, or 3."
            )
            return
        
        opportunity = opportunities[item_num - 1]
        
        # Check if proposal exists
        proposal = db.query(Proposal).filter(
            Proposal.opportunity_id == opportunity.id
        ).order_by(Proposal.created_at.desc()).first()
        
        # Check if using Twilio (which can't send PDFs)
        is_twilio = (settings.whatsapp_provider or "meta").lower() == "twilio"
        
        # Get RAG chunks for opportunity
        from rag.store import RAGStore
        rag_store = RAGStore()
        chunks = rag_store.query(opportunity.title, top_k=5)
        
        if is_twilio:
            # For Twilio: Generate and send text proposal directly
            deadline_str = opportunity.deadline.isoformat() if opportunity.deadline else None
            proposal_text = proposal_writer.generate_proposal_text(
                opportunity_title=opportunity.title,
                agency=opportunity.agency,
                deadline=deadline_str,
                amount=opportunity.amount,
                chunks=chunks
            )
            
            # Send text proposal
            success = whatsapp_sender.send_proposal_text(
                to=from_number,
                proposal_text=proposal_text,
                opportunity_title=opportunity.title
            )
            
            if not success:
                whatsapp_sender.send_text(
                    from_number,
                    f"Sorry, there was an error sending the proposal for: {opportunity.title}"
                )
        else:
            # For Meta: Generate PDF and send document
            # Check if proposal exists
            proposal = db.query(Proposal).filter(
                Proposal.opportunity_id == opportunity.id
            ).order_by(Proposal.created_at.desc()).first()
            
            if not proposal:
                # Generate PDF
                pdf_path = proposal_writer.generate_proposal_pdf(
                    opportunity_title=opportunity.title,
                    agency=opportunity.agency,
                    deadline=opportunity.deadline.isoformat() if opportunity.deadline else None,
                    amount=opportunity.amount,
                    chunks=chunks
                )
                
                # Save proposal
                proposal = Proposal(
                    opportunity_id=opportunity.id,
                    pdf_path=pdf_path,
                    summary=opportunity.title
                )
                db.add(proposal)
                db.commit()
            else:
                pdf_path = proposal.pdf_path
            
            # Send PDF
            whatsapp_sender.send_document(
                from_number,
                pdf_path,
                caption=f"Proposal for: {opportunity.title}"
            )
        
        # Generate and send ICS if deadline exists
        if opportunity.deadline:
            ics_path = generate_ics(
                title=opportunity.title,
                deadline=opportunity.deadline,
                description=f"Deadline for {opportunity.title}",
                url=opportunity.url
            )
            # Note: WhatsApp doesn't support ICS directly, so we'd need to convert or send as document
            # For now, we'll just send the PDF
        
    except Exception as e:
        logger.error(f"Error handling proposal request: {e}")
        whatsapp_sender.send_text(
            from_number,
            "Sorry, there was an error generating the proposal. Please try again later."
        )


async def handle_query(from_number: str, query: str, db: Session):
    """Handle general query."""
    try:
        # Route query through agent
        result = agent_router.answer_query(query, top_k=4)
        
        # Format answer with citations
        answer = result.answer
        
        # Send answer
        whatsapp_sender.send_text(from_number, answer)
        
    except Exception as e:
        logger.error(f"Error handling query: {e}")
        whatsapp_sender.send_text(
            from_number,
            "Sorry, there was an error processing your query. Please try again later."
        )


@app.post("/cron/run")
async def run_cron(db: Session = Depends(get_db)):
    """Manually trigger crawl and digest."""
    try:
        from ingest.ingester import Ingester
        from crawler.crawler import Crawler
        from crawler.sources import load_sources
        from database.models import Source
        
        # Load sources
        source_configs = load_sources()
        
        # Sync sources to DB
        for source_config in source_configs:
            if not source_config.active:
                continue
            
            db_source = db.query(Source).filter(Source.url == source_config.url).first()
            if not db_source:
                db_source = Source(
                    name=source_config.name,
                    url=source_config.url,
                    schedule_cron=source_config.schedule_cron,
                    active=source_config.active
                )
                db.add(db_source)
                db.commit()
                db.refresh(db_source)
            else:
                db_source.active = source_config.active
                db.commit()
        
        # Crawl and ingest
        ingester = Ingester(db)
        crawled_count = 0
        
        async with Crawler() as crawler:
            for source_config in source_configs:
                if not source_config.active:
                    continue
                
                db_source = db.query(Source).filter(Source.url == source_config.url).first()
                if not db_source:
                    continue
                
                try:
                    crawl_results = await crawler.crawl(source_config)
                    if crawl_results:
                        ingested = ingester.ingest(db_source.id, crawl_results)
                        crawled_count += ingested
                except Exception as e:
                    logger.error(f"Error crawling source {source_config.name}: {e}")
                    continue
        
        # Send digests to active subscribers
        subscribers = db.query(Subscriber).filter(
            Subscriber.active == True,
            Subscriber.channel == "whatsapp"
        ).all()
        
        digest_count = 0
        for subscriber in subscribers:
            try:
                await handle_digest_request(subscriber.handle, db)
                digest_count += 1
            except Exception as e:
                logger.error(f"Error sending digest to {subscriber.handle}: {e}")
        
        return {
            "status": "success",
            "crawled": crawled_count,
            "digests_sent": digest_count
        }
    except Exception as e:
        logger.error(f"Error running cron: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/reindex")
async def reindex_rag_store(db: Session = Depends(get_db)):
    """
    Reindex all documents from the database into ChromaDB.
    This is useful when embeddings failed during initial ingest.
    """
    try:
        from rag.store import RAGStore
        from rag.chunker import chunk_text
        from database.models import Document
        
        logger.info("Starting RAG store reindex...")
        
        # Load all documents with non-empty raw_text
        documents = db.query(Document).filter(
            Document.raw_text.isnot(None),
            Document.raw_text != ""
        ).all()
        
        logger.info(f"Found {len(documents)} documents to reindex")
        
        if not documents:
            return {
                "status": "success",
                "message": "No documents to reindex",
                "documents_processed": 0,
                "chunks_added": 0
            }
        
        # Initialize RAG store
        rag_store = RAGStore()
        
        total_chunks = 0
        processed = 0
        errors = 0
        
        for doc in documents:
            try:
                # Chunk the document
                chunks = chunk_text(
                    text=doc.raw_text,
                    url=doc.url,
                    title=doc.title
                )
                
                if chunks:
                    # Add to RAG store (duplicates will be handled by ChromaDB)
                    success = rag_store.add_documents(chunks)
                    if success:
                        total_chunks += len(chunks)
                        processed += 1
                        logger.info(f"Reindexed document {doc.id}: {doc.url} ({len(chunks)} chunks)")
                    else:
                        errors += 1
                        logger.warning(f"Failed to add chunks for document {doc.id}: {doc.url}")
                else:
                    logger.warning(f"No chunks generated for document {doc.id}: {doc.url}")
                    errors += 1
                    
            except Exception as e:
                errors += 1
                logger.error(f"Error reindexing document {doc.id} ({doc.url}): {e}")
                continue
        
        logger.info(f"Reindex complete: {processed} documents processed, {total_chunks} chunks added, {errors} errors")
        
        return {
            "status": "success",
            "documents_processed": processed,
            "chunks_added": total_chunks,
            "errors": errors,
            "total_documents": len(documents)
        }
    except Exception as e:
        logger.error(f"Error during reindex: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)

