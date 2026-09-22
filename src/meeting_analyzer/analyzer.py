"""
Transcript analyzer — orchestrates the analysis pipeline.

Takes a validated transcript text, runs the LLM analysis, and assembles
the structured :class:`TranscriptResult` + Markdown output (FR-007 through
FR-012).

This is the core business logic of the application.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional

from .config import settings
from .llm_service import LLMService, get_llm_service
from .markdown_builder import MarkdownBuilder
from .models import (
    ActionItem,
    Language,
    TopicCluster,
    TranscriptResult,
    UncertainFinding,
)
from .nlp_service import LanguageDetector
from .validators import validate_transcript_file

logger = logging.getLogger(__name__)


class TranscriptAnalyzer:
    """Orchestrates the full transcript analysis pipeline.

    Pipeline (data flow §6):
        1. Validate input file
        2. Detect language
        3. Run LLM analysis (clusters, action items, uncertainty)
        4. Assemble result + Markdown (FR-012)
    """

    def __init__(self, llm_service: Optional[LLMService] = None):
        self._llm = llm_service or get_llm_service()
        self._detector = LanguageDetector()

    async def analyze(
        self,
        filename: str,
        content: bytes,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TranscriptResult:
        """Run the full analysis pipeline on a transcript file.

        Args:
            filename: Original upload filename.
            content: Raw file bytes.
            metadata: Optional transcript metadata.

        Returns:
            A :class:`TranscriptResult` ready to serialize to JSON.

        Raises:
            ValueError: If file validation fails.
            RuntimeError: If the LLM provider fails.
        """
        pipeline_start = time.monotonic()

        # Step 1: Validate (FR-002, FR-003, FR-017)
        validation = validate_transcript_file(filename, content)
        if not validation:
            raise ValueError(
                f"Validation failed: {'; '.join(validation.errors)}"
            )

        # Decode to string for language detection and LLM processing
        text = content.decode("utf-8", errors="ignore")
        if not text.strip():
            raise ValueError("Transcript file is empty")

        # Step 2: Language detection (FR-004)
        language = self._detector.detect(text)
        logger.info("Detected language: %s", language)

        # Step 3: LLM analysis (FR-007 through FR-011)
        llm_result = await self._llm.analyze_transcript(text, language)

        # Step 4: Assemble result
        processing_time = round(time.monotonic() - pipeline_start, 3)

        # Convert LLM dicts to Pydantic models
        topic_clusters = [
            TopicCluster(**tc) for tc in llm_result.get("topic_clusters", [])
        ]
        action_items = [
            ActionItem(**ai) for ai in llm_result.get("action_items", [])
        ]
        uncertain_findings = [
            UncertainFinding(**uf)
            for uf in llm_result.get("uncertain_findings", [])
        ]

        # Step 5: Markdown assembly (FR-012)
        meeting_title = metadata.get("title") if metadata else None
        if not meeting_title:
            meeting_title = self._suggest_title(text)

        markdown_content = MarkdownBuilder.assemble(
            meeting_title=meeting_title,
            language=language,
            topic_clusters=topic_clusters,
            action_items=action_items,
            uncertain_findings=uncertain_findings,
        )

        return TranscriptResult(
            meeting_title=meeting_title,
            language=Language(language),
            topic_clusters=topic_clusters,
            action_items=action_items,
            uncertain_findings=uncertain_findings,
            processing_time=processing_time,
            markdown_content=markdown_content,
            generated_at=datetime.utcnow(),
        )

    @staticmethod
    def _suggest_title(text: str) -> str:
        """Derive a meeting title from the first line or a short excerpt."""
        first_line = text.strip().split("\n", 1)[0].strip()
        if first_line and len(first_line) <= 80:
            return first_line
        # Fallback: first 60 characters
        excerpt = text.strip()[:60].strip()
        return "Meeting transcript ({})".format(excerpt + "...") if excerpt else "Untitled meeting"
