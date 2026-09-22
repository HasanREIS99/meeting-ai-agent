"""
LLM service abstraction layer.

Implements ADR-002 (Claude via LiteLLM) and NFR-R-003 (modular LLM
replacement — swap providers without changing application code).

The public interface is the ``LLMService`` abstract base class.
A concrete ``LiteLLMService`` is provided for the default Anthropic
provider, and a ``ClaudeCLIService`` shells out to a locally
authenticated Claude Code CLI as a development fallback. Additional
providers (OpenAI, local Llama, etc.) implement the same interface.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .config import settings

logger = logging.getLogger(__name__)


class TruncatedResponseError(RuntimeError):
    """Raised when the LLM stopped because it hit the token ceiling.

    The payload that comes back is cut off mid-document, so it can never
    be parsed or repaired — the only fix is a larger ``LLM_MAX_TOKENS``.
    """


# ── Structured output models (LLM response validation) ──────────────


class LLMTopicCluster(BaseModel):
    """Schema for a single LLM topic cluster result."""

    title: str = Field(description="Topic cluster title")
    summary: str = Field(description="1-2 sentence summary")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0-1")
    uncertain: bool = Field(default=False)
    keywords: List[str] = Field(default_factory=list)


class LLMActionItem(BaseModel):
    """Schema for a single LLM action item result."""

    description: str = Field(description="The action item description")
    assignee: Optional[str] = Field(default=None)
    deadline: Optional[str] = Field(default=None)
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0-1")
    uncertain: bool = Field(default=False)


class LLMUncertainFinding(BaseModel):
    """Schema for a single LLM uncertain finding."""

    type: str = Field(description="Finding type: topic|summary|action_item")
    description: str = Field(description="What is uncertain and why")


class LLMAnalysisResult(BaseModel):
    """Validated structured output from the LLM analysis prompt."""

    topic_clusters: List[LLMTopicCluster] = Field(default_factory=list)
    action_items: List[LLMActionItem] = Field(default_factory=list)
    uncertain_findings: List[LLMUncertainFinding] = Field(default_factory=list)


class LLMService(ABC):
    """Abstract interface for LLM providers (NFR-R-003)."""

    @abstractmethod
    async def analyze_transcript(
        self,
        text: str,
        language: str,
    ) -> Dict[str, Any]:
        """Run full transcript analysis pipeline.

        Args:
            text: The transcript text to analyze.
            language: Detected primary language ('en', 'tr', 'mixed').

        Returns:
            A dict with keys:
                - topic_clusters: list[dict]
                - action_items: list[dict]
                - uncertain_findings: list[dict]
                - markdown_content: str
                - processing_time: float
        """

    @abstractmethod
    async def estimate_tokens(self, text: str) -> int:
        """Return an estimate of the token count for *text*."""

    @abstractmethod
    async def analyze_with_prompt(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> Dict[str, Any]:
        """Run a single LLM call with structured output validation.

        Args:
            system_prompt: The system message.
            user_prompt: The user message containing the task.

        Returns:
            Parsed and validated result dict.
        """


class PromptAnalysisService(LLMService):
    """Everything in the pipeline that does not depend on the provider.

    Prompt construction, confidence thresholding, normalisation and
    schema validation are identical whichever backend answers, so a
    provider only has to implement :meth:`analyze_with_prompt`
    (NFR-R-003 -- modular LLM replacement).
    """

    # ── LLMService abstract interface ───────────────────────────────

    async def analyze_transcript(
        self,
        text: str,
        language: str,
    ) -> Dict[str, Any]:
        """Execute the full analysis pipeline.

        Pipeline steps (NFR-R-003 — each step independent for retry/
        extension):
            1. Topic cluster identification (FR-007)
            2. Topic summarization (FR-008)
            3. Action item extraction (FR-009, FR-010)
            4. Uncertainty flagging (FR-011)
            5. Confidence thresholding (FR-011)

        Args:
            text: Transcript text.
            language: Detected primary language.

        Returns:
            Analysis result dict.

        Raises:
            RuntimeError: If the LLM provider is unavailable after retries.
        """
        start = time.monotonic()

        try:
            result = await self._run_analysis_prompt(text, language)
        except TruncatedResponseError as exc:
            # Keep the specific message: this one is actionable by an
            # operator, unlike a generic provider outage.
            logger.error("LLM analysis truncated: %s", exc)
            raise RuntimeError(str(exc)) from exc
        except Exception as exc:
            logger.error("LLM analysis failed: %s", exc, exc_info=True)
            raise RuntimeError(
                "LLM provider unavailable. Please try again later.",
            ) from exc

        result["processing_time"] = round(time.monotonic() - start, 3)

        logger.info(
            "Analysis complete: %d topics, %d action items, %.2fs",
            len(result.get("topic_clusters", [])),
            len(result.get("action_items", [])),
            result["processing_time"],
        )
        return result

    async def estimate_tokens(self, text: str) -> int:
        """Estimate token count using tiktoken (GPT encoding) as approximation."""
        try:
            import tiktoken

            enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        except ImportError:
            # Fallback: rough estimate (1 token ≈ 4 bytes for English)
            return max(1, len(text.encode("utf-8")) // 4)

    # ── Internal helpers ────────────────────────────────────────────

    async def _run_analysis_prompt(self, text: str, language: str) -> Dict[str, Any]:
        """Send the transcript to the LLM and parse the structured response."""
        system_prompt = _build_system_prompt(language)
        user_prompt = _build_user_prompt(text)

        result = await self.analyze_with_prompt(system_prompt, user_prompt)

        # Apply confidence thresholding (STORY-002-004, FR-011)
        threshold = settings.CONFIDENCE_THRESHOLD
        self._apply_uncertainty_thresholds(result, threshold)

        # Normalize uncertain finding types — Qwen may return values
        # not in FindingType (e.g. "Configuration"). Map them to "topic"
        # so Pydantic validation doesn't crash.
        _normalize_uncertain_findings(result)

        # Validate structured output with Pydantic (STORY-002-001)
        try:
            validated = LLMAnalysisResult.model_validate(result)
        except Exception as exc:
            logger.warning(
                "LLM structured output validation failed, falling back to raw: %s",
                exc,
            )
            # Return raw result — don't crash the pipeline
            return {
                "topic_clusters": result.get("topic_clusters", []),
                "action_items": result.get("action_items", []),
                "uncertain_findings": result.get("uncertain_findings", []),
            }

        return validated.model_dump(mode="json")

    @staticmethod
    def _apply_uncertainty_thresholds(
        result: Dict[str, Any],
        threshold: float,
    ) -> Dict[str, Any]:
        """Flag items below confidence threshold as uncertain (FR-011).

        Items with confidence below ``threshold`` are auto-flagged:
            - topic_clusters[].uncertain = True
            - action_items[].uncertain = True
            - new uncertain_findings appended for each flagged item

        Args:
            result: Raw LLM result dict.
            threshold: Confidence floor (0–1).

        Returns:
            The result dict with uncertainty flags applied in place.
        """
        uncertain_findings = list(result.get("uncertain_findings", []))

        for cluster in result.get("topic_clusters", []):
            if cluster.get("confidence", 1.0) < threshold and not cluster.get(
                "uncertain", False
            ):
                cluster["uncertain"] = True
                uncertain_findings.append(
                    {
                        "type": "topic",
                        "description": (
                            f'Topic "{cluster.get("title", "Unknown")}" '
                            f"has low confidence ({cluster['confidence']:.2f})"
                        ),
                    }
                )

        for item in result.get("action_items", []):
            if item.get("confidence", 1.0) < threshold and not item.get(
                "uncertain", False
            ):
                item["uncertain"] = True
                uncertain_findings.append(
                    {
                        "type": "action_item",
                        "description": (
                            f'Action "{item.get("description", "Unknown")}" '
                            f"has low confidence ({item['confidence']:.2f})"
                        ),
                    }
                )

        result["uncertain_findings"] = uncertain_findings
        return result


# ── LiteLLM concrete implementation ────────────────────────────────


class LiteLLMService(PromptAnalysisService):
    """LLM service backed by LiteLLM (supports Anthropic, OpenAI, etc.).

    Implements ADR-002 (provider-agnostic via LiteLLM) and NFR-R-001
    (graceful failure with exponential backoff retry).
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: int = 3,
    ):
        """Initialise the LiteLLM service.

        Args:
            provider: LLM provider name. Defaults to ``settings.LLM_PROVIDER``.
            model: Model identifier. Defaults to ``settings.LLM_MODEL``.
            max_retries: Max retry attempts on transient failures.
        """
        self.provider = provider or settings.LLM_PROVIDER
        self.model = model or settings.LLM_MODEL
        self._api_key = settings.LLM_API_KEY
        self._api_base = settings.LLM_API_BASE
        self._timeout = settings.TRANSCRIPT_TIMEOUT_SECONDS
        self._max_tokens = settings.LLM_MAX_TOKENS
        self._max_retries = max_retries
        self._cost_tracker: List[Dict[str, Any]] = []

    async def analyze_with_prompt(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> Dict[str, Any]:
        """Run a single LLM call with structured output validation.

        Args:
            system_prompt: The system message.
            user_prompt: The user message containing the task.

        Returns:
            Parsed and validated result dict.
        """
        last_error: Optional[Exception] = None

        for attempt in range(1, self._max_retries + 1):
            try:
                response = await self._completion(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )

                content_raw = response["choices"][0]["message"]["content"]
                finish_reason = response["choices"][0].get("finish_reason")
                usage = response.get("usage", {})

                logger.debug(
                    "LLM attempt %d: finish_reason=%s content_len=%s "
                    "input_tokens=%s output_tokens=%s",
                    attempt,
                    finish_reason,
                    len(content_raw) if isinstance(content_raw, str) else "N/A",
                    usage.get("prompt_tokens", "?"),
                    usage.get("completion_tokens", "?"),
                )

                # Checked before the None check: a reasoning model that spends
                # its whole budget thinking returns *both* finish_reason
                # "length" and empty content, and the ceiling is the useful
                # half of that story.
                if finish_reason == "length":
                    raise TruncatedResponseError(
                        "LLM hit the max_tokens ceiling "
                        f"({self._max_tokens}) and the response was cut off. "
                        "Raise LLM_MAX_TOKENS.",
                    )

                if content_raw is None:
                    raise ValueError("LLM returned empty content (None)")

                content = content_raw.strip()
                content = _strip_code_fences(content)

                # Track cost from LiteLLM proxy if available
                if "token_usage" in response:
                    self._cost_tracker.append(
                        {
                            "model": self.model,
                            "tokens": response["token_usage"],
                            "cost": response.get("cost", 0),
                            "attempt": attempt,
                        }
                    )

                return json.loads(content)

            except TruncatedResponseError:
                # Retrying sends the identical request against the identical
                # ceiling, so it truncates identically. Surface it now rather
                # than spending two more slow calls proving that.
                raise
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "LLM call attempt %d/%d failed: %s",
                    attempt,
                    self._max_retries,
                    exc,
                )
                if attempt < self._max_retries:
                    await asyncio.sleep(self._backoff_delay(attempt))

        raise RuntimeError(
            f"LLM provider failed after {self._max_retries} attempts",
        ) from last_error

    # ── Internal helpers ────────────────────────────────────────────

    async def _completion(
        self,
        messages: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """Execute a LiteLLM completion call.

        Args:
            messages: OpenAI-format message list.

        Returns:
            Raw LiteLLM response dict.
        """
        from litellm import acompletion  # noqa: local import per NFR-R-003

        return await acompletion(
            model=self.model,
            messages=messages,
            api_key=self._api_key,
            base_url=self._api_base,
            timeout=self._timeout,
            temperature=0.1,
            max_tokens=self._max_tokens,
            stream=False,
        )

    @staticmethod
    def _backoff_delay(attempt: int) -> float:
        """Exponential backoff with jitter (NFR-R-001).

        Pattern: 1s, 2s, 4s, ... (2^(attempt-1)) capped at 30s.
        """
        delay = min(2 ** (attempt - 1), 30)
        import random

        # Add jitter to prevent thundering herd
        return delay * (0.5 + random.random())

    def get_cost_summary(self) -> List[Dict[str, Any]]:
        """Return accumulated cost tracking entries."""
        return list(self._cost_tracker)

    def reset_cost_tracker(self) -> None:
        """Clear accumulated cost tracking entries."""
        self._cost_tracker.clear()


# ── Claude Code CLI fallback implementation ────────────────────────


# One ceiling for the whole process, not one per request: the router
# builds a fresh TranscriptAnalyzer (and so a fresh service) per upload,
# so a per-instance semaphore would never actually bound anything.
_cli_semaphore: Optional[asyncio.Semaphore] = None


def _get_cli_semaphore(limit: int) -> asyncio.Semaphore:
    """Return the process-wide cap on concurrent CLI invocations."""
    global _cli_semaphore
    if _cli_semaphore is None:
        _cli_semaphore = asyncio.Semaphore(limit)
    return _cli_semaphore


class ClaudeCLIService(PromptAnalysisService):
    """LLM service backed by the local Claude Code CLI (``claude -p``).

    Selected with ``LLM_PROVIDER=claude_cli``. It exists so the analysis
    pipeline can run against an already-authenticated CLI when no usable
    HTTP provider is available -- no API key, no provider budget.

    Local development only. The CLI authenticates against the desktop
    keychain, which does not exist in a container or in CI, so this must
    not be baked into the Dockerfile or the pipeline. Transcripts also
    leave the internal network on this path, unlike the sovereign AI Hub
    endpoint -- see ``.env.example``.

    Unlike :class:`LiteLLMService` this does not retry. A CLI failure is
    almost always deterministic (binary missing, not logged in, bad
    flag), so a second identical invocation just spends the timeout
    again.
    """

    # The CLI is an agent, not a completion endpoint. Left unconstrained
    # it may take extra turns or reach for the filesystem instead of
    # simply transforming the prompt it was handed.
    _DISALLOWED_TOOLS = (
        "Bash,Read,Write,Edit,NotebookEdit,Glob,Grep,WebFetch,WebSearch,Task"
    )

    def __init__(
        self,
        cli_path: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        """Initialise the CLI-backed service.

        Args:
            cli_path: Claude CLI binary. Defaults to ``settings.CLAUDE_CLI_PATH``.
            model: Model to run. Defaults to ``settings.CLAUDE_CLI_MODEL``.
            timeout: Per-invocation timeout. Defaults to the transcript timeout.
        """
        self.provider = "claude_cli"
        self.model = model or settings.CLAUDE_CLI_MODEL
        self._cli_path = cli_path or settings.CLAUDE_CLI_PATH
        self._timeout = timeout or settings.TRANSCRIPT_TIMEOUT_SECONDS

    async def analyze_with_prompt(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> Dict[str, Any]:
        """Run a single CLI invocation and parse its structured output.

        Args:
            system_prompt: The system message.
            user_prompt: The user message containing the task.

        Returns:
            Parsed result dict.

        Raises:
            RuntimeError: If the CLI is missing, fails, times out, or
                returns something that is not the expected JSON.
        """
        prompt = f"{system_prompt}\n\n{user_prompt}"

        async with _get_cli_semaphore(settings.CLAUDE_CLI_MAX_CONCURRENCY):
            envelope = await self._run_cli(prompt)

        if envelope.get("is_error") or envelope.get("subtype") != "success":
            raise RuntimeError(
                "Claude CLI reported failure "
                f"(subtype={envelope.get('subtype')!r}, "
                f"status={envelope.get('api_error_status')!r})",
            )

        result_raw = envelope.get("result")
        if not isinstance(result_raw, str):
            raise RuntimeError("Claude CLI envelope carried no textual result")

        logger.info(
            "Claude CLI call: model=%s cost_usd=%s duration_ms=%s",
            self.model,
            envelope.get("total_cost_usd"),
            envelope.get("duration_ms"),
        )

        content = _strip_code_fences(result_raw.strip())
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Claude CLI did not return valid JSON analysis output",
            ) from exc

    # ── Internal helpers ────────────────────────────────────────────

    async def _run_cli(self, prompt: str) -> Dict[str, Any]:
        """Invoke the CLI once and return its parsed JSON envelope."""
        argv = [
            self._cli_path,
            "-p",
            "--output-format", "json",
            "--model", self.model,
            "--max-turns", "1",
            "--disallowed-tools", self._DISALLOWED_TOOLS,
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *argv,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"Claude CLI not found at {self._cli_path!r}. Install it or "
                "set CLAUDE_CLI_PATH.",
            ) from exc

        # The prompt carries transcript content, so it goes on stdin and
        # never in argv -- argv is readable by any local process via ps
        # (NFR-S-001, NFR-R-002).
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(prompt.encode("utf-8")),
                timeout=self._timeout,
            )
        except (asyncio.TimeoutError, TimeoutError):
            await self._terminate(proc)
            raise RuntimeError(
                f"Claude CLI timed out after {self._timeout}s",
            ) from None

        if proc.returncode != 0:
            detail = stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(
                f"Claude CLI exited {proc.returncode}: {detail[:500]}",
            )

        try:
            return json.loads(stdout.decode("utf-8", errors="replace"))
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Claude CLI returned a non-JSON envelope",
            ) from exc

    @staticmethod
    async def _terminate(proc: Any) -> None:
        """Kill a timed-out CLI process so it cannot outlive the request."""
        try:
            proc.kill()
        except ProcessLookupError:  # already gone
            return
        try:
            await asyncio.wait_for(proc.wait(), timeout=5)
        except (asyncio.TimeoutError, TimeoutError):
            logger.warning("Claude CLI process did not exit after kill")


