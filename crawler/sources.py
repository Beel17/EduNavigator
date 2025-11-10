"""Source configuration management."""
import yaml
from typing import List, Dict, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class SourceConfig:
    """Source configuration."""
    def __init__(
        self,
        name: str,
        url: str,
        source_type: str = "html",
        schedule_cron: str = "0 6 * * *",
        active: bool = True,
        selectors: Optional[Dict[str, str]] = None,
        filters: Optional[Dict[str, str]] = None
    ):
        self.name = name
        self.url = url
        self.type = source_type
        self.schedule_cron = schedule_cron
        self.active = active
        self.selectors = selectors or {}
        self.filters = filters or {}


def load_sources(config_path: Optional[str] = None) -> List[SourceConfig]:
    """Load sources from YAML file."""
    if config_path is None:
        config_path = Path(__file__).parent / "sources.yaml"
    else:
        config_path = Path(config_path)
    
    if not config_path.exists():
        logger.warning(f"Sources config not found at {config_path}, using defaults")
        return []
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        sources = []
        for source_data in data.get("sources", []):
            source = SourceConfig(
                name=source_data["name"],
                url=source_data["url"],
                source_type=source_data.get("type", "html"),
                schedule_cron=source_data.get("schedule_cron", "0 6 * * *"),
                active=source_data.get("active", True),
                selectors=source_data.get("selectors"),
                filters=source_data.get("filters")
            )
            sources.append(source)
        
        logger.info(f"Loaded {len(sources)} sources from {config_path}")
        return sources
    except Exception as e:
        logger.error(f"Error loading sources: {e}")
        return []

