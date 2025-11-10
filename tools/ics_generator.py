"""ICS calendar file generator."""
from ics import Calendar, Event
from datetime import datetime
from typing import Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def generate_ics(
    title: str,
    deadline: datetime,
    description: str = "",
    url: str = "",
    output_path: Optional[str] = None
) -> str:
    """
    Generate ICS calendar file for deadline.
    
    Args:
        title: Event title
        deadline: Deadline datetime
        description: Event description
        url: Related URL
        output_path: Optional output file path
    
    Returns:
        Path to generated ICS file
    """
    try:
        cal = Calendar()
        event = Event()
        event.name = title
        event.begin = deadline
        event.end = deadline  # Same as begin for deadline events
        event.description = description + (f"\n\nURL: {url}" if url else "")
        event.url = url
        
        cal.events.add(event)
        
        if output_path is None:
            output_path = f"./storage/ics/{title.replace(' ', '_')}_{deadline.strftime('%Y%m%d')}.ics"
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.writelines(cal)
        
        logger.info(f"Generated ICS file: {output_path}")
        return str(output_path)
    except Exception as e:
        logger.error(f"Error generating ICS file: {e}")
        raise