# ── Helpers ─────────────────────────────────────────────────────────


def _strip_code_fences(content: str) -> str:
    """Strip markdown code fences from LLM JSON output.

    Handles single-fence (```) and triple-fence (````) variants,
    and common language tags like ``json``.

    Args:
        content: Raw LLM response text.

    Returns:
        JSON content with fences removed.
    """
    import re

    stripped = content.strip()

    # Remove opening fence: ``` followed by optional lang tag or quotes
    stripped = re.sub(r"^```[\"']?\s*(json|python|text)?\s*", "", stripped, flags=re.IGNORECASE)

    # Remove closing fence: ``` at the end, possibly preceded/followed by quotes
    # Handle trailing quotes after the fence: ```"  or  `"'  or  `"`
    stripped = re.sub(r"[\"']?\s*```\s*[\"']?\s*$", "", stripped)

    return stripped.strip()


def _build_user_prompt(text: str) -> str:
    """Build the user prompt for transcript analysis.

    Provides structured output instructions with JSON schema for
    topic clusters, action items, and uncertain findings.

    Args:
        text: The transcript text to analyze.

    Returns:
        User prompt string.
    """
    return (
        "Analyze the following meeting transcript.\n\n"
        "Produce a JSON object with these keys:\n"
        "  - topic_clusters: array of {title, summary, confidence (0-1), "
        "uncertain (bool), keywords: [strings]}\n"
        "  - action_items: array of {description, assignee (string or null), "
        "deadline (string or null), confidence (0-1), uncertain (bool)}\n"
        "  - uncertain_findings: array of {type (string), description (string)}\n\n"
        "Transcript:\n---\n"
        f"{text}\n"
        "---\n"
        "Return ONLY valid JSON — no markdown fences, no explanation."
    )


