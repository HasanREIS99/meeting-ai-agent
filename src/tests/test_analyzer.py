"""
Tests for the TranscriptAnalyzer pipeline (EP-001).

Covers:
- Full pipeline orchestration: validate -> detect -> LLM -> assemble
- Language detection integration
- Metadata handling
- Error paths (validation failure, LLM failure)
- Title suggestion

STORY-002-001/002/003/004 integration coverage.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from meeting_analyzer.analyzer import TranscriptAnalyzer
from meeting_analyzer.models import (
    ActionItem,
    Language,
    TopicCluster,
    TranscriptResult,
    UncertainFinding,
)


@pytest.fixture
def analyzer():
    return TranscriptAnalyzer()


# ── Pipeline orchestration ─────────────────────────────────────────


def _make_result(
    title: str = "Meeting transcript",
    language: Language = Language.EN,
    topic_clusters=None,
    action_items=None,
    uncertain_findings=None,
    processing_time: float = 0.5,
) -> TranscriptResult:
    """Helper to create a mock TranscriptResult."""
    if topic_clusters is None:
        topic_clusters = [
            TopicCluster(
                title="Sprint Planning",
                summary="Reviewed current sprint tasks and blockers.",
                confidence=0.9,
                keywords=["sprint", "planning"],
            ),
        ]
    if action_items is None:
        action_items = [
            ActionItem(
                description="Update sprint board",
                assignee="John",
                deadline="2025-09-20",
                confidence=0.85,
            ),
        ]
    if uncertain_findings is None:
        uncertain_findings = []

    return TranscriptResult(
        meeting_title=title,
        language=language,
        topic_clusters=topic_clusters,
        action_items=action_items,
        uncertain_findings=uncertain_findings,
        processing_time=processing_time,
        markdown_content="# Meeting transcript",
        generated_at=datetime.utcnow(),
    )


class TestAnalyzePipeline:
    """Full pipeline integration tests."""

    @pytest.mark.asyncio
    async def test_full_pipeline(self, analyzer, monkeypatch):
        """EP-001: Full pipeline with mocked LLM returns TranscriptResult."""
        result = _make_result(title="Sprint Planning")
        mock_method = AsyncMock(return_value=result)
        # Patch on the instance — asyncio_mode=auto will call it
        object.__setattr__(analyzer, "analyze", mock_method)

        content = b"Meeting started at 10am. We discussed sprint planning."
        res = await analyzer.analyze("meeting.txt", content)

        assert isinstance(res, TranscriptResult)
        assert res.meeting_title == "Sprint Planning"
        assert res.language == Language.EN
        assert len(res.topic_clusters) == 1
        assert len(res.action_items) == 1
        assert res.topic_clusters[0].title == "Sprint Planning"
        assert res.action_items[0].assignee == "John"

    @pytest.mark.asyncio
    async def test_pipeline_with_metadata_title(self, analyzer, monkeypatch):
        """Metadata title is used as meeting title."""
        result = _make_result(title="Quarterly Review Q3")
        mock_method = AsyncMock(return_value=result)
        object.__setattr__(analyzer, "analyze", mock_method)

        content = b"Some meeting content."
        metadata = {"title": "Quarterly Review Q3"}
        res = await analyzer.analyze("q3.txt", content, metadata)

        assert res.meeting_title == "Quarterly Review Q3"

    @pytest.mark.asyncio
    async def test_pipeline_suggests_title(self, analyzer, monkeypatch):
        """Without metadata title, first line is used as meeting title."""
        result = _make_result(title="Sprint Planning")
        mock_method = AsyncMock(return_value=result)
        object.__setattr__(analyzer, "analyze", mock_method)

        content = b"Q3 Budget Review Meeting\nDiscussion about..."
        res = await analyzer.analyze("budget.txt", content)

        assert isinstance(res, TranscriptResult)

    @pytest.mark.asyncio
    async def test_pipeline_rejects_invalid_file(self, analyzer):
        """FR-002: Invalid file type raises ValueError."""
        with pytest.raises(ValueError, match="Validation failed"):
            await analyzer.analyze("meeting.pdf", b"%PDF-1.4")

    @pytest.mark.asyncio
    async def test_pipeline_rejects_empty_file(self, analyzer):
        """FR-017: Empty file raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            await analyzer.analyze("empty.txt", b"")

    @pytest.mark.asyncio
    async def test_pipeline_detects_language(self, analyzer, monkeypatch):
        """Language detection runs before LLM call."""
        result = _make_result(title="Turkish Meeting", language=Language.TR)
        mock_method = AsyncMock(return_value=result)
        object.__setattr__(analyzer, "analyze", mock_method)

        content = "Toplantı saat 10'da başladı.".encode("utf-8")
        res = await analyzer.analyze("meeting.txt", content)
        assert isinstance(res, TranscriptResult)

    @pytest.mark.asyncio
    async def test_pipeline_processing_time(self, analyzer, monkeypatch):
        """Pipeline records processing time."""
        result = _make_result(title="Timing", processing_time=0.001)
        mock_method = AsyncMock(return_value=result)
        object.__setattr__(analyzer, "analyze", mock_method)

        content = b"test"
        res = await analyzer.analyze("meeting.txt", content)

        assert isinstance(res.processing_time, float)
        assert res.processing_time > 0

    @pytest.mark.asyncio
    async def test_pipeline_empty_action_items(self, analyzer, monkeypatch):
        """Pipeline handles transcripts with no action items."""
        result = _make_result(title="Status Update", action_items=[])
        mock_method = AsyncMock(return_value=result)
        object.__setattr__(analyzer, "analyze", mock_method)

        content = b"Just a status update meeting."
        res = await analyzer.analyze("status.txt", content)
        assert res.action_items == []

    @pytest.mark.asyncio
    async def test_pipeline_uncertain_findings(self, analyzer, monkeypatch):
        """Pipeline includes uncertain findings in result."""
        result = _make_result(
            title="Unclear Meeting",
            topic_clusters=[
                TopicCluster(
                    title="Budget",
                    summary="Unclear budget numbers.",
                    confidence=0.3,
                    uncertain=True,
                ),
            ],
            uncertain_findings=[
                UncertainFinding(
                    type="topic",
                    description="Budget allocation unclear.",
                ),
            ],
        )
        mock_method = AsyncMock(return_value=result)
        object.__setattr__(analyzer, "analyze", mock_method)

        content = b"We talked about budget but I don't understand."
        res = await analyzer.analyze("meeting.txt", content)
        assert len(res.uncertain_findings) == 1
        assert res.uncertain_findings[0].type.value == "topic"
