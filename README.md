# AI Agent for Web-Scraping Nigerian Grants/Scholarships/Policies

A production-ready Agentic Research Assistant that monitors Nigerian sources for grants, scholarships, and education/research policies. The system uses RAG (Retrieval-Augmented Generation) to provide accurate, citation-grounded answers via WhatsApp.

## Features

- **Automated Crawling**: Monitors multiple Nigerian sources (NDPC, TETFund, CBN, FME, etc.) using Playwright and RSS feeds
- **Change Detection**: Uses Llama 3 to detect and summarize changes in policies/grants
- **Opportunity Extraction**: Automatically extracts grants, scholarships, and policy opportunities
- **RAG-powered Q&A**: Answers user queries with citations using ChromaDB vector store
- **WhatsApp Integration**: Sends weekly digests and answers queries via WhatsApp Cloud API
- **Proposal Generation**: Generates one-pager PDF proposals for opportunities
- **Deduplication**: Prevents duplicate documents using exact and near-duplicate detection

## Architecture

```
Cron → Crawler → Deduper → Ingest → RAG (Chroma) → Change Detector → 
Opportunity Extractor → Proposal Writer → Digest Builder → WhatsApp
```

## Setup

### Prerequisites

- Python 3.9+
- MySQL 8.0+ (or SQLite for development)
- Playwright browsers (installed automatically)
- WhatsApp Business API access

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd ai-agent-researcher
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
playwright install chromium
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Set up database**
```bash
# Create MySQL database
mysql -u root -p
CREATE DATABASE nigerian_grants_db;

# Run migrations
alembic upgrade head
```

6. **Initialize database tables**
```bash
python -c "from database.session import init_db; init_db()"
```

## Configuration

Edit `.env` file with your configuration:

```env
# Database
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/nigerian_grants_db

# WhatsApp Cloud API
WHATSAPP_VERIFY_TOKEN=your_verify_token_here
WHATSAPP_ACCESS_TOKEN=your_access_token_here
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id_here

# LLM Configuration
LLM_PROVIDER=openai
LLM_MODEL=gpt-4-turbo-preview
LLM_API_KEY=your_api_key_here

# RAG Configuration
CHROMA_PERSIST_DIR=./chroma_db
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

## Running the Application

### Start the API server
```bash
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### Start the scheduler (optional, for automated crawling)
```bash
python -m scheduler.scheduler
```

Or run both together:
```bash
python run.py
```

## API Endpoints

### Health Check
```bash
GET /health
```

### WhatsApp Webhook
```bash
GET /webhook?hub.mode=subscribe&hub.verify_token=TOKEN&hub.challenge=CHALLENGE
POST /webhook
```

### Manual Cron Trigger
```bash
POST /cron/run
```

## WhatsApp Usage

### Commands

- **digest** - Get weekly digest of top 3 opportunities
- **1/2/3** - Get full one-pager PDF for opportunity 1, 2, or 3
- **STOP** - Unsubscribe from notifications
- **SUBSCRIBE** - Subscribe to notifications
- **Any question** - Ask a question about grants/scholarships/policies

### Example Interactions

**User**: `digest`

**Agent**: 
```
1) TETFund Research Call — Deadline: 2026-01-15
   Action: submit 2-pg CN
   https://tetfund.gov.ng/...

2) NDPC Education Policy Update — Deadline: 2025-12-30
   Action: Update onboarding forms
   https://ndpc.gov.ng/...

3) AI4D Africa Scholarship — Deadline: 2026-02-20
   Action: Apply online
   https://ai4d.ai/...

Reply 1/2/3 for full one-pager + calendar invite.
```

**User**: `2`

**Agent**: Sends PDF proposal for item 2

**User**: `policy update NDPC undergraduate research`

**Agent**:
```
Here's what NDPC changed (08 Nov 2025):
• Added KYC for student research stipends
• New compliance deadline: 30 Dec 2025

Actions: Update onboarding forms; notify departments.

Citations:
[1] ndpc.gov.ng/update#4.2
[2] ndpc.gov.ng/update#dates
```

## Project Structure

```
.
├── agents/              # AI agents (change detector, proposal writer, router)
├── api/                 # FastAPI application
├── crawler/             # Web crawler (Playwright + RSS)
├── database/            # Database models and session
├── dedupe/              # Deduplication logic
├── ingest/              # Document ingestion pipeline
├── rag/                 # RAG store and chunking
├── scheduler/           # Cron scheduler
├── tools/               # Utilities (PDF, WhatsApp, ICS)
├── tests/               # Pytest tests
├── alembic/             # Database migrations
└── README.md
```

## Testing

Run tests:
```bash
pytest tests/ -v
```

Run with coverage:
```bash
pytest tests/ --cov=. --cov-report=html
```

## Demo Plan

### 2-Minute Demo Script

1. **Setup (30s)**
   - Show project structure
   - Explain architecture

2. **Crawl & Ingest (30s)**
   - Trigger manual crawl: `POST /cron/run`
   - Show logs of crawling sources
   - Show database entries

3. **WhatsApp Interaction (60s)**
   - Send "digest" via WhatsApp
   - Show digest response with 3 items
   - Send "2" to request proposal PDF
   - Show PDF generation and delivery
   - Ask a question: "phd scholarships STEM 2026"
   - Show RAG-powered answer with citations

4. **Wrap-up (30s)**
   - Show change detection logs
   - Show RAG store contents
   - Explain scheduling and automation

## Development

### Adding New Sources

Edit `crawler/sources.yaml`:

```yaml
sources:
  - name: New Source
    url: https://example.com
    type: html  # or rss
    schedule_cron: "0 6 * * *"
    active: true
    selectors:
      title: h1
      content: .main-content
```

### Customizing Prompts

Edit prompts in `agents/`:
- `change_detector.py` - Change detection prompt
- `opportunity_extractor.py` - Opportunity extraction prompt
- `proposal_writer.py` - Proposal writing prompt

## Troubleshooting

### Playwright Issues
```bash
playwright install chromium
```

### Database Connection Issues
- Check MySQL is running
- Verify DATABASE_URL in .env
- Check user permissions

### WhatsApp Webhook Issues
- Verify webhook URL is publicly accessible (use ngrok for local testing)
- Check verify token matches
- Verify access token has correct permissions

### LLM API Issues
- Check API key is valid
- Verify base URL is correct
- Check rate limits

## License

MIT

## Contributing

Contributions welcome! Please open an issue or submit a pull request.

## Support

For issues and questions, please open an issue on GitHub.

