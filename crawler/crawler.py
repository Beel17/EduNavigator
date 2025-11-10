"""Web crawler using Playwright and RSS."""
import asyncio
import hashlib
import time
import logging
from typing import Optional, List
from datetime import datetime
import feedparser
import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Browser, Page
from config import settings
from tools.schemas import CrawlOut
from crawler.sources import SourceConfig

logger = logging.getLogger(__name__)


class Crawler:
    """Web crawler for scraping Nigerian grants/scholarships/policies."""
    
    def __init__(self):
        self.user_agent = settings.crawler_user_agent
        self.timeout = settings.crawler_timeout * 1000  # Convert to milliseconds
        self.max_retries = settings.crawler_max_retries
        self.backoff_factor = settings.crawler_backoff_factor
        self.browser: Optional[Browser] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.browser:
            await self.browser.close()
    
    def _calculate_hash(self, content: str) -> str:
        """Calculate SHA256 hash of content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()
    
    def _retry_with_backoff(self, func, *args, **kwargs):
        """Retry function with exponential backoff."""
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                wait_time = self.backoff_factor ** attempt
                logger.warning(f"Retry {attempt + 1}/{self.max_retries} after {wait_time}s: {e}")
                time.sleep(wait_time)
        return None
    
    async def crawl_rss(self, source: SourceConfig) -> List[CrawlOut]:
        """Crawl RSS feed."""
        results = []
        try:
            logger.info(f"Crawling RSS feed: {source.url}")
            feed = feedparser.parse(source.url)
            
            for entry in feed.entries:
                try:
                    url = entry.get("link", "")
                    title = entry.get("title", "Untitled")
                    content = entry.get("description", "") or entry.get("summary", "")
                    
                    # Extract text from HTML if needed
                    if content:
                        soup = BeautifulSoup(content, "html.parser")
                        content = soup.get_text(strip=True)
                    
                    http_hash = self._calculate_hash(content)
                    fetched_at = datetime.utcnow().isoformat()
                    
                    result = CrawlOut(
                        url=url,
                        title=title,
                        fetched_at=fetched_at,
                        http_hash=http_hash,
                        mime="text/html",
                        raw_text=content
                    )
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error processing RSS entry: {e}")
                    continue
            
            logger.info(f"Crawled {len(results)} items from RSS feed")
            return results
        except Exception as e:
            logger.error(f"Error crawling RSS feed {source.url}: {e}")
            return []
    
    async def crawl_html(self, source: SourceConfig) -> List[CrawlOut]:
        """Crawl HTML page using Playwright."""
        results = []
        try:
            logger.info(f"Crawling HTML page: {source.url}")
            
            if not self.browser:
                raise RuntimeError("Browser not initialized")
            
            page = await self.browser.new_page()
            await page.set_extra_http_headers({"User-Agent": self.user_agent})
            
            try:
                await page.goto(source.url, wait_until="networkidle", timeout=self.timeout)
                await page.wait_for_timeout(2000)  # Wait for dynamic content
                
                # Extract title
                title_selectors = source.selectors.get("title", "h1, title")
                title = await self._extract_text(page, title_selectors) or "Untitled"
                
                # Extract content
                content_selectors = source.selectors.get("content", "body")
                content = await self._extract_text(page, content_selectors) or ""
                
                # Get full HTML for storage
                html_content = await page.content()
                
                http_hash = self._calculate_hash(html_content)
                fetched_at = datetime.utcnow().isoformat()
                
                result = CrawlOut(
                    url=source.url,
                    title=title,
                    fetched_at=fetched_at,
                    http_hash=http_hash,
                    mime="text/html",
                    raw_text=content
                )
                results.append(result)
                
            finally:
                await page.close()
            
            logger.info(f"Crawled HTML page: {source.url}")
            return results
        except Exception as e:
            logger.error(f"Error crawling HTML page {source.url}: {e}")
            return []
    
    async def _extract_text(self, page: Page, selectors: str) -> str:
        """Extract text using CSS selectors."""
        try:
            # Try first selector
            for selector in selectors.split(","):
                selector = selector.strip()
                try:
                    element = await page.query_selector(selector)
                    if element:
                        text = await element.inner_text()
                        if text:
                            return text.strip()
                except Exception:
                    continue
            return ""
        except Exception as e:
            logger.warning(f"Error extracting text with selectors {selectors}: {e}")
            return ""
    
    async def crawl(self, source: SourceConfig) -> List[CrawlOut]:
        """Crawl a source based on its type."""
        if source.type == "rss":
            return await self.crawl_rss(source)
        elif source.type == "html":
            return await self.crawl_html(source)
        else:
            logger.warning(f"Unknown source type: {source.type}")
            return []
    
    async def crawl_pdf(self, url: str) -> Optional[CrawlOut]:
        """Download and extract text from PDF."""
        try:
            logger.info(f"Downloading PDF: {url}")
            response = requests.get(url, timeout=self.timeout, headers={"User-Agent": self.user_agent})
            response.raise_for_status()
            
            # Save PDF blob
            pdf_content = response.content
            http_hash = self._calculate_hash(pdf_content.decode("latin-1", errors="ignore"))
            
            # Extract text using pypdf2
            from tools.pdf_extractor import extract_text_from_pdf_bytes
            text = extract_text_from_pdf_bytes(pdf_content)
            
            fetched_at = datetime.utcnow().isoformat()
            
            return CrawlOut(
                url=url,
                title=url.split("/")[-1],
                fetched_at=fetched_at,
                http_hash=http_hash,
                mime="application/pdf",
                raw_text=text
            )
        except Exception as e:
            logger.error(f"Error crawling PDF {url}: {e}")
            return None

