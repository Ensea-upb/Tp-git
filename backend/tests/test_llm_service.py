"""Tests for LLM service — mocked Ollama responses."""
import json
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from app.services.llm.llm_service import (
    _build_cache_key,
    _extract_json,
    call_llm,
    call_llm_json,
    _IN_MEMORY_CACHE,
)


# ----- _extract_json --------------------------------------------------------

def test_extract_json_direct():
    assert _extract_json('{"key": "value"}') == {"key": "value"}


def test_extract_json_with_prefix():
    text = "Voici le résultat: {\"score\": 75, \"label\": \"ok\"}"
    result = _extract_json(text)
    assert result == {"score": 75, "label": "ok"}


def test_extract_json_multiline():
    text = """Some preamble
{
  "missions": ["mission 1", "mission 2"],
  "summary": "résumé"
}
Some postamble"""
    result = _extract_json(text)
    assert result["missions"] == ["mission 1", "mission 2"]


def test_extract_json_list():
    assert _extract_json('["a", "b", "c"]') == ["a", "b", "c"]


def test_extract_json_invalid():
    assert _extract_json("no json here") is None


# ----- _build_cache_key -----------------------------------------------------

def test_cache_key_deterministic():
    k1 = _build_cache_key("gemma3n:e2b", "hello prompt")
    k2 = _build_cache_key("gemma3n:e2b", "hello prompt")
    assert k1 == k2


def test_cache_key_different_models():
    k1 = _build_cache_key("model-a", "same prompt")
    k2 = _build_cache_key("model-b", "same prompt")
    assert k1 != k2


# ----- call_llm (mocked) ----------------------------------------------------

@pytest.mark.asyncio
async def test_call_llm_returns_response():
    mock_response = MagicMock()
    mock_response.json.return_value = {"response": "bonjour"}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        # Clear in-memory cache to force HTTP call
        _IN_MEMORY_CACHE.clear()

        result = await call_llm("test prompt", model="test-model")

    assert result == "bonjour"


@pytest.mark.asyncio
async def test_call_llm_uses_memory_cache():
    cache_key = _build_cache_key("cached-model", "cached prompt")
    _IN_MEMORY_CACHE[cache_key] = "cached response"

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value.__aenter__ = AsyncMock()
        result = await call_llm("cached prompt", model="cached-model")

    # httpx should NOT be called since we have a cache hit
    mock_client_cls.assert_not_called()
    assert result == "cached response"

    # Cleanup
    del _IN_MEMORY_CACHE[cache_key]


@pytest.mark.asyncio
async def test_call_llm_json_parses_response():
    json_response = json.dumps({"summary": "test", "missions": ["m1"]})

    with patch("app.services.llm.llm_service.call_llm", AsyncMock(return_value=json_response)):
        result = await call_llm_json("any prompt")

    assert result["summary"] == "test"
    assert result["missions"] == ["m1"]


@pytest.mark.asyncio
async def test_call_llm_json_returns_none_on_invalid():
    with patch("app.services.llm.llm_service.call_llm", AsyncMock(return_value="not json")):
        result = await call_llm_json("any prompt")

    assert result is None


@pytest.mark.asyncio
async def test_call_llm_raises_on_http_error():
    _IN_MEMORY_CACHE.clear()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.HTTPError("connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        with pytest.raises(httpx.HTTPError):
            await call_llm("fail prompt", model="error-model")
