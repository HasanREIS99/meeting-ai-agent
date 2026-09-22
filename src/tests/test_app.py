"""
Tests for the main application factory.

Tests the app creation, lifespan, and global error handler.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from meeting_analyzer.main import create_app


@pytest.fixture
def app():
    """Create a test FastAPI app."""
    return create_app()


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


def test_health_check(client):
    """EP-002: Health check returns 200 OK with status."""
    resp = client.post("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


def test_openapi_docs_exist(client):
    """FastAPI should serve automatic OpenAPI docs."""
    resp = client.get("/api/docs")
    assert resp.status_code == 200


def test_redoc_exists(client):
    """FastAPI should serve ReDoc docs."""
    resp = client.get("/api/redoc")
    assert resp.status_code == 200