def _build_system_prompt(language: str) -> str:
    """Build the system prompt adapted to the detected language.

    Args:
        language: 'en', 'tr', or 'mixed'.

    Returns:
        System prompt string for the LLM.
    """
    lang_instruction = {
        "en": (
            "You are a meeting transcript analysis assistant. "
            "The transcript is primarily in English. "
            "Produce all output in English."
        ),
        "tr": (
            "You are a meeting transcript analysis assistant. "
            "The transcript is primarily in Turkish. "
            "Produce all output in Turkish."
        ),
        "mixed": (
            "You are a meeting transcript analysis assistant. "
            "The transcript contains mixed English and Turkish content. "
            "Determine the dominant language and produce output in that language."
        ),
    }
    base = lang_instruction.get(language, lang_instruction["en"])

    return (
        f"{base}\n\n"
        "Your task is to:\n"
        "1. Identify distinct topic clusters from the transcript\n"
        "2. Provide a 1-2 sentence summary for each topic\n"
        "3. Extract action items with assignees and deadlines\n"
        "4. Flag uncertain findings with confidence scores\n\n"
        "Rules:\n"
        "- Every topic must have a title, summary, and confidence (0-1)\n"
        "- Assignee and deadline may be null if not mentioned\n"
        "- Mark uncertain items with uncertain: true and include a reason\n"
        "- Return ONLY valid JSON with no surrounding text\n"
        "- Be concise and accurate\n"
    )


