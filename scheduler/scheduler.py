"""Cron scheduler for automated crawling."""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from config import settings
import requests

logger = logging.getLogger(__name__)


class Scheduler:
    """Cron scheduler for triggering crawl jobs."""
    
    def __init__(self):
        """Initialize scheduler."""
        self.scheduler = BackgroundScheduler()
        self.api_url = f"http://{settings.api_host}:{settings.api_port}"
    
    def trigger_cron_job(self):
        """Trigger cron job via API."""
        try:
            url = f"{self.api_url}/cron/run"
            response = requests.post(url, timeout=600)  # 10 minute timeout
            response.raise_for_status()
            logger.info(f"Cron job triggered successfully: {response.json()}")
        except Exception as e:
            logger.error(f"Error triggering cron job: {e}")
    
    def start(self):
        """Start scheduler."""
        # Parse cron schedule
        cron_parts = settings.cron_schedule.split()
        if len(cron_parts) == 5:
            minute, hour, day, month, day_of_week = cron_parts
            self.scheduler.add_job(
                self.trigger_cron_job,
                trigger=CronTrigger(
                    minute=minute,
                    hour=hour,
                    day=day,
                    month=month,
                    day_of_week=day_of_week
                ),
                id="crawl_job",
                name="Crawl and Digest Job"
            )
        else:
            # Default: daily at 6 AM
            self.scheduler.add_job(
                self.trigger_cron_job,
                trigger=CronTrigger(hour=6, minute=0),
                id="crawl_job",
                name="Crawl and Digest Job"
            )
        
        self.scheduler.start()
        logger.info(f"Scheduler started with schedule: {settings.cron_schedule}")
    
    def stop(self):
        """Stop scheduler."""
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")

