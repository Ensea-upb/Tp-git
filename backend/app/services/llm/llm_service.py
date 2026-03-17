"""
LLM service — Ollama HTTP client with cache + retry + JSON parsing.
Uses httpx.AsyncClient, no extra pip deps needed.
"""
import hashlib
import json
import logging
import re
from collections import OrderedDict
from datetime import datetime, timedelta

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Cache in-memory borné (LLM responses rarely change for the same prompt).
# Taille maximale : 1 000 entrées avec éviction FIFO pour éviter les fuites mémoire.
_MAX_CACHE_SIZE = 1_000
_IN_MEMORY_CACHE: OrderedDict[str, str] = OrderedDict()


def _cache_put(key: str, value: str) -> None:
    """Insère dans le cache in-memory avec éviction FIFO si la limite est atteinte."""
    if key in _IN_MEMORY_CACHE:
        _IN_MEMORY_CACHE.move_to_end(key)
    else:
        if len(_IN_MEMORY_CACHE) >= _MAX_CACHE_SIZE:
            _IN_MEMORY_CACHE.popitem(last=False)
        _IN_MEMORY_CACHE[key] = value


def _build_cache_key(model: str, prompt: str) -> str:
    raw = f"{model}:{prompt}"
    return hashlib.sha256(raw.encode()).hexdigest()


def normalize_list(value) -> list[str] | None:
    """
    Coerce an LLM-provided value to list[str] or None.
    Handles: None, list, comma-separated string, single string.
    Ensures every element is a non-empty string.
    """
    if value is None:
        return None
    if isinstance(value, list):
        result = [str(x).strip() for x in value if str(x).strip()]
        return result if result else None
    if isinstance(value, str):
        parts = [p.strip() for p in value.split(",") if p.strip()]
        return parts if parts else None
    # dict, int, etc. — discard
    return None


def _extract_json(text: str) -> dict | list | None:
    """Extract first JSON object or array from LLM response text."""
    # Try direct parse first
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    # Try extracting {...} block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    # Try extracting [...] block
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


async def call_llm(
    prompt: str,
    model: str | None = None,
    max_tokens: int = 512,
    temperature: float = 0.0,
    db_session=None,
) -> str:
    """
    Call Ollama /api/generate.
    1. Check in-memory cache.
    2. Check DB cache (if db_session provided).
    3. Call Ollama.
    4. Store in both caches.
    Returns raw text response.
    """
    effective_model = model or settings.llm_model_default
    cache_key = _build_cache_key(effective_model, prompt)

    # In-memory cache
    if cache_key in _IN_MEMORY_CACHE:
        logger.debug("LLM in-memory cache hit: %s", cache_key[:16])
        _IN_MEMORY_CACHE.move_to_end(cache_key)
        return _IN_MEMORY_CACHE[cache_key]

    # DB cache
    if db_session is not None:
        from app.repositories.llm_cache_repository import LLMCacheRepository
        repo = LLMCacheRepository(db_session)
        cached = repo.get(cache_key)
        if cached is not None:
            logger.debug("LLM DB cache hit: %s", cache_key[:16])
            _cache_put(cache_key, cached)
            return cached

    # Call Ollama
    payload = {
        "model": effective_model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
            response = await client.post(
                f"{settings.llm_base_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            result_text: str = data.get("response", "")
    except httpx.HTTPError as e:
        logger.error("Ollama HTTP error: %s", e)
        raise
    except Exception as e:
        logger.error("Ollama unexpected error: %s", e)
        raise

    # Store in caches
    _cache_put(cache_key, result_text)
    if db_session is not None:
        from app.repositories.llm_cache_repository import LLMCacheRepository
        repo = LLMCacheRepository(db_session)
        repo.set(cache_key, effective_model, prompt, result_text)
        # Don't commit here — caller controls transaction

    return result_text


async def call_llm_json(
    prompt: str,
    model: str | None = None,
    max_tokens: int = 512,
    temperature: float = 0.0,
    db_session=None,
) -> dict | list | None:
    """Call LLM and return parsed JSON. Returns None if parsing fails."""
    raw = await call_llm(
        prompt=prompt,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        db_session=db_session,
    )
    result = _extract_json(raw)
    if result is None:
        logger.warning("LLM response could not be parsed as JSON. raw=%s", raw[:200])
    return result