# ── Factory function ───────────────────────────────────────────────


def _normalize_uncertain_findings(result: Dict[str, Any]) -> None:
    """Normalize uncertain finding type values before Pydantic validation.

    Qwen 3.x may return arbitrary strings for ``uncertain_findings[].type``
    (e.g. "Configuration") that are not in the ``FindingType`` enum.
    This function maps unknown values to "topic" in-place so validation
    doesn't crash.

    Args:
        result: The LLM result dict, mutated in place.
    """
    VALID_TYPES = {"topic", "summary", "action_item"}
    for finding in result.get("uncertain_findings", []):
        ftype = finding.get("type", "")
        if ftype not in VALID_TYPES:
            logger.warning(
                "UncertainFinding.type '%s' not in %s; normalizing to 'topic'",
                ftype,
                VALID_TYPES,
            )
            finding["type"] = "topic"


def get_llm_service() -> LLMService:
    """Return an LLM service instance based on configuration.

    NFR-R-003 compliant — changing the provider requires only updating
    the ``LLM_PROVIDER`` environment variable.

    Returns:
        A configured :class:`LLMService` instance.
    """
    provider = settings.LLM_PROVIDER.lower()

    if provider in ("claude_cli", "claude-cli"):
        return ClaudeCLIService()
    elif provider == "anthropic":
        return LiteLLMService(provider="anthropic")
    elif provider == "openai":
        return LiteLLMService(provider="openai")
    else:
        # Default to LiteLLM which supports any provider via model string
        logger.info("Using LiteLLM service for provider: %s", provider)
        return LiteLLMService(provider=provider)
