# EduNavigator - Technical Documentation for Presentation

## 1. High-level Overview

**EduNavigator** is a production-ready AI-powered Agentic Research Assistant that automatically monitors Nigerian government sources, regulatory bodies, and funding organizations for grants, scholarships, and education/research policies. The system uses RAG (Retrieval-Augmented Generation) to provide accurate, citation-grounded answers to user queries via WhatsApp.

The project solves the critical problem of information discovery and monitoring for Nigerian academia. Researchers, students, and lecturers face challenges staying updated with rapidly changing funding opportunities, scholarship deadlines, and policy updates from multiple sources (NDPC, TETFund, CBN, FME, etc.). EduNavigator automates the monitoring, extraction, and intelligent summarization of these opportunities, delivering personalized digests and answering questions through a familiar WhatsApp interface.

**Main Users:**
- Nigerian academics (researchers, lecturers, PhD students, research teams)
- University research offices and grant administrators
- Students seeking scholarships and funding opportunities
- Educational institutions tracking policy changes

**Core Problems Solved:**
- **Information Overload**: Aggregates content from 20+ sources into a single, digestible format
- **Deadline Awareness**: Tracks and highlights application deadlines automatically
- **Change Detection**: Identifies policy and regulation changes that may affect eligibility
- **Knowledge Access**: Provides instant Q&A with citations about grants, scholarships, and policies
- **Proposal Assistance**: Generates one-pager proposal templates based on opportunity requirements

---

## 2. Architecture & Tech Stack

### Programming Languages
- **Python 3.9+** (primary language)

### Main Frameworks and Libraries

**Web Framework & API:**
- **FastAPI** (`0.104.1`) - Modern async web framework for REST API
- **Uvicorn** (`0.24.0`) - ASGI server
- **Pydantic** (`2.5.0`) - Data validation and settings management

**Database & ORM:**
- **SQLAlchemy** (`2.0.23`) - ORM for database operations
- **Alembic** (`1.12.1`) - Database migration tool
- **PyMySQL** (`1.1.0`) / **psycopg2** (`2.9.9`) - Database drivers (MySQL/PostgreSQL)

**Web Crawling & Content Extraction:**
- **Playwright** (`1.40.0`) - Headless browser for dynamic content scraping
- **feedparser** (`6.0.10`) - RSS feed parsing
- **BeautifulSoup4** (`4.12.2`) - HTML parsing
- **lxml** (`4.9.3`) - XML/HTML processing

**AI/ML & Vector Search:**
- **ChromaDB** (`0.4.18`) - Vector database for embeddings storage
- **sentence-transformers** (`2.2.2`) - Local embedding generation
- **LangChain** (`0.0.350`) - LLM framework utilities
- **OpenAI** (`1.3.7`) - OpenAI API client
- **groq** - Groq API client for fast LLM inference

**LLM Providers Supported:**
- OpenAI (GPT models)
- Groq (Llama models)
- Ollama-compatible APIs (local deployment)

**PDF Processing:**
- **pypdf2** (`3.0.1`) - PDF text extraction
- **pdfplumber** (`0.10.3`) - Advanced PDF extraction
- **WeasyPrint** (`60.2`) - PDF generation from HTML/Markdown
- **reportlab** (`4.0.7`) - Programmatic PDF creation
- **markdown** (`3.5.1`) - Markdown parsing

**WhatsApp Integration:**
- **Twilio** (`8.11.0`) - Twilio Programmable Messaging API
- Meta WhatsApp Cloud API (via `requests`)

**Scheduling:**
- **APScheduler** (`3.10.4`) - Cron job scheduling

**Deduplication:**
- **simhash** (`2.1.2`) - Near-duplicate detection

**Utilities:**
- **python-dotenv** (`1.0.0`) - Environment variable management
- **pyyaml** (`6.0.1`) - YAML parsing for source configuration
- **ics** (`0.7.2`) - Calendar file generation
- **httpx** (`0.25.2`) - Async HTTP client

**Testing:**
- **pytest** (`7.4.3`) - Testing framework
- **pytest-asyncio** (`0.21.1`) - Async test support
- **pytest-cov** (`4.1.0`) - Coverage reporting

### Data Stores

**Primary Database:**
- **MySQL 8.0+** (production) or **SQLite** (development)
- Stores: sources, documents, versions, changes, opportunities, proposals, subscribers

**Vector Database:**
- **ChromaDB** (persistent on-disk)
- Stores: document embeddings for semantic search
- Location: `./chroma_db` (configurable via `CHROMA_PERSIST_DIR`)

**In-Memory:**
- Deduplication hash sets (SimHash and SHA256)

### Background Workers & External Services

**Background Workers:**
- **APScheduler** - Runs in a separate thread, triggers cron jobs
- Default schedule: Daily at 6 AM (`0 6 * * *`)

**External Services:**
- **Meta WhatsApp Cloud API** - For sending/receiving WhatsApp messages (optional)
- **Twilio WhatsApp API** - Alternative WhatsApp provider
- **LLM APIs** - OpenAI, Groq, or self-hosted Ollama
- **Remote Embedding Service** - Optional microservice for embedding generation (Hugging Face Spaces)

