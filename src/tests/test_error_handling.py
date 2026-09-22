"""
Tests for error handling and reliability (STORY-004-003, FR-015).

Covers:
- RFC 7807 Problem Details error responses
- Timeout handling (HTTP 408)
- LLM provider failure handling (502 + retry-after)
- Validation error handling (400)
- Performance monitoring
- Secure logging (sensitive filter)
"""

from __future__ import annotations

import json
import logging
from io import BytesIO
from typing import Any

import pytest
from starlette.testclient import TestClient
from starlette.types import ASGIApp, Receive, Scope, Send

from meeting_analyzer.error_handling import (
    PerformanceMonitor,
    create_error_response,
)
from meeting_analyzer.main import SensitiveFilter, create_app


# ── Helpers ───────────────────────────────────────────────────────


def _make_authed(app):
    """Wrap an app with an ASGI middleware that injects user into the scope."""
    from starlette.middleware.sessions import SessionMiddleware

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
                scope.setdefault("session", {})["user"] = {
                    "sub": "123",
                    "email": "test@example.com",
                    "display_name": "Test User",
                }
            await self._app(scope, receive, send)

    return TestClient(SessionInjector(app), raise_server_exceptions=False)


# ── create_error_response ─────────────────────────────────────────


class TestCreateErrorResponse:
    """RFC 7807 Problem Details response creation."""

    def test_basic_error(self):
        """Basic error response has required fields."""
        resp = create_error_response(400, "validation_error", "Bad Request", "Invalid input")
        assert resp.status_code == 400
        body = json.loads(resp.body)
        assert body["type"] == "validation_error"
        assert body["title"] == "Bad Request"
        assert body["status"] == 400
        assert body["detail"] == "Invalid input"
        assert "timestamp" in body

    def test_retry_after_header(self):
        """502 errors include Retry-After header."""
        resp = create_error_response(502, "llm_error", "Unavailable", "Service down", retry_after=30)
        assert resp.status_code == 502
        assert resp.headers.get("Retry-After") == "30"


# ── PerformanceMonitor ────────────────────────────────────────────


class TestPerformanceMonitor:
    """Performance metric logging."""

    def test_normal_request(self, caplog):
        """Normal request logs at INFO level."""
        caplog.set_level("INFO")
        monitor = PerformanceMonitor(slow_threshold_seconds=120.0)
        monitor.log("meeting.txt", 0.5, "success")
        assert any("meeting.txt" in r.message for r in caplog.records)
        assert any(r.levelno == 20 for r in caplog.records)

    def test_slow_request(self, caplog):
        """Slow request triggers a warning."""
        caplog.set_level("INFO")
        monitor = PerformanceMonitor(slow_threshold_seconds=1.0)
        monitor.log("big_meeting.txt", 5.0, "success")
        assert any(r.levelno == 30 for r in caplog.records)
        assert any("Slow request" in r.message for r in caplog.records)


# ── Exception handler tests ───────────────────────────────────────


