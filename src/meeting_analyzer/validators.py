"""
File validation logic for transcript uploads.

Implements FR-002 (reject non-.txt), FR-003 (reject > 50 pages),
and FR-017 (reject empty files). Used by EP-001 (upload) and EP-003
(pre-upload validation).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

from .config import settings

logger = logging.getLogger(__name__)

# Estimated: ~100 lines per page (standard letter size, 12pt font).
# A 50-page transcript ≈ 5,000 lines.
_LINES_PER_PAGE: int = 100


@dataclass(frozen=True)
class ValidationResult:
    """Immutable validation result returned by validate_transcript_file."""

    valid: bool
    errors: List[str]

    def __bool__(self) -> bool:
        return self.valid


def _estimate_pages(content: str) -> int:
    """Rough page count based on line count."""
    line_count = content.count("\n") + 1
    return max(1, line_count // _LINES_PER_PAGE)


def validate_transcript_file(
    filename: str,
    content: bytes,
    max_pages: Optional[int] = None,
) -> ValidationResult:
    """Validate a transcript file before processing.

    Checks:
    1. File extension must be ``.txt`` (FR-002).
    2. File must not be empty (FR-017).
    3. File must not exceed ``max_pages`` pages (FR-003).

    Args:
        filename: Original upload filename.
        content: Raw file bytes.
        max_pages: Override for ``settings.MAX_TRANSCRIPT_PAGES``.

    Returns:
        A :class:`ValidationResult` that is truthy when all checks pass.
    """
    if max_pages is None:
        max_pages = settings.MAX_TRANSCRIPT_PAGES

    errors: List[str] = []

    # 1. Extension check (FR-002)
    if not filename.lower().endswith(".txt"):
        errors.append("File must be a .txt (plain text) file")
        return ValidationResult(valid=False, errors=errors)

    # 2. Empty check (FR-017)
    stripped = content.decode("utf-8", errors="ignore").strip()
    if not stripped:
        errors.append("Transcript file is empty")
        return ValidationResult(valid=False, errors=errors)

    # 3. Page limit check (FR-003)
    pages = _estimate_pages(stripped)
    if pages > max_pages:
        errors.append(
            f"Transcript exceeds {max_pages} pages "
            f"(estimated {pages} pages). Maximum allowed: {max_pages}.",
        )
        return ValidationResult(valid=False, errors=errors)

    logger.info(
        "File '%s' validated: %d pages, %d bytes",
        filename,
        pages,
        len(content),
    )
    return ValidationResult(valid=True, errors=[])


def validate_file_preupload(
    filename: str,
    size_bytes: int,
) -> ValidationResult:
    """Lightweight pre-upload validation using only the filename and size.

    This is used by EP-003 where the full file content is not yet available.
    It catches gross violations (wrong extension, empty file) without reading
    the entire content.

    Args:
        filename: Upload filename.
        size_bytes: File size in bytes.

    Returns:
        A :class:`ValidationResult`.
    """
    errors: List[str] = []

    if not filename.lower().endswith(".txt"):
        errors.append("File must be a .txt (plain text) file")
        return ValidationResult(valid=False, errors=errors)

    if size_bytes == 0:
        errors.append("Transcript file is empty")
        return ValidationResult(valid=False, errors=errors)

    # Rough byte-level page estimate (plain text ≈ 50 bytes/line,
    # 100 lines/page → ~5000 bytes/page)
    estimated_pages = max(1, size_bytes // (50 * _LINES_PER_PAGE))
    if estimated_pages > settings.MAX_TRANSCRIPT_PAGES:
        errors.append(
            f"File size suggests {estimated_pages} pages "
            f"(max {settings.MAX_TRANSCRIPT_PAGES}). "
            f"Upload and validate for an accurate check.",
        )
        return ValidationResult(valid=False, errors=errors)

    return ValidationResult(valid=True, errors=[])
