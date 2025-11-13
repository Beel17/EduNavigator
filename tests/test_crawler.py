"""Tests for crawler."""
import pytest
from crawler.sources import load_sources, SourceConfig


def test_load_sources():
    """Test loading sources from YAML."""
    sources = load_sources()
    assert len(sources) > 0
    assert all(isinstance(source, SourceConfig) for source in sources)
    assert all(source.url for source in sources)
    assert all(source.name for source in sources)


def test_source_config():
    """Test source configuration."""
    source = SourceConfig(
        name="Test Source",
        url="https://education.gov.ng/2026-2027-commonwealth-scholarships/",
        source_type="html",
        schedule_cron="0 6 * * *",
        active=True
    )
    
    assert source.name == "Test Source"
    assert source.url == "https://education.gov.ng/2026-2027-commonwealth-scholarships/"
    assert source.type == "html"
    assert source.active is True

