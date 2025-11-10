"""FastAPI application."""
import logging
from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json

from config import settings
from database.session import get_db, init_db
from database.models import Subscriber, Opportunity, Proposal
from tools.whatsapp import WhatsAppSender
from tools.schemas import WhatsAppMessage, DigestItem
from agents.router import AgentRouter
from agents.proposal_writer import ProposalWriter
from tools.ics_generator import generate_ics
from datetime import datetime

# Configure logging
logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)

app = FastAPI(title="Nigerian Grants Agent", version="1.0.0")

# Initialize components
whatsapp_sender = WhatsAppSender()
agent_router = AgentRouter()
proposal_writer = ProposalWriter()


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


@app.get("/webhook")
async def verify_webhook(request: Request):
    """Verify WhatsApp webhook."""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    if mode == "subscribe" and token == settings.whatsapp_verify_token:
        logger.info("Webhook verified successfully")
        return Response(content=challenge, media_type="text/plain")
    else:
        logger.warning("Webhook verification failed")
        raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhook")
async def handle_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle incoming WhatsApp messages."""
    try:
        body = await request.json()
        logger.info(f"Received webhook: {json.dumps(body, indent=2)}")
        
        # Parse WhatsApp webhook payload
        if "object" not in body or body["object"] != "whatsapp_business_account":
            return JSONResponse(content={"status": "ignored"})
        
        entries = body.get("entry", [])
        for entry in entries:
            changes = entry.get("changes", [])
            for change in changes:
                value = change.get("value", {})
                messages = value.get("messages", [])
                
                for message in messages:
                    from_number = message.get("from")
                    message_text = message.get("text", {}).get("body", "")
                    message_id = message.get("id")
                    timestamp = message.get("timestamp")
                    
                    if not message_text:
                        continue
                    
                    # Handle unsubscribe
                    if message_text.upper().strip() in ["STOP", "UNSUBSCRIBE"]:
                        subscriber = db.query(Subscriber).filter(
                            Subscriber.handle == from_number,
                            Subscriber.channel == "whatsapp"
                        ).first()
                        if subscriber:
                            subscriber.active = False
                            db.commit()
                            whatsapp_sender.send_text(
                                from_number,
                                "You have been unsubscribed. Send 'SUBSCRIBE' to resubscribe."
                            )
                        continue
                    
                    # Handle subscribe
                    if message_text.upper().strip() in ["SUBSCRIBE", "START"]:
                        subscriber = db.query(Subscriber).filter(
                            Subscriber.handle == from_number,
                            Subscriber.channel == "whatsapp"
                        ).first()
                        if not subscriber:
                            subscriber = Subscriber(
                                channel="whatsapp",
                                handle=from_number,
                                locale="en",
                                active=True
                            )
                            db.add(subscriber)
                        else:
                            subscriber.active = True
                        db.commit()
                        whatsapp_sender.send_text(
                            from_number,
                            "Welcome! You are now subscribed. Send 'digest' for weekly digest or ask a question."
                        )
                        continue
                    
                    # Handle digest request
                    if message_text.lower().strip() == "digest":
                        await handle_digest_request(from_number, db)
                        continue
                    
                    # Handle proposal request (1, 2, 3, etc.)
                    if message_text.strip().isdigit():
                        item_num = int(message_text.strip())
                        await handle_proposal_request(from_number, item_num, db)
                        continue
                    
                    # Handle general query
                    await handle_query(from_number, message_text, db)
        
        return JSONResponse(content={"status": "ok"})
    except Exception as e:
        logger.error(f"Error handling webhook: {e}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)


async def handle_digest_request(from_number: str, db: Session):
    """Handle digest request."""
    try:
        # Get top opportunities
        opportunities = db.query(Opportunity).filter(
            Opportunity.deadline >= datetime.utcnow()
        ).order_by(Opportunity.score.desc(), Opportunity.deadline.asc()).limit(3).all()
        
        if not opportunities:
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
        
        # Send digest
        whatsapp_sender.send_digest(from_number, items)
        
        # Store digest state (simplified - in production, use Redis or DB)
        # For now, we'll query fresh each time
        
    except Exception as e:
        logger.error(f"Error handling digest request: {e}")
        whatsapp_sender.send_text(
            from_number,
            "Sorry, there was an error generating the digest. Please try again later."
        )


async def handle_proposal_request(from_number: str, item_num: int, db: Session):
    """Handle proposal request (1, 2, 3, etc.)."""
    try:
        # Get opportunities (same logic as digest)
        opportunities = db.query(Opportunity).filter(
            Opportunity.deadline >= datetime.utcnow()
        ).order_by(Opportunity.score.desc(), Opportunity.deadline.asc()).limit(3).all()
        
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
        
        # Generate proposal if doesn't exist
        if not proposal:
            # Get RAG chunks for opportunity
            from rag.store import RAGStore
            rag_store = RAGStore()
            chunks = rag_store.query(opportunity.title, top_k=5)
            
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)

