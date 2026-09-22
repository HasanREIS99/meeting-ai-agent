"""
Tests for the LLM service layer.

Tests LiteLLM integration, prompt building, structured output
validation, retry/backoff, cost tracking, and confidence
thresholding (STORY-002-001 through STORY-002-004).
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from meeting_analyzer.config import settings
from meeting_analyzer.llm_service import (
    ClaudeCLIService,
    LiteLLMService,
    TruncatedResponseError,
    LLMAnalysisResult,
    LLMActionItem,
    LLMTopicCluster,
    LLMUncertainFinding,
    _build_system_prompt,
    _build_user_prompt,
    _strip_code_fences,
    get_llm_service,
)


# ── Prompt tests (STORY-002-002, FR-004/005/006) ──────────────────


class TestBuildSystemPrompt:
    """Language-specific system prompt tests (FR-004, FR-005, FR-006)."""

    def test_english_prompt(self):
        prompt = _build_system_prompt("en")
        assert "English" in prompt
        assert "output in English" in prompt

    def test_turkish_prompt(self):
        prompt = _build_system_prompt("tr")
        assert "Turkish" in prompt
        assert "output in Turkish" in prompt

    def test_mixed_prompt(self):
        prompt = _build_system_prompt("mixed")
        assert "mixed English and Turkish" in prompt

    def test_fallback_for_unknown_language(self):
        prompt = _build_system_prompt("de")
        assert "English" in prompt

    def test_prompt_contains_common_sections(self):
        for lang in ("en", "tr", "mixed"):
            prompt = _build_system_prompt(lang)
            assert "topic clusters" in prompt.lower()
            assert "action items" in prompt.lower()
            assert "confidence" in prompt.lower()
            assert "valid json" in prompt.lower()


class TestBuildUserPrompt:
    """Structured user prompt tests."""

    def test_user_prompt_includes_transcript(self):
        text = "Meeting notes from Monday."
        prompt = _build_user_prompt(text)
        assert text in prompt
        assert "topic_clusters" in prompt
        assert "action_items" in prompt
        assert "uncertain_findings" in prompt

    def test_user_prompt_enforces_json_only(self):
        prompt = _build_user_prompt("test")
        assert "ONLY valid JSON" in prompt
        assert "no markdown fences" in prompt


class TestStripCodeFences:
    """Markdown code fence stripping tests."""

    def test_plain_json(self):
        content = '{"key": "value"}'
        assert _strip_code_fences(content) == content

    def test_single_fence(self):
        content = '```json\n{"key": "value"}\n```'
        assert _strip_code_fences(content) == '{"key": "value"}'

    def test_triple_fence(self):
        # Standard triple-fence with language tag (common LLM output)
        content = '```json\n{"key": "value"}\n```'
        assert _strip_code_fences(content) == '{"key": "value"}'

    def test_raw_triple_backticks(self):
        # Triple backticks without language tag
        content = '```\n{"key": "value"}\n```'
        assert _strip_code_fences(content) == '{"key": "value"}'

    def test_mixed_quotes_and_fences(self):
        # Handles fence with extra quote characters (non-standard but possible)
        content = '```"\n{"key": "value"}\n```"'
        result = _strip_code_fences(content)
        assert result == '{"key": "value"}'

    def test_no_language_tag(self):
        content = '```\n{"key": "value"}\n```'
        assert _strip_code_fences(content) == '{"key": "value"}'

    def test_whitespace_around_fences(self):
        content = '\n  ```json\n{"a": 1}\n```\n  '
        assert _strip_code_fences(content) == '{"a": 1}'


# ── Structured output validation (STORY-002-001) ──────────────────


class TestLLMAnalysisResult:
    """Pydantic validation of LLM structured output."""

    def test_valid_response(self):
        data = {
            "topic_clusters": [
                {
                    "title": "Sprint",
                    "summary": "Backlog review.",
                    "confidence": 0.9,
                    "uncertain": False,
                    "keywords": ["sprint"],
                }
            ],
            "action_items": [
                {
                    "description": "Update board",
                    "assignee": "Jane",
                    "deadline": None,
                    "confidence": 0.85,
                    "uncertain": False,
                }
            ],
            "uncertain_findings": [],
        }
        result = LLMAnalysisResult.model_validate(data)
        assert len(result.topic_clusters) == 1
        assert len(result.action_items) == 1

    def test_empty_response(self):
        result = LLMAnalysisResult.model_validate({})
        assert result.topic_clusters == []
        assert result.action_items == []
        assert result.uncertain_findings == []

    def test_invalid_confidence_lower_bound(self):
        with pytest.raises(Exception):  # Pydantic ValidationError
            LLMAnalysisResult.model_validate({
                "topic_clusters": [
                    {
                        "title": "X",
                        "summary": "Y",
                        "confidence": -0.1,
                    }
                ],
                "action_items": [],
                "uncertain_findings": [],
            })

    def test_invalid_confidence_upper_bound(self):
        with pytest.raises(Exception):
            LLMAnalysisResult.model_validate({
                "topic_clusters": [
                    {
                        "title": "X",
                        "summary": "Y",
                        "confidence": 1.1,
                    }
                ],
                "action_items": [],
                "uncertain_findings": [],
            })


# ── LiteLLMService integration tests (STORY-002-001/002/003/004) ──


class TestLiteLLMService:
    """LiteLLM service tests with mocked API calls."""

    def test_default_initialization(self, monkeypatch):
        # setattr, not setenv: `settings` is a singleton built at import
        # time, so an env var set inside the test arrives too late.
        monkeypatch.setattr(settings, "LLM_PROVIDER", "anthropic")
        service = LiteLLMService()
        assert service.provider == "anthropic"

    def test_custom_max_retries(self, monkeypatch):
        monkeypatch.setenv("LLM_API_KEY", "test-key")
        service = LiteLLMService(max_retries=5)
        assert service._max_retries == 5

    def test_completion_sends_max_tokens(self, monkeypatch):
        """Regression: an unset max_tokens lets LiteLLM apply its own 4096
        default, which a reasoning model exhausts on hidden thinking tokens —
        truncating the JSON mid-document. Silent if it ever regresses."""
        captured = {}

        async def mock_acompletion(*args, **kwargs):
            captured.update(kwargs)
            return {"choices": [{"message": {"content": '{"key": "val"}'}}]}

        monkeypatch.setenv("LLM_API_KEY", "test-key")
        monkeypatch.setattr("litellm.acompletion", mock_acompletion)

        service = LiteLLMService()
        asyncio.get_event_loop().run_until_complete(
            service.analyze_with_prompt("sys", "user")
        )

        assert captured["max_tokens"] == service._max_tokens
        assert captured["max_tokens"] > 4096

    def test_truncated_response_raises(self, monkeypatch):
        """finish_reason 'length' must name the ceiling, not surface as a
        confusing JSON parse error."""
        async def mock_acompletion(*args, **kwargs):
            return {
                "choices": [{
                    "finish_reason": "length",
                    "message": {"content": '{"topic_clusters": [{"title": "cut'},
                }],
            }

        monkeypatch.setenv("LLM_API_KEY", "test-key")
        monkeypatch.setattr("litellm.acompletion", mock_acompletion)

        service = LiteLLMService()
        with pytest.raises(TruncatedResponseError, match="max_tokens"):
            asyncio.get_event_loop().run_until_complete(
                service.analyze_with_prompt("sys", "user")
            )

    def test_truncation_is_not_retried(self, monkeypatch):
        """Truncation is deterministic — retrying the same request against the
        same ceiling only spends two more slow calls to fail identically."""
        calls = []

        async def mock_acompletion(*args, **kwargs):
            calls.append(1)
            return {
                "choices": [{
                    "finish_reason": "length",
                    "message": {"content": "{"},
                }],
            }

        monkeypatch.setenv("LLM_API_KEY", "test-key")
        monkeypatch.setattr("litellm.acompletion", mock_acompletion)

        service = LiteLLMService(max_retries=3)
        with pytest.raises(TruncatedResponseError):
            asyncio.get_event_loop().run_until_complete(
                service.analyze_with_prompt("sys", "user")
            )

        assert len(calls) == 1

    def test_analyze_with_prompt_success(self, monkeypatch):
        mock_response = {
            "choices": [{
                "message": {"content": '{"key": "val"}'},
            }],
        }

        async def mock_acompletion(*args, **kwargs):
            return mock_response

        monkeypatch.setenv("LLM_API_KEY", "test-key")
        monkeypatch.setattr("litellm.acompletion", mock_acompletion)

        service = LiteLLMService()
        result = asyncio.get_event_loop().run_until_complete(
            service.analyze_with_prompt("sys", "user")
        )

        assert result == {"key": "val"}

    def test_analyze_with_prompt_fences(self, monkeypatch):
        mock_response = {
            "choices": [{
                "message": {"content": '```json\n{"key": "val"}\n```'},
            }],
        }

        async def mock_acompletion(*args, **kwargs):
            return mock_response

        monkeypatch.setenv("LLM_API_KEY", "test-key")
        monkeypatch.setattr("litellm.acompletion", mock_acompletion)

        service = LiteLLMService()
        result = asyncio.get_event_loop().run_until_complete(
            service.analyze_with_prompt("sys", "user")
        )

        assert result == {"key": "val"}

    def test_analyze_calls_llm_and_returns_results(self, monkeypatch):
        mock_response = {
            "choices": [{
                "message": {"content": '''{
                    "topic_clusters": [{"title": "Test", "summary": "A test topic", "confidence": 0.95, "uncertain": false, "keywords": []}],
                    "action_items": [{"description": "Do something", "assignee": null, "deadline": null, "confidence": 0.8, "uncertain": false}],
                    "uncertain_findings": []
                }'''}
            }],
        }

        async def mock_acompletion(*args, **kwargs):
            return mock_response

        monkeypatch.setenv("LLM_API_KEY", "test-key")
        monkeypatch.setattr("litellm.acompletion", mock_acompletion)

        service = LiteLLMService()
        result = asyncio.get_event_loop().run_until_complete(
            service.analyze_transcript("test transcript", "en")
        )

        assert "topic_clusters" in result
        assert "action_items" in result
        assert "uncertain_findings" in result
        assert len(result["topic_clusters"]) == 1

    @pytest.mark.asyncio
    async def test_cost_tracking(self, monkeypatch):
        mock_response = {
            "choices": [{
                "message": {"content": '{"topic_clusters":[],"action_items":[],"uncertain_findings":[]}'},
            }],
            "token_usage": {"total_tokens": 100},
            "cost": 0.001,
        }

        async def mock_acompletion(*args, **kwargs):
            return mock_response

        monkeypatch.setenv("LLM_API_KEY", "test-key")
        monkeypatch.setattr("litellm.acompletion", mock_acompletion)

        service = LiteLLMService()
        await service.analyze_transcript("test", "en")

        assert len(service.get_cost_summary()) == 1
        assert service.get_cost_summary()[0]["cost"] == 0.001

    def test_cost_reset(self, monkeypatch):
        monkeypatch.setenv("LLM_API_KEY", "test-key")
        service = LiteLLMService()
        service._cost_tracker.append({"test": True})
        assert len(service.get_cost_summary()) == 1

        service.reset_cost_tracker()
        assert len(service.get_cost_summary()) == 0

    def test_backoff_delay_pattern(self):
        """Exponential backoff base pattern without jitter."""
        # _backoff_delay uses 2^(attempt-1) * (0.5 + random()) with cap 30.
        # With random=0.0: 2^0*0.5=0.5, 2^1*0.5=1.0, 2^2*0.5=2.0
        import random

        # Patch the module-level random BEFORE the method imports it
        orig = random.random
        try:
            random.random = lambda: 0.0
            service = LiteLLMService()
            # The method imports `random` locally, but since we patched
            # the module-level random first, the next import in the module
            # will pick up our patched version
            assert service._backoff_delay(1) == 0.5
            assert service._backoff_delay(2) == 1.0
            assert service._backoff_delay(3) == 2.0
        finally:
            random.random = orig

    def test_backoff_cap_at_30(self):
        """Backoff is capped at 30s."""
        import random

        orig = random.random
        try:
            random.random = lambda: 0.0
            service = LiteLLMService()
            # attempt=8: min(2^7, 30) * 0.5 = 30 * 0.5 = 15
            assert service._backoff_delay(8) == 15.0
        finally:
            random.random = orig

    def test_uncertainty_thresholds(self, monkeypatch):
        """STORY-002-004: Items below threshold are auto-flagged."""
        monkeypatch.setenv("LLM_API_KEY", "test-key")
        monkeypatch.setenv("CONFIDENCE_THRESHOLD", "0.7")

        mock_response = {
            "choices": [{
                "message": {"content": '''{
                    "topic_clusters": [
                        {"title": "High", "summary": "High confidence", "confidence": 0.9, "uncertain": false, "keywords": []},
                        {"title": "Low", "summary": "Low confidence", "confidence": 0.4, "uncertain": false, "keywords": []}
                    ],
                    "action_items": [
                        {"description": "Good item", "assignee": null, "deadline": null, "confidence": 0.95, "uncertain": false},
                        {"description": "Weak item", "assignee": null, "deadline": null, "confidence": 0.3, "uncertain": false}
                    ],
                    "uncertain_findings": []
                }'''}
            }],
        }

        async def mock_acompletion(*args, **kwargs):
            return mock_response

        monkeypatch.setattr("litellm.acompletion", mock_acompletion)

        service = LiteLLMService()
        result = asyncio.get_event_loop().run_until_complete(
            service.analyze_transcript("test transcript", "en")
        )

        # High-confidence items should stay uncertain=False
        assert result["topic_clusters"][0]["uncertain"] is False

        # Low-confidence items should be auto-flagged
        assert result["topic_clusters"][1]["uncertain"] is True
        assert result["action_items"][1]["uncertain"] is True

        # New uncertain findings should be appended
        low_conf_types = [f["type"] for f in result["uncertain_findings"]]
        assert "topic" in low_conf_types
        assert "action_item" in low_conf_types

    def test_analyze_fallback_on_validation_failure(self, monkeypatch):
        """If Pydantic validation fails, raw result is returned."""
        # Return JSON that's missing required fields — validation will fail
        mock_response = {
            "choices": [{
                "message": {"content": '{"partial": "data"}'},
            }],
        }

        async def mock_acompletion(*args, **kwargs):
            return mock_response

        monkeypatch.setenv("LLM_API_KEY", "test-key")
        monkeypatch.setattr("litellm.acompletion", mock_acompletion)

        service = LiteLLMService()
        result = asyncio.get_event_loop().run_until_complete(
            service.analyze_transcript("test transcript", "en")
        )

        # Should not raise — fallback returns empty lists
        assert "topic_clusters" in result
        assert "action_items" in result
        assert "uncertain_findings" in result


# ── Factory function tests (NFR-R-003) ────────────────────────────


class TestGetLLMService:
    """Factory function tests."""

    def test_anthropic_provider(self, monkeypatch):
        monkeypatch.setattr(settings, "LLM_PROVIDER", "anthropic")
        service = get_llm_service()
        assert isinstance(service, LiteLLMService)

    def test_openai_provider(self, monkeypatch):
        monkeypatch.setattr(settings, "LLM_PROVIDER", "openai")
        service = get_llm_service()
        assert isinstance(service, LiteLLMService)

    def test_unknown_provider_defaults(self, monkeypatch):
        monkeypatch.setenv("LLM_API_KEY", "test-key")
        # Unknown provider should create a LiteLLMService without error.
        # Directly test the provider passthrough (the factory just calls
        # LiteLLMService(provider=provider) for unknown values).
        service = LiteLLMService(provider="custom-model")
        assert isinstance(service, LiteLLMService)
        assert service.provider == "custom-model"


# ── ClaudeCLIService (LLM_PROVIDER=claude_cli fallback) ────────────


class _FakeProc:
    """Stand-in for an asyncio subprocess."""

    def __init__(self, stdout=b"", stderr=b"", returncode=0, hang=False):
        self._stdout = stdout
        self._stderr = stderr
        self.returncode = returncode
        self._hang = hang
        self.stdin_payload = None
        self.killed = False

    async def communicate(self, payload=None):
        self.stdin_payload = payload
        if self._hang:
            await asyncio.sleep(3600)
        return self._stdout, self._stderr

    def kill(self):
        self.killed = True
        self.returncode = -9

    async def wait(self):
        return self.returncode


def _envelope(result_text, **over):
    body = {"subtype": "success", "is_error": False, "result": result_text,
            "total_cost_usd": 0.01, "duration_ms": 1200}
    body.update(over)
    return json.dumps(body).encode()


_GOOD_RESULT = json.dumps(
    {
        "topic_clusters": [
            {"title": "Deploy", "summary": "Pipeline broke.", "confidence": 0.9,
             "uncertain": False, "keywords": ["deploy"]},
        ],
        "action_items": [
            {"description": "Fix the pipeline", "assignee": "Bob",
             "deadline": "Friday", "confidence": 0.9, "uncertain": False},
        ],
        "uncertain_findings": [],
    }
)


class TestClaudeCLIService:
    """The CLI-backed fallback provider."""

    @staticmethod
    def _patch(monkeypatch, proc):
        captured = {}

        async def fake_exec(*argv, **kwargs):
            captured["argv"] = list(argv)
            captured["kwargs"] = kwargs
            return proc

        monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
        return captured

    @pytest.mark.asyncio
    async def test_parses_envelope_result(self, monkeypatch):
        """The analysis JSON is read out of the CLI's JSON envelope."""
        proc = _FakeProc(stdout=_envelope(_GOOD_RESULT))
        self._patch(monkeypatch, proc)

        service = ClaudeCLIService()
        out = await service.analyze_with_prompt("sys", "user")

        assert out["topic_clusters"][0]["title"] == "Deploy"
        assert out["action_items"][0]["assignee"] == "Bob"

    @pytest.mark.asyncio
    async def test_strips_code_fences_from_result(self, monkeypatch):
        """The CLI fences its JSON in practice; the existing helper handles it."""
        fenced = f"```json\n{_GOOD_RESULT}\n```"
        proc = _FakeProc(stdout=_envelope(fenced))
        self._patch(monkeypatch, proc)

        out = await ClaudeCLIService().analyze_with_prompt("sys", "user")
        assert out["topic_clusters"][0]["title"] == "Deploy"

    @pytest.mark.asyncio
    async def test_prompt_goes_on_stdin_not_argv(self, monkeypatch):
        """Transcript content must never reach argv (NFR-S-001, NFR-R-002)."""
        proc = _FakeProc(stdout=_envelope(_GOOD_RESULT))
        captured = self._patch(monkeypatch, proc)

        secret = "CONFIDENTIAL-TRANSCRIPT-BODY"
        await ClaudeCLIService().analyze_with_prompt("sys", secret)

        assert secret.encode() in proc.stdin_payload
        assert not any(secret in arg for arg in captured["argv"])

    @pytest.mark.asyncio
    async def test_runs_single_turn_without_tools(self, monkeypatch):
        """It must be a pure transform, not an agent loose on the machine."""
        proc = _FakeProc(stdout=_envelope(_GOOD_RESULT))
        captured = self._patch(monkeypatch, proc)

        await ClaudeCLIService().analyze_with_prompt("sys", "user")
        argv = captured["argv"]

        assert "-p" in argv and "--max-turns" in argv
        assert argv[argv.index("--max-turns") + 1] == "1"
        assert "Bash" in argv[argv.index("--disallowed-tools") + 1]

    @pytest.mark.asyncio
    async def test_nonzero_exit_raises(self, monkeypatch):
        """A failed CLI surfaces its stderr, not a silent empty result."""
        proc = _FakeProc(stdout=b"", stderr=b"not logged in", returncode=1)
        self._patch(monkeypatch, proc)

        with pytest.raises(RuntimeError, match="not logged in"):
            await ClaudeCLIService().analyze_with_prompt("sys", "user")

    @pytest.mark.asyncio
    async def test_timeout_kills_the_process(self, monkeypatch):
        """A hung CLI is killed, not left running past the request."""
        proc = _FakeProc(hang=True)
        self._patch(monkeypatch, proc)

        service = ClaudeCLIService(timeout=1)
        with pytest.raises(RuntimeError, match="timed out"):
            await service.analyze_with_prompt("sys", "user")

        assert proc.killed is True

    @pytest.mark.asyncio
    async def test_missing_binary_is_actionable(self, monkeypatch):
        """A missing binary names the setting that fixes it."""
        async def boom(*argv, **kwargs):
            raise FileNotFoundError(argv[0])

        monkeypatch.setattr(asyncio, "create_subprocess_exec", boom)

        with pytest.raises(RuntimeError, match="CLAUDE_CLI_PATH"):
            await ClaudeCLIService().analyze_with_prompt("sys", "user")

    @pytest.mark.asyncio
    async def test_error_envelope_raises(self, monkeypatch):
        """An envelope flagged as an error is not parsed as a result."""
        proc = _FakeProc(
            stdout=_envelope("", subtype="error_max_turns", is_error=True),
        )
        self._patch(monkeypatch, proc)

        with pytest.raises(RuntimeError, match="reported failure"):
            await ClaudeCLIService().analyze_with_prompt("sys", "user")

    @pytest.mark.asyncio
    async def test_non_json_result_raises(self, monkeypatch):
        """Prose instead of JSON fails loudly rather than half-parsing."""
        proc = _FakeProc(stdout=_envelope("I could not do that."))
        self._patch(monkeypatch, proc)

        with pytest.raises(RuntimeError, match="valid JSON"):
            await ClaudeCLIService().analyze_with_prompt("sys", "user")

    @pytest.mark.asyncio
    async def test_full_pipeline_through_base_class(self, monkeypatch):
        """analyze_transcript works end to end on the shared pipeline."""
        proc = _FakeProc(stdout=_envelope(_GOOD_RESULT))
        self._patch(monkeypatch, proc)

        result = await ClaudeCLIService().analyze_transcript("some text", "en")

        assert len(result["topic_clusters"]) == 1
        assert "processing_time" in result


class TestClaudeCLIFactory:
    """LLM_PROVIDER routes to the CLI provider."""

    @pytest.mark.parametrize("value", ["claude_cli", "claude-cli", "CLAUDE_CLI"])
    def test_provider_selects_cli_service(self, monkeypatch, value):
        monkeypatch.setattr(settings, "LLM_PROVIDER", value)
        assert isinstance(get_llm_service(), ClaudeCLIService)

    def test_anthropic_still_uses_litellm(self, monkeypatch):
        monkeypatch.setattr(settings, "LLM_PROVIDER", "anthropic")
        assert isinstance(get_llm_service(), LiteLLMService)
