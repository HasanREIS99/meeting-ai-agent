"""Application configuration via environment variables.

All configuration is externalized via pydantic-settings for NFR-R-003
(modular LLM replacement).

For testing, all values can be overridden via environment variables.
"""

from __future__ import annotations

import os
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed, validated configuration loaded from .env / environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ────────────────────────────────────────────────
    APP_NAME: str = "meeting-transcript-analyzer"
    APP_ENV: str = Field(default="test", alias="ENVIRONMENT")
    LOG_LEVEL: str = "WARNING"  # Quiet during tests

    # ── LLM Provider (ADR-002) ─────────────────────────────────────
    LLM_PROVIDER: str = Field(default="anthropic", alias="LLM_PROVIDER")
    LLM_MODEL: str = Field(
        default="claude-sonnet-4-20250514",
        alias="LLM_MODEL",
    )
    LLM_API_KEY: Optional[str] = Field(default=None, alias="LLM_API_KEY")
    LLM_API_BASE: Optional[str] = Field(default=None, alias="LLM_API_BASE")
    LLM_MAX_TOKENS: int = Field(
        default=8000,
        alias="LLM_MAX_TOKENS",
        description=(
            "Max completion tokens per LLM call. Reasoning models (Qwen 3.6 "
            "via the AI Hub) spend most of this budget on hidden thinking "
            "tokens, so a ceiling sized only for the visible answer truncates "
            "the response mid-JSON."
        ),
    )

    # ── Claude Code CLI fallback (LLM_PROVIDER=claude_cli) ─────────
    # Local-development escape hatch for when the configured HTTP
    # provider is unavailable: shells out to the already-authenticated
    # `claude -p` CLI instead of calling an API. The CLI authenticates
    # against the desktop keychain, which does not exist in a container
    # or in CI, so this provider is not a deployment path.
    CLAUDE_CLI_PATH: str = Field(
        default="claude",
        alias="CLAUDE_CLI_PATH",
        description="Path to the Claude Code CLI binary.",
    )
    CLAUDE_CLI_MODEL: str = Field(
        default="claude-haiku-4-5-20251001",
        alias="CLAUDE_CLI_MODEL",
        description="Model the CLI is asked to run the analysis with.",
    )
    CLAUDE_CLI_MAX_CONCURRENCY: int = Field(
        default=2,
        alias="CLAUDE_CLI_MAX_CONCURRENCY",
        description=(
            "Concurrent `claude -p` processes. Each invocation is a whole "
            "Node process, so this is bounded far lower than an HTTP "
            "provider would need."
        ),
    )

    # LiteLLM proxy (optional — enables cost tracking, routing)
    LITELLM_PROXY_URL: Optional[str] = Field(
        default=None, alias="LITELLM_PROXY_URL",
    )

    # ── Upload constraints ─────────────────────────────────────────
    MAX_TRANSCRIPT_PAGES: int = Field(
        default=50, alias="MAX_TRANSCRIPT_PAGES",
    )
    MAX_FILE_SIZE_BYTES: int = Field(
        default=5 * 1024 * 1024,  # ~5 MB = ~50 pages of plain text
        alias="MAX_FILE_SIZE_BYTES",
    )

    # ── Analysis settings (STORY-002-004, FR-011) ──────────────────
    CONFIDENCE_THRESHOLD: float = Field(
        default=0.5,
        alias="CONFIDENCE_THRESHOLD",
        description="Minimum confidence (0–1) for items to not be flagged uncertain.",
    )

    # ── Performance (NFR-P-001, NFR-P-002) ─────────────────────────
    TRANSCRIPT_TIMEOUT_SECONDS: int = Field(
        default=300, alias="TRANSCRIPT_TIMEOUT",
        description=(
            "Per-request LLM timeout. A 30-page transcript measured ~83s "
            "end-to-end, so the 50-page upload limit needs headroom above "
            "the original 120s."
        ),
    )


# Singleton — import `settings` everywhere instead of re-loading.
settings = Settings()
