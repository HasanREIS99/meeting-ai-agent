"""
Tests for the analysis router (EP-001).

Tests file upload, validation errors, and LLM error handling at the
HTTP endpoint level.
"""

from __future__ import annotations

from io import BytesIO
from typing import Any

import pytest
from starlette.testclient import TestClient

from meeting_analyzer.main import create_app
from meeting_analyzer.analyzer import TranscriptAnalyzer
from meeting_analyzer.models import ActionItem, TranscriptResult, TopicCluster
from datetime import datetime


def _make_unauthed():
    """App with SessionMiddleware (creates empty session → 401 for protected)."""
    app = create_app()
    return app


def _make_authed():
    """App WITHOUT SessionMiddleware; our wrapper injects session directly.

    SessionMiddleware replaces scope["session"] at the ASGI level, so any
    data we inject *before* it runs gets overwritten.  The reliable
    workaround is to remove SessionMiddleware from the FastAPI stack
    (so nothing touches scope["session"]) and inject a plain dict in our
    ASGI wrapper.  Request.session reads scope["session"] directly — a
    plain dict satisfies the assertion and works with .get().
    """
    from starlette.middleware.sessions import SessionMiddleware
    from starlette.types import ASGIApp, Receive, Scope, Send

    app = create_app()
    # Strip SessionMiddleware so our wrapper is the only session source
    app.user_middleware = [
        m
        for m in app.user_middleware
        if not (hasattr(m, "cls") and m.cls is SessionMiddleware)
    ]
    app.middleware_stack = None
    app.build_middleware_stack()

    class SessionInjector:
        def __init__(self, app: ASGIApp) -> None:
            self._app = app

        async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
            if scope["type"] == "http":
                scope.setdefault("session", {})
                scope["session"]["user"] = {
                    "sub": "123",
                    "email": "test@example.com",
                    "display_name": "Test User",
                }
            await self._app(scope, receive, send)

    return TestClient(SessionInjector(app), raise_server_exceptions=False)


@pytest.fixture
def unauthed_app():
    return _make_unauthed()


@pytest.fixture
def authed_client(unauthed_app):
    return _make_authed()


def test_upload_and_analyze(authed_client: TestClient, monkeypatch: Any):
    """Happy path: upload valid transcript and receive analysis (EP-001)."""

    async def mock_analyze(self, filename, content, metadata):
        return TranscriptResult(
            meeting_title="Sprint Planning",
            language="en",
            topic_clusters=[
                TopicCluster(
                    title="Sprint Planning",
                    summary="Discussed sprint backlog and blockers.",
                    confidence=0.9,
                    keywords=["sprint", "planning"],
                ),
            ],
            action_items=[
                ActionItem(
                    description="Update backlog",
                    assignee="John",
                    confidence=0.85,
                ),
            ],
            processing_time=0.5,
            markdown_content="# Sprint Planning",
            generated_at=datetime.utcnow(),
        )

    monkeypatch.setattr(TranscriptAnalyzer, "analyze", mock_analyze)

    content = b"Meeting started at 10am. We discussed sprint planning."

    resp = authed_client.post(
        "/api/v1/analyze",
        files={
            "file": ("meeting.txt", BytesIO(content), "text/plain"),
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert "topic_clusters" in data
    assert "action_items" in data
    assert "markdown_content" in data
    assert "processing_time" in data
    assert "language" in data
    assert len(data["topic_clusters"]) == 1


def test_upload_rejects_non_txt(authed_client: TestClient):
    """FR-002: Non-.txt files return 400."""
    resp = authed_client.post(
        "/api/v1/analyze",
        files={
            "file": ("meeting.pdf", b"%PDF-1.4", "application/pdf"),
        },
    )

    assert resp.status_code == 400
    data = resp.json()
    assert "Validation Failed" in data.get("title", "")


def test_upload_rejects_empty_file(authed_client: TestClient):
    """FR-017: Empty files return 400."""
    resp = authed_client.post(
        "/api/v1/analyze",
        files={
            "file": ("empty.txt", b"", "text/plain"),
        },
    )

    assert resp.status_code == 400
    data = resp.json()
    assert "Validation failed" in data.get("detail", "").lower() or data.get(
        "status"
    ) == 400


def test_validate_endpoint(authed_client: TestClient):
    """EP-003: Pre-upload validation returns correct result."""
    content = b"This is a valid meeting transcript."

    resp = authed_client.post(
        "/api/v1/validate",
        files={
            "file": ("meeting.txt", BytesIO(content), "text/plain"),
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["errors"] == []


def test_validate_rejects_pdf(authed_client: TestClient):
    """EP-003: Validation rejects non-.txt files.

    The endpoint returns HTTP 200 with a JSON body containing
    ``{"valid": false, ...}`` so that browsers can parse the error
    response (4xx responses block JSON body parsing).
    """
    resp = authed_client.post(
        "/api/v1/validate",
        files={
            "file": ("meeting.pdf", b"%PDF-1.4", "application/pdf"),
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is False
    assert len(data["errors"]) > 0
