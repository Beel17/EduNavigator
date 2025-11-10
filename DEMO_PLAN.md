# Demo Plan - 2-Minute Walkthrough

## Overview
This document outlines a 2-minute demonstration of the Nigerian Grants Agent system.

## Demo Flow

### 1. Setup & Architecture (30 seconds)
- **Show project structure**: Navigate through key directories
  - `agents/` - AI agents (change detector, proposal writer, router)
  - `crawler/` - Web scraping (Playwright + RSS)
  - `rag/` - RAG store with ChromaDB
  - `api/` - FastAPI application
  - `database/` - MySQL models

- **Explain architecture**:
  ```
  Cron → Crawler → Deduper → Ingest → RAG → 
  Change Detector → Opportunity Extractor → 
  Proposal Writer → Digest Builder → WhatsApp
  ```

### 2. Crawl & Ingest (30 seconds)
- **Trigger manual crawl**:
  ```bash
  curl -X POST http://localhost:8000/cron/run
  ```

- **Show logs**:
  - Crawler fetching from sources (NDPC, TETFund, etc.)
  - Deduplication in action
  - Documents being ingested
  - Opportunities being extracted

- **Show database**:
  - New documents in `documents` table
  - Opportunities in `opportunities` table
  - Versions in `doc_versions` table

### 3. WhatsApp Interactions (60 seconds)

#### 3.1 Digest Request
- **User sends**: `digest`
- **Agent responds** with:
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

#### 3.2 Proposal Request
- **User sends**: `2`
- **Agent**:
  - Retrieves opportunity #2 from database
  - Queries RAG for relevant chunks
  - Generates proposal using LLM
  - Creates PDF using WeasyPrint
  - Sends PDF via WhatsApp
  - Generates ICS calendar file (optional)

#### 3.3 Query Request
- **User sends**: `policy update NDPC undergraduate research`
- **Agent**:
  - Queries RAG store
  - Retrieves relevant chunks with citations
  - Generates answer using LLM
  - Formats response with citations
  - Sends answer via WhatsApp:
    ```
    Here's what NDPC changed (08 Nov 2025):
    • Added KYC for student research stipends
    • New compliance deadline: 30 Dec 2025
    
    Actions: Update onboarding forms; notify departments.
    
    Citations:
    [1] ndpc.gov.ng/update#4.2
    [2] ndpc.gov.ng/update#dates
    ```

### 4. Wrap-up (30 seconds)
- **Show change detection**: Display change logs from `changes` table
- **Show RAG store**: Display ChromaDB collection with embedded chunks
- **Show scheduling**: Explain cron job configuration
- **Show automation**: Explain how system runs daily at 6 AM UTC

## Key Features to Highlight

1. **Automated Crawling**: Monitors multiple Nigerian sources
2. **Change Detection**: Uses LLM to detect and summarize changes
3. **RAG-powered Q&A**: Grounded answers with citations
4. **WhatsApp Integration**: Natural language interface
5. **Proposal Generation**: One-pager PDFs for opportunities
6. **Deduplication**: Prevents duplicate documents

## Technical Highlights

- **Llama 3**: For change detection and proposal writing
- **ChromaDB**: Vector store for RAG
- **Playwright**: Headless browser for dynamic content
- **FastAPI**: Modern async API framework
- **MySQL**: Production database
- **WhatsApp Cloud API**: Business messaging

## Next Steps

1. **Scale**: Add more sources
2. **Enhance**: Improve LLM prompts
3. **Monitor**: Add monitoring and alerts
4. **Deploy**: Deploy to production

## Troubleshooting Tips

- If webhook fails: Check ngrok tunnel
- If LLM fails: Check API key and rate limits
- If crawling fails: Check network and selectors
- If RAG fails: Check ChromaDB initialization

