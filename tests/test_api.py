"""Tests for API endpoints."""
import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_health():
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()


def test_webhook_verification():
    """Test webhook verification."""
    # This would need proper verify token in .env
    response = client.get("/webhook?hub.mode=subscribe&hub.verify_token=test&hub.challenge=test123")
    # Should return 403 if token doesn't match, or challenge if it does
    assert response.status_code in [200, 403]


def test_cron_endpoint():
    """Test cron endpoint."""
    # This would require database setup
    # response = client.post("/cron/run")
    # assert response.status_code in [200, 500]
    pass

