"""Conftest — shared fixtures for all tests."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _mock_litellm(monkeypatch):
    """Ensure litellm.acompletion is a no-op during tests.

    We patch after the module has been imported (via the fixture
    executing at call time, not collection time).
    """
    import litellm

    async def _noop(*args, **kwargs):
        raise RuntimeError(
            "LLM call was made in tests! "
            "Patch litellm.acompletion in the test that needs it."
        )

    monkeypatch.setattr(litellm, "acompletion", _noop)
