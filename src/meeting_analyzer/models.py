"""
Pydantic data models for the Meeting Transcript Analyzer API.

Aligned with the OpenAPI schemas in docs/analysis/meeting-transcript-analyzer/
services/openapi.yaml (generated from services.md §3).

All models are intentionally minimal — they mirror the external contract
(EP-001 through EP-006) and are used by the FastAPI routers for validation.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────────


class Language(str, Enum):
    """Detected primary language of the transcript."""

    EN = "en"
    TR = "tr"
    MIXED = "mixed"


class FindingType(str, Enum):
    """Category of an uncertain finding."""

    TOPIC = "topic"
    SUMMARY = "summary"
    ACTION_ITEM = "action_item"


# ── TranscriptResult (EP-001 response) ────────────────────────────


class TopicCluster(BaseModel):
    """A topic cluster identified from the transcript content."""

    title: str = Field(description="Topic cluster title")
    summary: str = Field(description="1-2 sentence summary")
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence score (0–1)",
    )
    uncertain: bool = Field(default=False, description="Flagged as uncertain")
    keywords: List[str] = Field(
        default_factory=list,
        description="Keywords or tags associated with this topic",
    )


class ActionItem(BaseModel):
    """An action item extracted from the transcript."""

    description: str = Field(description="The action item description")
    assignee: Optional[str] = Field(
        default=None,
        description='Person responsible; "unspecified" if not stated',
    )
    deadline: Optional[str] = Field(
        default=None,
        description='Deadline for the action; "unspecified" if not stated',
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence score (0–1)",
    )
    uncertain: bool = Field(default=False, description="Flagged as uncertain")


class UncertainFinding(BaseModel):
    """An item flagged as uncertain by the LLM."""

    type: FindingType = Field(description="Type of uncertain finding")
    description: str = Field(description="Description of what is uncertain")

    model_config = {
        "populate_by_name": True,  # serialize as snake_case but also accept camelCase
    }


class TranscriptResult(BaseModel):
    """Full analysis result returned to the user (EP-001)."""

    meeting_title: str = Field(description="Auto-generated or user-provided title")
    language: Language = Field(description="Detected primary language")
    topic_clusters: List[TopicCluster] = Field(
        description="List of identified topic clusters",
    )
    action_items: List[ActionItem] = Field(
        description="List of extracted action items",
    )
    uncertain_findings: List[UncertainFinding] = Field(
        default_factory=list,
        description="Items flagged as uncertain (FR-011)",
    )
    processing_time: float = Field(description="Time taken to process in seconds")
    markdown_content: str = Field(description="Full Markdown-formatted output")
    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this analysis was generated",
    )


# ── Upload request (EP-001 request) ───────────────────────────────


class TranscriptMetadata(BaseModel):
    """Optional metadata attached to an upload."""

    title: Optional[str] = Field(default=None, description="Human-readable meeting title")
    meeting_date: Optional[str] = Field(
        default=None,
        description="Date of the meeting (YYYY-MM-DD)",
    )
    participants: List[str] = Field(
        default_factory=list,
        description="List of participant names",
    )


# ── Validation response (EP-003) ──────────────────────────────────


class ValidationResponse(BaseModel):
    """Pre-upload file validation result (FR-002, FR-003, FR-017)."""

    valid: bool = Field(description="Whether the file passes validation")
    errors: List[str] = Field(
        default_factory=list,
        description="List of validation errors (empty if valid)",
    )


# ── Error response (RFC 7807 Problem Details) ─────────────────────


class ErrorResponse(BaseModel):
    """Standardized error response following RFC 7807."""

    type: str = Field(
        default="about:blank",
        description="Error type URI",
    )
    title: str = Field(description="Short error title")
    status: int = Field(description="HTTP status code")
    detail: Optional[str] = Field(
        default=None,
        description="Human-readable error message",
    )
    instance: Optional[str] = Field(
        default=None,
        description="Error instance identifier",
    )


# ── (End of models) ────────────────────────────────────────────────
