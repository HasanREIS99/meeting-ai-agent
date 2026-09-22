"""
Transcript analysis router (EP-001).

Handles file upload and triggers the full analysis pipeline.
Returns structured JSON result (TranscriptResult).

No authentication required -- anyone can upload and analyze transcripts.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse

from ..analyzer import TranscriptAnalyzer

logger = logging.getLogger(__name__)

router = APIRouter()


def get_analyzer() -> TranscriptAnalyzer:
    """Dependency that provides a TranscriptAnalyzer instance."""
    return TranscriptAnalyzer()


@router.post("")
async def analyze_transcript(
    file: UploadFile = File(...),
    title: Optional[str] = Form(default=None),
    meeting_date: Optional[str] = Form(default=None),
    participants: Optional[str] = Form(default=None),
    analyzer_instance: TranscriptAnalyzer = Depends(get_analyzer),
) -> JSONResponse:
    """Upload a transcript and receive analysis (EP-001).

    Accepts a .txt transcript file via multipart form data, validates it,
    runs the full analysis pipeline (FR-007 through FR-012), and returns
    a structured JSON result.

    No authentication is required.

    Args:
        file: The .txt transcript file.
        title: Optional meeting title.
        meeting_date: Optional meeting date (YYYY-MM-DD).
        participants: Optional comma-separated participant names.

    Returns:
        JSON TranscriptResult with topic clusters, action items, and Markdown.
    """
    filename = file.filename or "unknown.txt"
    content = await file.read()

    # Build metadata from optional form fields
    metadata: Dict[str, Any] = {}
    if title:
        metadata["title"] = title
    if meeting_date:
        metadata["meeting_date"] = meeting_date
    if participants:
        metadata["participants"] = [p.strip() for p in participants.split(",") if p.strip()]

    try:
        result = await analyzer_instance.analyze(filename, content, metadata)
        return JSONResponse(
            status_code=200,
            content=result.model_dump(mode="json"),
        )

    except ValueError as exc:
        # Validation errors (FR-002, FR-003, FR-017)
        return JSONResponse(
            status_code=400,
            content={
                "type": "validation_error",
                "title": "Validation Failed",
                "status": 400,
                "detail": str(exc),
            },
        )

    except RuntimeError as exc:
        # LLM provider failures (FR-015)
        response = JSONResponse(
            status_code=502,
            content={
                "type": "llm_error",
                "title": "LLM Provider Unavailable",
                "status": 502,
                "detail": str(exc),
            },
        )
        response.headers["Retry-After"] = "30"
        return response

    except Exception as exc:
        # Unexpected errors
        logger.error("Analysis failed for '%s': %s", filename, exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "type": "internal_error",
                "title": "Internal Server Error",
                "status": 500,
                "detail": "An unexpected error occurred during analysis.",
            },
        )
