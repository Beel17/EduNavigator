"""Main application runner."""
import logging
import uvicorn
from threading import Thread
from config import settings
from scheduler.scheduler import Scheduler

logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)


def run_scheduler():
    """Run scheduler in separate thread."""
    scheduler = Scheduler()
    scheduler.start()
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.stop()


def run_api():
    """Run API server."""
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.app_env == "development"
    )


if __name__ == "__main__":
    logger.info("Starting application...")
    
    # Start scheduler in background thread
    scheduler_thread = Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    # Run API server
    run_api()

