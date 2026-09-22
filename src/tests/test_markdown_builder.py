"""
Tests for the Markdown output builder (FR-012).

Covers:
- FR-012: Structured Markdown output with heading hierarchy,
  topic clusters, summaries, action items, and uncertainty indicators.
- NFR-U-003: Output structured with clear headings and visual hierarchy.
"""

from __future__ import annotations

from meeting_analyzer.models import (
    ActionItem,
    TopicCluster,
    UncertainFinding,
)
from meeting_analyzer.markdown_builder import MarkdownBuilder


class TestMarkdownBuilder:
    """Markdown assembly tests."""

    def test_basic_assembly(self):
        """Basic assembly with all sections."""
        md = MarkdownBuilder.assemble(
            meeting_title="Sprint Planning",
            language="en",
            topic_clusters=[
                TopicCluster(
                    title="Sprint Backlog",
                    summary="Reviewed current sprint tasks and blockers.",
                    confidence=0.9,
                    keywords=["sprint", "backlog"],
                ),
            ],
            action_items=[
                ActionItem(
                    description="Update sprint board",
                    assignee="John",
                    deadline="2025-09-20",
                    confidence=0.85,
                ),
            ],
            uncertain_findings=[],
        )

        assert "# Sprint Planning" in md
        assert "Language: en" in md
        assert "## Topic Clusters" in md
        assert "### 1. Sprint Backlog" in md
        assert "## Action Items" in md
        assert "**Update sprint board**" in md
        assert "Assignee: `John`" in md
        assert "Deadline: `2025-09-20`" in md

    def test_uncertainty_flagging(self):
        """FR-011: Uncertain items are marked with ⚠."""
        md = MarkdownBuilder.assemble(
            meeting_title="Review",
            language="en",
            topic_clusters=[
                TopicCluster(
                    title="Budget",
                    summary="Budget discussion was unclear.",
                    confidence=0.4,
                    uncertain=True,
                ),
            ],
            action_items=[
                ActionItem(
                    description="Follow up on budget",
                    assignee=None,
                    deadline=None,
                    confidence=0.3,
                    uncertain=True,
                ),
            ],
            uncertain_findings=[
                UncertainFinding(
                    type="topic",
                    description="Budget allocation unclear from transcript.",
                ),
            ],
        )

        assert "⚠️ *This topic is flagged as uncertain.*" in md
        assert "⚠️ *Uncertain" in md
        assert "## ⚠️ Uncertain Findings" in md
        assert "Budget allocation unclear" in md

    def test_turkish_output(self):
        """FR-005: Turkish transcripts produce Turkish output."""
        md = MarkdownBuilder.assemble(
            meeting_title="Sprint Planlama",
            language="tr",
            topic_clusters=[],
            action_items=[],
            uncertain_findings=[],
        )

        assert "# Sprint Planlama" in md
        assert "Language: tr" in md

    def test_no_action_items(self):
        """Empty action items section."""
        md = MarkdownBuilder.assemble(
            meeting_title="Status",
            language="en",
            topic_clusters=[],
            action_items=[],
            uncertain_findings=[],
        )

        assert "No action items identified" in md

    def test_no_topic_clusters(self):
        """Empty topic clusters section."""
        md = MarkdownBuilder.assemble(
            meeting_title="Status",
            language="en",
            topic_clusters=[],
            action_items=[],
            uncertain_findings=[],
        )

        assert "No topic clusters identified" in md

    def test_unspecified_fields(self):
        """FR-010: Missing assignee/deadline show 'unspecified'."""
        md = MarkdownBuilder.assemble(
            meeting_title="Meeting",
            language="en",
            topic_clusters=[],
            action_items=[
                ActionItem(
                    description="Do something",
                    assignee=None,
                    deadline=None,
                    confidence=0.8,
                ),
            ],
            uncertain_findings=[],
        )

        assert "Assignee: `unspecified`" in md
        assert "Deadline: `unspecified`" in md
