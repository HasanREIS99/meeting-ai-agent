"""
File validation router (EP-003).

Provides pre-upload file validation (FR-002, FR-003, FR-017) without
processing the transcript content.

No authentication required -- anyone can validate and upload transcripts.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse

from . import validate
from ..validators import validate_file_preupload

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("")
async def validate_file(
    file: UploadFile = File(...),
) -> JSONResponse:
    """Pre-upload file validation (EP-003).

    Checks file type, size, and content emptiness BEFORE the full upload.
    This prevents users from uploading large invalid files that will be
    rejected anyway.

    No authentication is required.

    FR-002: Reject non-.txt files.
    FR-003: Reject > 50 page files.
    FR-017: Reject empty files.
    """
    filename = file.filename or ""
    content = await file.read()
    size_bytes = len(content)

    result = validate_file_preupload(filename, size_bytes)

    # Always return 200 — the caller checks the `valid` field and
    # `errors` list. Returning 400 here would prevent the frontend
    # from reading the JSON body (browsers block parsing on 4xx).
    return JSONResponse(
        status_code=200,
        content={
            "valid": result.valid,
            "errors": result.errors,
            "filename": filename,
            "size_bytes": size_bytes,
            "message": "File passed validation. Ready to upload." if result.valid else "File failed validation.",
        },
    )
