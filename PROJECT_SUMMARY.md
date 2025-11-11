# Project Summary

## Overview
This is a production-ready AI Agent system for monitoring and delivering Nigerian grants, scholarships, and education policies to academia via WhatsApp.

## Components

### 1. Crawler (`crawler/`)
- **Playwright**: Headless browser for dynamic content
- **RSS**: Feed parsing for news feeds
- **Sources**: YAML-configurable source list
- **Retry Logic**: Exponential backoff for resilience

### 2. Deduplication (`dedupe/`)
- **Exact Duplicates**: SHA256 hashing
- **Near Duplicates**: SimHash with configurable threshold
- **Memory Efficient**: In-memory hash storage

### 3. RAG Store (`rag/`)
- **ChromaDB**: Vector store for embeddings
- **Chunking**: Heading-aware text chunking (800-1200 tokens)
- **Embeddings**: Sentence transformers (local) or remote embedding service
- **Query**: Semantic search with citations
- **Embedding Client**: Supports both local and remote embedding generation
  - Local mode: Uses SentenceTransformer models directly (default)
  - Remote mode: Calls separate embedding microservice (deployed on Hugging Face Spaces)

### 4. Agents (`agents/`)
- **ChangeDetector**: LLM-powered change detection
- **OpportunityExtractor**: Extract grants/scholarships
- **ProposalWriter**: Generate one-pager PDFs
- **Router**: Handle user queries with RAG
- **LLMClient**: Unified LLM interface (OpenAI/Ollama)

### 5. Tools (`tools/`)
- **PDF Extractor**: Extract text from PDFs
- **PDF Generator**: Generate proposal PDFs (WeasyPrint)
- **WhatsApp Sender**: Send messages/documents via Cloud API
- **ICS Generator**: Generate calendar files for deadlines

### 6. Database (`database/`)
- **Models**: SQLAlchemy models for all entities
- **Migrations**: Alembic for schema management
- **Session**: Database session management

### 7. API (`api/`)
- **FastAPI**: Modern async API
- **Webhook**: WhatsApp webhook handler
- **Cron Endpoint**: Manual trigger for crawling
- **Health Check**: System health monitoring

### 8. Scheduler (`scheduler/`)
- **APScheduler**: Cron job scheduling
- **Configurable**: Schedule via environment variable
- **Background**: Runs in separate thread

### 9. Ingestion (`ingest/`)
- **Pipeline**: Complete ingestion pipeline
- **Versioning**: Document version tracking
- **Change Detection**: Automatic change detection
- **Opportunity Extraction**: Automatic opportunity extraction

## Data Flow

1. **Cron Trigger** → Scheduler triggers crawl job
2. **Crawl** → Playwright/RSS fetches content
3. **Dedupe** → Check for duplicates
4. **Ingest** → Store in database
5. **Chunk** → Create RAG chunks
6. **Embed** → Generate embeddings
7. **Store** → Add to ChromaDB
8. **Detect Changes** → LLM detects changes
9. **Extract Opportunities** → LLM extracts opportunities
10. **Send Digest** → WhatsApp digest to subscribers
11. **Handle Queries** → RAG-powered Q&A

## Database Schema

- **sources**: Crawling sources
- **documents**: Crawled documents
- **doc_versions**: Document versions
- **changes**: Detected changes
- **opportunities**: Extracted opportunities
- **proposals**: Generated proposals
- **subscribers**: WhatsApp subscribers

## API Endpoints

- `GET /health` - Health check
- `GET /webhook` - WhatsApp webhook verification
- `POST /webhook` - WhatsApp webhook handler
- `POST /cron/run` - Manual cron trigger

## WhatsApp Commands

- `digest` - Get weekly digest
- `1/2/3` - Get proposal PDF
- `STOP` - Unsubscribe
- `SUBSCRIBE` - Subscribe
- `[query]` - Ask a question

## Configuration

All configuration via `.env` file:
- Database URL
- WhatsApp credentials
- LLM provider/API key
- RAG configuration
  - Embedding provider (local/remote)
  - Embedding service URL (for remote mode)
  - Embedding service API key (optional)
- Crawler settings
- Cron schedule

### Embedding Service Architecture

The system supports a split embedding architecture for Hugging Face Space deployment:
- **Local Mode** (default): Uses SentenceTransformer models directly in the main application
- **Remote Mode**: Calls a separate embedding microservice deployed on Hugging Face Spaces
  - Reduces memory usage in the main application
  - Allows independent scaling of embedding generation
  - Configure via `EMBEDDING_PROVIDER=remote` and `EMBEDDING_SERVICE_URL`

## Testing

- **Unit Tests**: `tests/test_*.py`
- **Integration Tests**: API endpoints
- **Coverage**: pytest-cov

## Deployment

1. Set up MySQL database
2. Configure `.env` file
3. Run migrations: `alembic upgrade head`
4. Start application: `python run.py`
5. Configure WhatsApp webhook
6. Set up cron (optional, uses APScheduler)

## Key Features

✅ Automated crawling with retry logic
✅ Exact and near-duplicate detection
✅ RAG-powered Q&A with citations
✅ Change detection using LLM
✅ Opportunity extraction
✅ Proposal generation (PDF)
✅ WhatsApp integration
✅ Cron scheduling
✅ Document versioning
✅ Error handling and logging

## Next Steps

1. Add more sources to `crawler/sources.yaml`
2. Customize LLM prompts in `agents/`
3. Improve opportunity ranking
4. Add monitoring and alerts
5. Deploy to production
6. Scale with more workers

## License

MIT

