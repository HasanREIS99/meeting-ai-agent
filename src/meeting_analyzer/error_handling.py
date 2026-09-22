"""
Error handling and reliability middleware (STORY-004-003, FR-015).

Implements:
- RFC 7807 Problem Details error responses
- Timeout handling (HTTP 408)
- Retry-after headers on transient LLM failures
- Secure logging (no transcript content)
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class TimeoutMiddleware(BaseHTTPMiddleware):
    """Enforce per-request timeout and return 408 when exceeded.

    NFR-P-001, NFR-P-002: Transcript processing must complete within
    the configured timeout (default 120 s).  The middleware aborts the
    handler once the budget is spent and answers 408.

    The budget is for the *whole* request, not one LLM call.  The LLM
    layer retries a failed call up to three times, each with its own
    per-call timeout, so without a hard ceiling here a single upload can
    occupy the connection for a multiple of ``timeout_seconds`` -- an
    unresponsive provider produced a 915 s request against a 300 s
    limit.  ``asyncio.wait_for`` cancels the handler instead.
    """

    def __init__(self, app, timeout_seconds: int = 120):
        super().__init__(app)
        self.timeout_seconds = timeout_seconds

    async def dispatch(self, request: Request, call_next):
        start = time.monotonic()

        try:
            response = await asyncio.wait_for(
                call_next(request), timeout=self.timeout_seconds,
            )
            elapsed = time.monotonic() - start

            # Log processing time for performance monitoring
            logger.info(
                "Completed %s %s in %.2fs (status=%d)",
                request.method,
                request.url.path,
                elapsed,
                response.status_code,
            )

            return response

        except (asyncio.TimeoutError, TimeoutError):
            elapsed = time.monotonic() - start
            logger.warning(
                "Request timed out: %s %s aborted after %.2fs (limit %ds)",
                request.method,
                request.url.path,
                elapsed,
                self.timeout_seconds,
            )
            return self._timeout_response(request)

        except Exception:
            elapsed = time.monotonic() - start
            if elapsed > self.timeout_seconds:
                return self._timeout_response(request)
            raise

    def _timeout_response(self, request: Request) -> JSONResponse:
        """Build the RFC 7807 408 body (FR-015)."""
        return JSONResponse(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            content={
                "type": "timeout_error",
                "title": "Request Timeout",
                "status": 408,
                "detail": (
                    "Processing exceeded the configured timeout. "
                    "Please try again."
                ),
                "instance": str(request.url),
            },
        )


class PerformanceMonitor:
    """Records performance metrics for analysis requests.

    Used by the analysis router to log processing time and detect
    slow requests (>2 minutes triggers a warning).
    """

    def __init__(self, slow_threshold_seconds: float = 120.0):
        self._slow_threshold = slow_threshold_seconds

    def log(self, filename: str, processing_time: float, status: str):
        """Record a performance metric entry.

        Args:
            filename: Upload filename (no content).
            processing_time: Time in seconds to process the transcript.
            status: "success" or "error".
        """
        if processing_time > self._slow_threshold:
            logger.warning(
                "Slow request: '%s' processed in %.2fs (threshold: %ds) — %s",
                filename,
                processing_time,
                self._slow_threshold,
                status,
            )
        else:
            logger.info(
                "Request complete: '%s' in %.2fs — %s",
                filename,
                processing_time,
                status,
            )


def create_error_response(
    status_code: int,
    error_type: str,
    title: str,
    detail: str,
    retry_after: Optional[int] = None,
) -> JSONResponse:
    """Create an RFC 7807 Problem Details response.

    FR-015: Standardized error responses for all failure modes.
    """
    body = {
        "type": error_type,
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": f"{datetime.now(timezone.utc).isoformat()}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    response = JSONResponse(status_code=status_code, content=body)

    if retry_after and status_code in (429, 502, 503):
        response.headers["Retry-After"] = str(retry_after)

    return response


def setup_error_handlers(app: FastAPI) -> None:
    """Attach error handlers to the application.

    Called by main.py during app creation.
    """

    @app.exception_handler(ValueError)
    async def validation_error_handler(request: Request, exc: ValueError):
        """Handle validation errors with 400 + RFC 7807 response."""
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "type": "validation_error",
                "title": "Validation Failed",
                "status": 400,
                "detail": str(exc),
                "instance": str(request.url),
            },
        )

    @app.exception_handler(RuntimeError)
    async def runtime_error_handler(request: Request, exc: RuntimeError):
        """Handle LLM/provider errors with 502 + RFC 7807 response."""
        # Don't log the full exception message — it may contain sensitive data
        logger.error("LLM provider error: %s", exc, exc_info=True)

        body = {
            "type": "llm_error",
            "title": "LLM Provider Unavailable",
            "status": 502,
            "detail": "The AI provider is currently unavailable. Please try again.",
            "instance": str(request.url),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        response = JSONResponse(status_code=502, content=body)
        response.headers["Retry-After"] = "30"
        return response