### High-Level Architecture

The system follows a **pipeline architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                      User Interface                          │
│                    (WhatsApp Messages)                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Webhook      │  │ Agent Router │  │ Proposal     │     │
│  │ Handler      │  │ (RAG Q&A)    │  │ Writer       │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Scheduling Layer                          │
│              (APScheduler - Background Thread)               │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Crawling & Ingestion Pipeline              │
│                                                               │
│  [Cron] → [Crawler] → [Dedupe] → [Ingester]                 │
│                                                               │
│  Crawler:                                                     │
│  - Playwright (HTML)                                          │
│  - RSS Feed Parser                                            │
│  - PDF Downloader                                             │
│                                                               │
│  Dedupe:                                                      │
│  - SHA256 exact duplicates                                    │
│  - SimHash near-duplicates                                    │
│                                                               │
│  Ingester:                                                    │
│  - Store in MySQL                                             │
│  - Create document versions                                   │
│  - Chunk text (heading-aware)                                 │
│  - Generate embeddings (local/remote)                         │
│  - Store in ChromaDB                                          │
│  - Detect changes (LLM)                                       │
│  - Extract opportunities (LLM)                                │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │                                  │
        ▼                                  ▼
┌──────────────────┐          ┌──────────────────┐
│   MySQL Database │          │   ChromaDB       │
│                  │          │   (Vector Store) │
│ - Sources        │          │                  │
│ - Documents      │          │ - Embeddings     │
│ - Versions       │          │ - Metadata       │
│ - Changes        │          │ - Documents      │
│ - Opportunities  │          └──────────────────┘
│ - Proposals      │
│ - Subscribers    │
└──────────────────┘
```

**Data Flow:**

1. **Crawl Phase:**
   - Scheduler triggers cron job → `POST /cron/run`
   - Crawler fetches content from sources (Playwright/RSS)
   - Content is hashed (SHA256) for duplicate detection

2. **Ingestion Phase:**
   - Deduper checks for exact/near duplicates
   - New/updated documents stored in MySQL
   - Document versions tracked for change detection
   - Text chunked with heading awareness (800-1200 chars)
   - Embeddings generated (local SentenceTransformer or remote service)
   - Chunks + embeddings stored in ChromaDB

3. **AI Processing Phase:**
   - ChangeDetector compares old/new document versions (LLM)
   - OpportunityExtractor identifies grants/scholarships (LLM)
   - Changes and opportunities stored in MySQL

4. **Query Phase:**
   - User sends WhatsApp message → Webhook receives
   - AgentRouter queries ChromaDB (semantic search)
   - LLM generates answer with citations
   - Answer sent back via WhatsApp

5. **Digest Phase:**
   - System selects top 3 opportunities (by score + deadline)
   - Digest formatted and sent to active subscribers
   - Users can request proposal PDFs (1/2/3)

---

## 3. Folder & Module Structure

### Root Directory Overview

```
EduNavigator/
├── agents/              # AI agents (LLM-powered components)
├── api/                 # FastAPI application
├── crawler/             # Web crawling logic
├── database/            # Database models and session management
├── dedupe/              # Deduplication logic
├── embedding_service/   # Optional remote embedding microservice
├── ingest/              # Document ingestion pipeline
├── rag/                 # RAG store and chunking
├── scheduler/           # Cron job scheduler
├── tools/               # Utility functions (PDF, WhatsApp, ICS)
├── tests/               # Pytest test suite
├── alembic/             # Database migrations
├── chroma_db/           # ChromaDB persistent storage
├── config.py            # Application configuration
├── run.py               # Main entry point
├── requirements.txt     # Python dependencies
└── README.md            # Project documentation
```

### Key Modules

#### `agents/` - AI Agents
**Purpose:** LLM-powered components for intelligent document processing and query answering.

**Key Files:**
- `llm_client.py` - Unified LLM client (OpenAI/Groq/Ollama)
- `router.py` - Routes user queries through RAG pipeline
- `change_detector.py` - Detects changes in document versions
- `opportunity_extractor.py` - Extracts grants/scholarships from documents
- `proposal_writer.py` - Generates one-pager PDF proposals
- `digest_notifier.py` - Formats and sends digest notifications

**Connections:**
- Uses `rag/store.py` for semantic search
- Uses `tools/whatsapp.py` for notifications
- Uses `database/models.py` for data access

#### `api/` - FastAPI Application
**Purpose:** REST API server and WhatsApp webhook handler.

**Key Files:**
- `main.py` - FastAPI app, routes, webhook handlers

**Connections:**
- Depends on `database/models.py` for data models
- Uses `tools/whatsapp.py` for messaging
- Uses `agents/router.py` for query handling
- Uses `agents/proposal_writer.py` for PDF generation
- Triggers crawling via `ingest/ingester.py`

#### `crawler/` - Web Crawling
**Purpose:** Fetches content from configured sources.

**Key Files:**
- `crawler.py` - Main crawler class (Playwright, RSS, PDF)
- `sources.py` - Source configuration loader
- `sources.yaml` - YAML source definitions (20+ Nigerian sources)

**Connections:**
- Used by `ingest/ingester.py` during cron jobs
- Returns `CrawlOut` objects (defined in `tools/schemas.py`)

#### `database/` - Database Layer
**Purpose:** SQLAlchemy models and session management.

**Key Files:**
- `models.py` - SQLAlchemy ORM models (Source, Document, Opportunity, etc.)
- `session.py` - Database session factory and initialization

**Connections:**
- Used by all modules that need database access
- Migrations managed by Alembic (`alembic/`)

#### `dedupe/` - Deduplication
**Purpose:** Prevents duplicate document storage.

**Key Files:**
- `dedupe.py` - SimHash and SHA256 duplicate detection

**Connections:**
- Used by `ingest/ingester.py` before storing documents

#### `rag/` - Retrieval-Augmented Generation
**Purpose:** Vector store for semantic search and embedding generation.

**Key Files:**
- `store.py` - ChromaDB wrapper and embedding client
- `chunker.py` - Heading-aware text chunking

**Connections:**
- Used by `ingest/ingester.py` to store embeddings
- Used by `agents/router.py` for query retrieval
- Uses `config.py` for embedding provider settings

#### `ingest/` - Ingestion Pipeline
**Purpose:** Orchestrates the complete document ingestion workflow.

**Key Files:**
- `ingester.py` - Main ingestion pipeline (dedupe → store → AI processing)

**Connections:**
- Orchestrates: `dedupe/`, `rag/`, `database/`, `agents/change_detector.py`, `agents/opportunity_extractor.py`

#### `scheduler/` - Cron Scheduling
**Purpose:** Triggers automated crawling jobs.

**Key Files:**
- `scheduler.py` - APScheduler wrapper

**Connections:**
- Triggers `POST /cron/run` endpoint via HTTP
- Configured via `config.py` (`CRON_SCHEDULE`)

#### `tools/` - Utilities
**Purpose:** Reusable utility functions.

**Key Files:**
- `whatsapp.py` - WhatsApp sender abstraction (Meta/Twilio)
- `pdf_extractor.py` - PDF text extraction
- `pdf_generator.py` - PDF generation from Markdown
- `ics_generator.py` - Calendar file generation
- `schemas.py` - Pydantic data models

**Connections:**
- Used by `api/main.py` for WhatsApp communication
- Used by `agents/proposal_writer.py` for PDF generation

---

## 4. Core Features & Flows

### Feature 1: Automated Source Monitoring & Crawling

**Entry Point:** 
- Cron scheduler (`scheduler/scheduler.py`) triggers `POST /cron/run`
- Manual trigger via `POST /cron/run` API endpoint

**Flow:**
1. **Scheduler** (`scheduler/scheduler.py:trigger_cron_job()`) → HTTP POST to `/cron/run`
2. **API Handler** (`api/main.py:run_cron()`) → Loads sources from `crawler/sources.yaml`
3. **Crawler** (`crawler/crawler.py:Crawler.crawl()`) → 
   - For RSS: `crawl_rss()` uses `feedparser`
   - For HTML: `crawl_html()` uses Playwright
   - For PDF: `crawl_pdf()` downloads and extracts text
4. **Hash Calculation** (`crawler/crawler.py:_calculate_hash()`) → SHA256 for duplicate detection
5. Returns `CrawlOut` objects (list of crawled documents)

**Key Files:**
- `scheduler/scheduler.py:trigger_cron_job()`
- `api/main.py:run_cron()`
- `crawler/crawler.py:Crawler.crawl()`
- `crawler/sources.py:load_sources()`

---

### Feature 2: Document Ingestion & RAG Storage

**Entry Point:**
- Called from `api/main.py:run_cron()` after crawling

**Flow:**
1. **Ingester** (`ingest/ingester.py:Ingester.ingest()`) → Receives `CrawlOut` list
2. **Deduplication** (`dedupe/dedupe.py:Deduper.is_duplicate()`) →
   - Exact duplicates: SHA256 hash check
   - Near-duplicates: SimHash with Hamming distance threshold
3. **Database Storage** (`database/models.py:Document`) →
   - New documents: Creates `Document` and `DocVersion`
   - Updated documents: Creates new `DocVersion`, updates `Document`
4. **Text Chunking** (`rag/chunker.py:chunk_text()`) →
   - Heading-aware chunking (respects h1-h6)
   - Chunk size: 1000 chars, overlap: 200 chars
5. **Embedding Generation** (`rag/store.py:EmbeddingClient.encode()`) →
   - Local: Uses SentenceTransformer model directly
   - Remote: HTTP POST to embedding service
6. **Vector Storage** (`rag/store.py:RAGStore.add_documents()`) →
   - Stores chunks + embeddings in ChromaDB
   - Metadata: url, title, heading
7. **Change Detection** (`agents/change_detector.py:ChangeDetector.detect_changes()`) →
   - LLM compares old/new document versions
   - Creates `Change` record with JSON summary
8. **Opportunity Extraction** (`agents/opportunity_extractor.py:OpportunityExtractor.extract_opportunities()`) →
   - LLM extracts grants/scholarships from document
   - Creates `Opportunity` records in database

**Key Files:**
- `ingest/ingester.py:Ingester.ingest()`
- `dedupe/dedupe.py:Deduper.is_duplicate()`
- `rag/chunker.py:chunk_text()`
- `rag/store.py:RAGStore.add_documents()`
- `agents/change_detector.py:ChangeDetector.detect_changes()`
- `agents/opportunity_extractor.py:OpportunityExtractor.extract_opportunities()`

---

### Feature 3: WhatsApp Query Handling (RAG-Powered Q&A)

**Entry Point:**
- WhatsApp webhook: `POST /whatsapp/webhook`
- Meta: JSON payload via `api/main.py:handle_meta_webhook()`
- Twilio: Form data via `api/main.py:handle_twilio_webhook()`

**Flow:**
1. **Webhook Handler** (`api/main.py:handle_whatsapp_webhook()`) →
   - Validates signature (Twilio) or verifies token (Meta)
   - Extracts message text and sender number
2. **Message Router** (`api/main.py:process_incoming_message()`) →
   - Command detection: "digest", "STOP", "SUBSCRIBE", numeric (1/2/3)
   - Default: Treats as query → `handle_query()`
3. **Agent Router** (`agents/router.py:AgentRouter.answer_query()`) →
   - Queries ChromaDB: `rag/store.py:RAGStore.query()` (top_k=4)
   - Builds context from retrieved chunks
   - Formats citations (URLs + titles)
4. **LLM Generation** (`agents/llm_client.py:LLMClient.generate()`) →
   - System prompt: Factual, citation-grounded answers
   - User prompt: Query + context chunks
   - Generates answer with citations
5. **Response** (`tools/whatsapp.py:BaseWhatsAppSender.send_text()`) →
   - Sends answer via Meta/Twilio WhatsApp API

**Key Files:**
- `api/main.py:handle_whatsapp_webhook()`
- `api/main.py:process_incoming_message()`
- `api/main.py:handle_query()`
- `agents/router.py:AgentRouter.answer_query()`
- `rag/store.py:RAGStore.query()`
- `agents/llm_client.py:LLMClient.generate()`
- `tools/whatsapp.py:BaseWhatsAppSender.send_text()`

---

### Feature 4: Weekly Digest Delivery

**Entry Point:**
- User sends "digest" via WhatsApp
- Cron job triggers digest to all active subscribers

**Flow:**
1. **Digest Request** (`api/main.py:handle_digest_request()`) →
   - Queries `Opportunity` table: future deadlines or no deadline
   - Orders by: score DESC, deadline ASC
   - Limits to top 3 opportunities
2. **Formatting** (`tools/whatsapp.py:BaseWhatsAppSender.send_digest()`) →
   - Formats opportunities with title, deadline, action, URL
   - Adds instruction: "Reply 1/2/3 for full one-pager"
3. **Delivery** (`tools/whatsapp.py:MetaWhatsAppSender.send_text()` or `TwilioWhatsAppSender.send_text()`) →
   - Sends formatted digest via WhatsApp

**Key Files:**
- `api/main.py:handle_digest_request()`
- `tools/whatsapp.py:BaseWhatsAppSender.send_digest()`
- `database/models.py:Opportunity` (query)

---

### Feature 5: Proposal PDF Generation

**Entry Point:**
- User sends "1", "2", or "3" via WhatsApp (referring to digest items)

**Flow:**
1. **Proposal Request** (`api/main.py:handle_proposal_request()`) →
   - Retrieves top 3 opportunities (same query as digest)
   - Selects opportunity by index (1, 2, or 3)
2. **Cache Check** (`database/models.py:Proposal`) →
   - Checks if proposal PDF already exists
3. **RAG Retrieval** (`rag/store.py:RAGStore.query()`) →
   - Retrieves relevant chunks for opportunity title (top_k=5)
4. **Proposal Generation** (`agents/proposal_writer.py:ProposalWriter.generate_proposal_pdf()`) →
   - Writes proposal markdown: `write_proposal()` (LLM-generated)
   - Converts to PDF: `tools/pdf_generator.py:generate_proposal_pdf()`
   - Saves to `PDF_STORAGE_DIR`
5. **Database Storage** (`database/models.py:Proposal`) →
   - Creates `Proposal` record linking to `Opportunity`
6. **Document Delivery** (`tools/whatsapp.py:MetaWhatsAppSender.send_document()`) →
   - Uploads PDF to WhatsApp media API (Meta)
   - Sends document message to user
   - **Note:** Twilio sender sends fallback text (no direct document support)

**Key Files:**
- `api/main.py:handle_proposal_request()`
- `agents/proposal_writer.py:ProposalWriter.generate_proposal_pdf()`
- `tools/pdf_generator.py:generate_proposal_pdf()`
- `tools/whatsapp.py:MetaWhatsAppSender.send_document()`

---

## 5. Data Model & Persistence

### Database Schema (SQLAlchemy ORM)

**ORM:** SQLAlchemy 2.0 with Alembic migrations

**Models Defined In:** `database/models.py`

#### Main Entities

**1. `Source`** - Crawling source configuration
- `id` (PK, Integer)
- `name` (String 255) - Source name (e.g., "TETFund Home")
- `url` (Text) - Source URL
- `schedule_cron` (String 100) - Cron schedule
- `active` (Boolean) - Whether source is active
- `created_at`, `updated_at` (DateTime)
- **Relationships:** One-to-many with `Document`

**2. `Document`** - Crawled document
- `id` (PK, Integer)
- `source_id` (FK → Source.id)
- `url` (Text, indexed)
- `title` (String 500)
- `fetched_at` (DateTime)
- `http_hash` (String 64, indexed) - SHA256 hash for deduplication
- `mime` (String 100) - MIME type (text/html, application/pdf)
- `raw_text` (Text) - Extracted text content
- `raw_blob` (LargeBinary) - Original binary (for PDFs)
- **Relationships:**
  - Many-to-one with `Source`
  - One-to-many with `DocVersion`, `Change`, `Opportunity`
- **Indexes:** `(url, http_hash)` composite index

**3. `DocVersion`** - Document version history
- `id` (PK, Integer)
- `doc_id` (FK → Document.id)
- `version` (Integer) - Version number
- `text` (Text) - Text content at this version
- `created_at` (DateTime)
- **Relationships:** Many-to-one with `Document`
- **Indexes:** `(doc_id, version)` composite index

**4. `Change`** - Detected changes between versions
- `id` (PK, Integer)
- `doc_id` (FK → Document.id)
- `old_version` (Integer)
- `new_version` (Integer)
- `summary_json` (Text) - JSON string of `ChangeSummary` (what_changed, who_is_affected, key_dates, required_actions, citations)
- `created_at` (DateTime)
- **Relationships:** Many-to-one with `Document`

**5. `Opportunity`** - Extracted grant/scholarship/policy opportunity
- `id` (PK, Integer)
- `doc_id` (FK → Document.id)
- `title` (String 500)
- `deadline` (DateTime, nullable, indexed)
- `eligibility` (Text, nullable)
- `amount` (String 200, nullable)
- `agency` (String 200) - Agency name (e.g., "TETFund")
- `url` (Text)
- `score` (Float, default=0.0, indexed) - Ranking score
- `created_at`, `updated_at` (DateTime)
- **Relationships:**
  - Many-to-one with `Document`
  - One-to-many with `Proposal`
- **Indexes:** `deadline`, `score`

**6. `Proposal`** - Generated proposal PDFs
- `id` (PK, Integer)
- `opportunity_id` (FK → Opportunity.id)
- `pdf_path` (String 500) - File system path
- `summary` (Text, nullable)
- `created_at` (DateTime)
- **Relationships:** Many-to-one with `Opportunity`

**7. `Subscriber`** - WhatsApp subscriber
- `id` (PK, Integer)
- `channel` (String 50) - Always "whatsapp"
- `handle` (String 100) - WhatsApp number (digits only)
- `locale` (String 10, default="en")
- `active` (Boolean, default=True)
- `created_at`, `updated_at` (DateTime)
- **Constraints:** `channel IN ('whatsapp')`
- **Indexes:** `(channel, handle)` composite index

### Data Operations

**Create (C):**
- Documents: Created during ingestion (`ingest/ingester.py`)
- Opportunities: Extracted by LLM during ingestion
- Subscribers: Created when user sends "SUBSCRIBE" (`api/main.py`)
- Proposals: Generated on-demand when user requests PDF

**Read (R):**
- Opportunities: Queried for digest (by deadline + score)
- Documents: Retrieved for RAG query context
- Subscribers: Filtered by `active=True` for digest delivery

**Update (U):**
- Documents: `http_hash` and `raw_text` updated when content changes
- Subscribers: `active` flag toggled via "STOP"/"SUBSCRIBE" commands

**Delete (D):**
- Not currently implemented (data retention policy)

### Vector Store (ChromaDB)

**Storage:** Persistent ChromaDB collection "nigerian_grants"
- **Embeddings:** Generated from text chunks (384-dim for all-MiniLM-L6-v2)
- **Metadata:** url, title, heading
- **Distance Metric:** Cosine similarity
- **Persistence:** SQLite backend (`./chroma_db/chroma.sqlite3`)

---

## 6. Integrations & External Dependencies

### 1. Meta WhatsApp Cloud API
**Purpose:** Send and receive WhatsApp messages (primary provider)

**Integration:**
- **File:** `tools/whatsapp.py:MetaWhatsAppSender`
- **Functions:**
  - `send_text()` - Sends text messages
  - `send_document()` - Uploads and sends PDF documents
- **Authentication:** Bearer token (`WHATSAPP_ACCESS_TOKEN`)
- **Webhook:** `GET /whatsapp/webhook` (verification), `POST /whatsapp/webhook` (inbound)
- **Configuration:** `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_API_VERSION`

### 2. Twilio WhatsApp API
**Purpose:** Alternative WhatsApp provider (via Twilio Programmable Messaging)

**Integration:**
- **File:** `tools/whatsapp.py:TwilioWhatsAppSender`
- **Functions:**
  - `send_text()` - Sends text messages
  - `send_document()` - Falls back to text (Twilio limitations)
- **Authentication:** Account SID + Auth Token
- **Webhook:** `POST /whatsapp/webhook` (with `X-Twilio-Signature` validation)
- **Configuration:** `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_NUMBER`

### 3. OpenAI API
**Purpose:** LLM inference for change detection, opportunity extraction, proposal writing, query answering

**Integration:**
- **File:** `agents/llm_client.py:LLMClient`
- **Usage:** Default provider when `LLM_PROVIDER=openai`
- **Configuration:** `LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`, `LLM_TEMPERATURE`
- **Models Used:** GPT-4 Turbo, GPT-3.5 Turbo (configurable)

### 4. Groq API
**Purpose:** Fast LLM inference (Llama models)

**Integration:**
- **File:** `agents/llm_client.py:LLMClient`
- **Usage:** Alternative provider when `LLM_PROVIDER=groq`
- **Default Model:** `llama-3.3-70b-versatile`
- **Configuration:** `LLM_API_KEY` (Groq API key), `LLM_BASE_URL` (optional, defaults to Groq)

### 5. Remote Embedding Service (Optional)
**Purpose:** Separate embedding microservice for memory-efficient deployment (Hugging Face Spaces)

**Integration:**
- **File:** `rag/store.py:EmbeddingClient._encode_remote()`
- **Usage:** When `EMBEDDING_PROVIDER=remote`
- **Endpoint:** `POST {EMBEDDING_SERVICE_URL}/embed` with `{"texts": [...]}`
- **Configuration:** `EMBEDDING_SERVICE_URL`, `EMBEDDING_SERVICE_API_KEY` (optional auth)
- **Response Format:** `{"embeddings": [[...], ...]}`

### 6. Sentence Transformers (Local Embeddings)
**Purpose:** Local embedding generation (default)

**Integration:**
- **File:** `rag/store.py:EmbeddingClient.encode()`
- **Model:** `sentence-transformers/all-MiniLM-L6-v2` (384-dim, default)
- **Configuration:** `EMBEDDING_MODEL`, `EMBEDDING_PROVIDER=sentence_transformers`

---

## 7. Notable Implementation Details

### Design Patterns

**1. Strategy Pattern:**
- WhatsApp sender abstraction (`BaseWhatsAppSender`) with concrete implementations (`MetaWhatsAppSender`, `TwilioWhatsAppSender`)
- **File:** `tools/whatsapp.py:get_whatsapp_sender()`

**2. Factory Pattern:**
- LLM client factory based on provider configuration
- **File:** `agents/llm_client.py:LLMClient.__init__()`

**3. Repository Pattern (Implicit):**
- Database access abstracted through SQLAlchemy ORM
- **File:** `database/models.py` (all models)

**4. Pipeline Pattern:**
- Document ingestion pipeline with clear stages (crawl → dedupe → store → AI process)
- **File:** `ingest/ingester.py:Ingester.ingest()`

### Security Considerations

**1. API Key Management:**
- Environment variables via `.env` file
- Loaded via `python-dotenv` and Pydantic settings
- **File:** `config.py:Settings`

**2. Webhook Verification:**
- Meta: Token verification (`GET /whatsapp/webhook?hub.verify_token`)
- Twilio: Request signature validation (`X-Twilio-Signature`)
- **Files:** `api/main.py:verify_whatsapp_webhook()`, `handle_twilio_webhook()`

**3. Secret Key:**
- Configurable `SECRET_KEY` for application secrets (default: "change-me-in-production")
- **File:** `config.py:Settings.secret_key`

**4. Rate Limiting:**
- Not explicitly implemented (rely on LLM provider rate limits)
- Crawler includes retry logic with exponential backoff

**5. Input Sanitization:**
- Pydantic models validate input schemas
- WhatsApp number normalization removes special characters
- **File:** `api/main.py:normalize_whatsapp_number()`

### Performance & Scalability

**1. Async Operations:**
- FastAPI async endpoints for concurrent request handling
- Playwright async API for non-blocking web crawling
- **Files:** `api/main.py` (async def handlers), `crawler/crawler.py` (async methods)

**2. Database Connection Pooling:**
- SQLAlchemy connection pool with `pool_pre_ping=True`
- **File:** `database/session.py:create_engine()`

**3. Embedding Service Separation:**
- Optional remote embedding service reduces memory footprint
- Allows independent scaling of embedding generation
- **File:** `rag/store.py:EmbeddingClient`

**4. Chunking Strategy:**
- Heading-aware chunking preserves document structure
- Overlap prevents information loss at chunk boundaries
- **File:** `rag/chunker.py:chunk_text()`

**5. Deduplication Efficiency:**
- In-memory hash sets (SimHash + SHA256)
- O(1) duplicate detection for exact duplicates
- **File:** `dedupe/dedupe.py:Deduper`

**6. Vector Search:**
- ChromaDB uses HNSW indexing for fast similarity search
- Configurable `top_k` for query results
- **File:** `rag/store.py:RAGStore.query()`

**7. Caching:**
- Proposal PDFs cached in database (`Proposal` model)
- Reuses generated PDFs for repeated requests
- **File:** `api/main.py:handle_proposal_request()`

### Configuration Management

**Environment Variables (via `.env`):**
- Database: `DATABASE_URL`
- WhatsApp: `WHATSAPP_PROVIDER`, `WHATSAPP_*`, `TWILIO_*`
- LLM: `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_TEMPERATURE`
- RAG: `CHROMA_PERSIST_DIR`, `EMBEDDING_MODEL`, `EMBEDDING_PROVIDER`, `EMBEDDING_SERVICE_URL`, `EMBEDDING_SERVICE_API_KEY`
- Crawler: `CRAWLER_USER_AGENT`, `CRAWLER_TIMEOUT`, `CRAWLER_MAX_RETRIES`, `CRAWLER_BACKOFF_FACTOR`
- App: `APP_ENV`, `LOG_LEVEL`, `API_HOST`, `API_PORT`, `CRON_SCHEDULE`, `STORAGE_DIR`, `PDF_STORAGE_DIR`
- Security: `SECRET_KEY`, `ALLOWED_ORIGINS`

**File:** `config.py:Settings` (Pydantic BaseSettings)

**YAML Configuration:**
- Source definitions: `crawler/sources.yaml`
- **File:** `crawler/sources.py:load_sources()`

---

## 8. Limitations, TODOs, and Technical Debt

### Known Limitations

1. **Twilio Document Sending:**
   - Twilio WhatsApp sender cannot send local PDF files directly
   - Falls back to text notification (`tools/whatsapp.py:TwilioWhatsAppSender.send_document()`)
   - **Impact:** Users on Twilio cannot receive proposal PDFs via WhatsApp

2. **ChromaDB Deletion:**
   - `delete_by_url()` not fully implemented (`rag/store.py:RAGStore.delete_by_url()`)
   - ChromaDB doesn't support direct deletion by metadata without querying first
   - **Impact:** Cannot efficiently remove outdated chunks from vector store

3. **ICS Calendar Files:**
   - ICS generation exists but not sent via WhatsApp (`api/main.py:handle_proposal_request()`)
   - WhatsApp doesn't support ICS files directly
   - **Impact:** Calendar invites not delivered to users

4. **Opportunity Ranking:**
   - `Opportunity.score` defaults to 0.0, no ranking algorithm implemented
   - Digest selection only uses deadline ordering
   - **Impact:** Opportunities not prioritized by relevance/importance

5. **Deduplication State:**
   - SimHash and SHA256 sets stored in-memory only
   - Lost on application restart
   - **Impact:** Duplicate detection resets on restart (mitigated by database `http_hash` check)

### TODOs (From Code Comments)

1. **Remote Embedding Service Integration Test:**
   - `tests/test_rag.py:102` - TODO: Add integration test for remote embedding service

### Potential Risks & Fragile Areas

1. **LLM API Reliability:**
   - Heavy dependence on external LLM APIs (OpenAI/Groq)
   - No fallback if API is down
   - **Risk:** Ingestion and query processing fail completely

2. **Playwright Browser Resource Usage:**
   - Headless browser consumes significant memory
   - Multiple concurrent crawls could exhaust resources
   - **Mitigation:** Sequential crawling, browser reuse

3. **Database Transaction Handling:**
   - Ingestion commits all documents in a single transaction
   - Large batches could cause timeouts
   - **Risk:** Partial ingestion on failure

4. **Webhook Security:**
   - Meta webhook verification only checks token match (no HMAC)
   - **Risk:** Potential webhook spoofing if token leaked

5. **PDF Storage:**
   - Generated PDFs stored on local filesystem
   - No cleanup mechanism for old proposals
   - **Risk:** Disk space exhaustion over time

6. **Error Handling:**
   - Some error cases return empty responses instead of detailed error messages
   - **Example:** `agents/router.py:AgentRouter.answer_query()` returns generic message on failure

---

## 9. Slide Deck Outline

### Slide 1 – Title & Introduction
- **Project Name:** EduNavigator
- **One-line Problem Statement:** AI-powered research assistant that monitors Nigerian grants, scholarships, and education policies, delivering personalized updates via WhatsApp
- **My Role and Tech Stack:** Senior Software Engineer | Python, FastAPI, ChromaDB, LLMs (OpenAI/Groq), Playwright, WhatsApp APIs

---

### Slide 2 – Problem & Motivation
- Nigerian academia struggles to track 20+ government sources manually
- Critical deadlines missed due to information overload
- Policy changes go unnoticed, affecting eligibility
- Time-consuming to extract actionable insights from lengthy documents
- Need for centralized, intelligent information delivery

---

### Slide 3 – Solution Overview
- Automated web crawling from 20+ Nigerian sources (NDPC, TETFund, CBN, FME, etc.)
- AI-powered change detection and opportunity extraction
- RAG-powered Q&A with citations
- WhatsApp integration for familiar user experience
- Weekly digest with top 3 opportunities
- One-pager proposal PDF generation

---

### Slide 4 – Architecture Overview
- **Pipeline Architecture:** Cron → Crawler → Dedupe → Ingest → RAG → AI Processing → WhatsApp
- **Data Stores:** MySQL (documents, opportunities) + ChromaDB (embeddings)
- **AI Components:** LLM agents for change detection, extraction, proposal writing
- **Communication:** FastAPI REST API + WhatsApp webhooks (Meta/Twilio)

---

### Slide 5 – Tech Stack Highlights
- **Backend:** FastAPI (async), SQLAlchemy ORM, Alembic migrations
- **Crawling:** Playwright (headless browser), RSS feed parser
- **AI/ML:** ChromaDB (vector store), SentenceTransformers (embeddings), OpenAI/Groq (LLMs)
- **Messaging:** Meta WhatsApp Cloud API / Twilio
- **PDF Processing:** WeasyPrint, pdfplumber
- **Scheduling:** APScheduler (cron jobs)

---

### Slide 6 – Core Workflow: Ingestion Pipeline
- **Crawl:** Playwright/RSS fetches content from configured sources
- **Dedupe:** SHA256 + SimHash prevent duplicate storage
- **Store:** Documents stored in MySQL with version tracking
- **Chunk & Embed:** Heading-aware chunking → embeddings → ChromaDB
- **AI Processing:** Change detection + opportunity extraction via LLM
- **Deliver:** Weekly digest to subscribers

---

### Slide 7 – Core Workflow: User Interaction
- **Query:** User asks question via WhatsApp → RAG retrieves relevant chunks → LLM generates answer with citations
- **Digest:** User requests "digest" → Top 3 opportunities sent
- **Proposal:** User replies "1/2/3" → LLM generates one-pager PDF → Delivered via WhatsApp
- **Subscriptions:** "SUBSCRIBE"/"STOP" commands manage notifications

---

### Slide 8 – Key Features Deep Dive
- **Change Detection:** LLM compares document versions, extracts what changed, who's affected, key dates, required actions
- **Opportunity Extraction:** LLM identifies grants/scholarships with deadlines, eligibility, amounts
- **RAG Q&A:** Semantic search retrieves relevant passages, LLM synthesizes answer with citations
- **Proposal Generation:** LLM writes 500-700 word one-pager based on opportunity requirements

---

### Slide 9 – Data Model
- **Main Entities:** Source, Document, DocVersion, Change, Opportunity, Proposal, Subscriber
- **Relationships:** Source → Document → Versions/Changes/Opportunities → Proposals
- **Vector Store:** ChromaDB stores chunked documents with embeddings (384-dim)
- **Indexing:** Deadlines, scores, URL+hash for fast queries

---

### Slide 10 – Integrations & External Services
- **WhatsApp:** Meta Cloud API (default) or Twilio (alternative)
- **LLM Providers:** OpenAI (GPT-4) or Groq (Llama 3.3-70B) – configurable
- **Embedding Service:** Local (SentenceTransformers) or Remote (Hugging Face Spaces)
- **20+ Sources:** NDPC, TETFund, CBN, FME, NITDA, PTDF, Commonwealth, etc.

---

### Slide 11 – Design Patterns & Best Practices
- **Strategy Pattern:** WhatsApp sender abstraction (Meta/Twilio)
- **Pipeline Pattern:** Clear separation of crawl → ingest → AI → delivery
- **Async Operations:** FastAPI async endpoints, Playwright async crawling
- **Configuration Management:** Pydantic settings, environment variables, YAML sources
- **Error Handling:** Retry logic, graceful degradation, logging

---

### Slide 12 – Performance & Scalability
- **Connection Pooling:** SQLAlchemy connection pool for database efficiency
- **Vector Search:** HNSW indexing in ChromaDB for fast similarity search
- **Caching:** Proposal PDFs cached to avoid regeneration
- **Embedding Separation:** Optional remote service reduces memory footprint
- **Deduplication:** In-memory hash sets (O(1) lookup)

---

### Slide 13 – Known Limitations & Future Work
- **Current Limitations:** Twilio PDF support, ChromaDB deletion, opportunity ranking algorithm
- **Future Enhancements:** Multi-language support, email delivery, web dashboard, opportunity scoring algorithm, PDF cleanup automation, improved error messages

---

### Slide 14 – Demo & Q&A
- **Live Demo:** Show WhatsApp interaction (digest, query, proposal request)
- **Architecture Diagram:** Visual overview of system components
- **Metrics:** Number of sources, documents processed, opportunities extracted
- **Questions & Answers**

---

**Total Slides: 14** (suitable for 10-15 minute presentation)