class TestExceptionHandlers:
    """Test that exception handlers produce correct responses."""

    def test_validation_error_returns_400(self):
        """ValueError → 400 with Problem Details."""
        app = create_app()
        client = _make_authed(app)
        resp = client.post(
            "/api/v1/analyze",
            files={"file": ("meeting.pdf", b"%PDF", "application/pdf")},
            headers={"Accept": "application/json"},
        )
        assert resp.status_code == 400
        data = resp.json()
        assert data["status"] == 400
        assert "Validation Failed" in data.get("title", "")

    def test_llm_error_returns_502(self):
        """RuntimeError from LLM → 502 with retry-after header."""
        from unittest.mock import AsyncMock
        from meeting_analyzer.analyzer import TranscriptAnalyzer

        async def mock_fail(*args, **kwargs):
            raise RuntimeError("LLM provider down")

        app = create_app()
        client = _make_authed(app)
        with pytest.MonkeyPatch().context() as mp:
            mp.setattr(TranscriptAnalyzer, "analyze", mock_fail)
            resp = client.post(
                "/api/v1/analyze",
                files={"file": ("meeting.txt", BytesIO(b"content"), "text/plain")},
                headers={"Accept": "application/json"},
            )

        assert resp.status_code == 502
        data = resp.json()
        assert data["status"] == 502
        assert "Retry-After" in resp.headers

    def test_generic_exception_returns_500(self):
        """Unexpected exceptions → 500."""
        from unittest.mock import AsyncMock
        from meeting_analyzer.analyzer import TranscriptAnalyzer

        async def mock_generic_fail(*args, **kwargs):
            raise ZeroDivisionError("div by zero")

        app = create_app()
        client = _make_authed(app)
        with pytest.MonkeyPatch().context() as mp:
            mp.setattr(TranscriptAnalyzer, "analyze", mock_generic_fail)
            resp = client.post(
                "/api/v1/analyze",
                files={"file": ("meeting.txt", BytesIO(b"content"), "text/plain")},
                headers={"Accept": "application/json"},
            )

        assert resp.status_code == 500
        data = resp.json()
        assert data["status"] == 500
        assert "Internal Server Error" in data.get("title", "")


# ── Secure logging ────────────────────────────────────────────────


class TestSensitiveFilter:
    """Ensure sensitive transcript content is filtered from logs."""

    @staticmethod
    def _make_log_record(msg: str) -> logging.LogRecord:
        """Create a LogRecord for testing the filter."""
        return logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=msg,
            args=None,
            exc_info=None,
        )

    def test_filters_transcript_keyword(self):
        """Log lines containing 'transcript' are redacted."""
        filt = SensitiveFilter()
        record = self._make_log_record("Processing transcript content: Hello world")
        assert filt.filter(record) is True  # Log is not blocked
        assert "[REDACTED]" in record.msg
        assert "transcript" not in record.msg

    def test_filters_action_item_keyword(self):
        """Log lines containing 'action item' are redacted."""
        filt = SensitiveFilter()
        record = self._make_log_record("Extracted action item: update the board")
        assert filt.filter(record) is True
        assert "action item" not in record.msg

    def test_allows_non_sensitive_log(self):
        """Non-sensitive log lines pass through unchanged."""
        filt = SensitiveFilter()
        record = self._make_log_record("Server started on port 8000")
        assert filt.filter(record) is True
        assert "Server started on port 8000" == record.msg


# ── TimeoutMiddleware enforcement (NFR-P-001, NFR-P-002) ──────────


class TestTimeoutMiddlewareEnforcement:
    """The per-request budget must abort the handler, not merely log it.

    Regression: the middleware used to time the request and warn when it
    overran, so an unresponsive LLM provider (three retried calls, each
    with its own timeout) held the connection for 915s against a 300s
    limit before the client saw an error.
    """

    @staticmethod
    def _app_with_handler(timeout_seconds: float, handler):
        from fastapi import FastAPI

        from meeting_analyzer.error_handling import TimeoutMiddleware

        app = FastAPI()
        app.add_middleware(TimeoutMiddleware, timeout_seconds=timeout_seconds)
        app.get("/slow")(handler)
        return TestClient(app, raise_server_exceptions=False)

    def test_slow_handler_is_aborted_with_408(self):
        """A handler that overruns the budget returns 408, not its result."""
        import asyncio

        async def slow():
            await asyncio.sleep(5)
            return {"never": "returned"}

        client = self._app_with_handler(0.2, slow)
        resp = client.get("/slow")

        assert resp.status_code == 408
        body = resp.json()
        assert body["type"] == "timeout_error"
        assert body["status"] == 408

    def test_fast_handler_passes_through(self):
        """A handler inside the budget is unaffected."""

        async def fast():
            return {"ok": True}

        client = self._app_with_handler(30, fast)
        resp = client.get("/slow")

        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
