"""
Tests for validators (FR-002, FR-003, FR-017).

Covers:
- FR-002: Reject non-.txt files
- FR-003: Reject > 50 pages
- FR-017: Reject empty files
"""

from __future__ import annotations

import pytest

from meeting_analyzer.validators import (
    validate_transcript_file,
    validate_file_preupload,
)


# ── validate_transcript_file ──────────────────────────────────────


class TestValidateTranscriptFile:
    """Full-content validation tests."""

    def test_valid_txt_file(self):
        """Valid .txt file passes validation."""
        content = b"This is a valid transcript."
        result = validate_transcript_file("meeting.txt", content)
        assert result.valid is True
        assert result.errors == []

    def test_rejects_pdf_file(self):
        """FR-002: Non-.txt files are rejected."""
        content = b"%PDF-1.4 fake pdf content"
        result = validate_transcript_file("meeting.pdf", content)
        assert result.valid is False
        assert any(".txt" in err.lower() for err in result.errors)

    def test_rejects_docx_file(self):
        """FR-002: .docx files are rejected."""
        content = b"PK fake docx content"
        result = validate_transcript_file("meeting.docx", content)
        assert result.valid is False
        assert any(".txt" in err.lower() for err in result.errors)

    def test_rejects_empty_file(self):
        """FR-017: Empty files are rejected."""
        result = validate_transcript_file("empty.txt", b"")
        assert result.valid is False
        assert any("empty" in err.lower() for err in result.errors)

    def test_rejects_whitespace_only_file(self):
        """FR-017: Whitespace-only files are rejected."""
        result = validate_transcript_file("spaces.txt", b"   \n\n  \t  ")
        assert result.valid is False
        assert any("empty" in err.lower() for err in result.errors)

    def test_rejects_over_page_limit(self, tmp_path):
        """FR-003: Files exceeding MAX_TRANSCRIPT_PAGES are rejected."""
        # Generate text that exceeds 50 pages
        # ~100 lines/page × 50 pages = 5000 lines
        lines = ["This is line number " + str(i) for i in range(5100)]
        content = "\n".join(lines).encode("utf-8")

        result = validate_transcript_file("long.txt", content)
        assert result.valid is False
        assert any("page" in err.lower() for err in result.errors)

    def test_accepts_file_at_page_limit(self):
        """File exactly at 50 pages limit should pass."""
        # ~50 pages = ~5000 lines
        lines = ["Line " + str(i) for i in range(5000)]
        content = "\n".join(lines).encode("utf-8")

        result = validate_transcript_file("at_limit.txt", content, max_pages=50)
        assert result.valid is True

    def test_custom_max_pages(self):
        """Custom max_pages overrides settings."""
        content = b"Short file"
        result = validate_transcript_file("short.txt", content, max_pages=1)
        assert result.valid is True

    def test_case_insensitive_extension(self):
        """.TXT (uppercase) should also be accepted."""
        result = validate_transcript_file("meeting.TXT", b"content")
        assert result.valid is True
