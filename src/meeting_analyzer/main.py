"""
FastAPI application -- Meeting Transcript Analyzer.

Entry point for the service. Registers routers, middleware, and
event handlers (startup/shutdown).
"""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .error_handling import PerformanceMonitor, TimeoutMiddleware, setup_error_handlers
from .routers import analyze, health, validate

# ── Logging setup (NFR-R-002: no sensitive data in logs) ───────────


class SensitiveFilter(logging.Filter):
    """Filter out lines that might contain sensitive transcript data."""

    # Keywords that suggest transcript content in log lines
    _SENSITIVE_PATTERNS = [
        "transcript", "meeting minutes", "action item",
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        msg = str(record.msg)
        for pattern in self._SENSITIVE_PATTERNS:
            if pattern in msg.lower():
                # Redact the sensitive portion
                record.msg = msg.replace(pattern, "[REDACTED]")
        return True


def setup_logging() -> None:
    """Configure application logging.

    Logs only metadata (file size, processing time) -- never
    transcript content (NFR-R-002, NFR-S-001).
    """
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "[%(asctime)s] %(name)s %(levelname)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    handler.addFilter(SensitiveFilter())

    root = logging.getLogger()
    root.setLevel(log_level)
    root.addHandler(handler)

    # Reduce noise from upstream libraries
    for noisy in ("uvicorn.access", "uvicorn.error", "httpx", "litellm"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


# ── Lifespan ───────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: startup and shutdown hooks."""
    logging.info("Starting %s v%s", settings.APP_NAME, "1.0.0")
    yield
    logging.info("Shutting down %s", settings.APP_NAME)


# ── App factory ────────────────────────────────────────────────────


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    The app is fully open -- no authentication is required.
    Any user can upload and analyze transcripts directly at ``/``.
    """
    setup_logging()

    app = FastAPI(
        title=settings.APP_NAME,
        description=(
            "AI-powered meeting transcript analyzer. "
            "Upload a .txt transcript and receive structured analysis "
            "with topic clusters, summaries, and action items."
        ),
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )

    # CORS -- restrict to internal network origins in production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # TODO: restrict to internal domain
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Timeout middleware -- enforce per-request timeout (NFR-P-001, NFR-P-002)
    app.add_middleware(TimeoutMiddleware, timeout_seconds=settings.TRANSCRIPT_TIMEOUT_SECONDS)

    # Error handlers -- RFC 7807 Problem Details format (FR-015)
    setup_error_handlers(app)

    # Register routers
    app.include_router(health.router, prefix="/api/v1", tags=["Health"])
    app.include_router(
        validate.router, prefix="/api/v1/validate", tags=["Validation"]
    )
    app.include_router(
        analyze.router, prefix="/api/v1/analyze", tags=["Analysis"]
    )

    # Serve frontend static files and pages
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse
    from pathlib import Path

    frontend_dir = Path(__file__).parent / "frontend" / "static"
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(str(frontend_dir.parent / "index.html"))

    # Global error handler (FR-015, RFC 7807 Problem Details)
    @app.exception_handler(Exception)
    async def global_error_handler(request, exc: Exception):
        logging.error("Unhandled exception: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "type": "about:blank",
                "title": "Internal Server Error",
                "status": 500,
                "detail": "An unexpected error occurred.",
            },
        )

    return app


# Entry point for uvicorn
app = create_app()
